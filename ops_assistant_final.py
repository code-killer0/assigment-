import os
import re
from datetime import datetime, timedelta
from pathlib import Path

from dotenv import load_dotenv
from langchain_huggingface import ChatHuggingFace, HuggingFaceEndpoint
from langchain_core.prompts import PromptTemplate
from langchain.output_parsers import StructuredOutputParser, ResponseSchema
from sqlalchemy import create_engine, text

load_dotenv()


class OpsAssistant:
    def __init__(self, db_path='location_analytics.db'):
        self.db_path = db_path
        self.engine = create_engine(f"sqlite:///{db_path}")
        self.current_time = datetime.now()

        print("Loading model...")

        llm_endpoint = HuggingFaceEndpoint(
            repo_id=os.getenv('MODEL_NAME', 'google/gemma-2-2b-it'),
            task="text-generation",
            max_new_tokens=int(os.getenv('MAX_TOKENS', '512')),
            temperature=float(os.getenv('TEMPERATURE', '0.1'))
        )
        self.llm = ChatHuggingFace(llm=llm_endpoint)

        sql_parser = StructuredOutputParser.from_response_schemas([
            ResponseSchema(name='sql_query', description='Valid SQLite SELECT query'),
            ResponseSchema(name='explanation', description='What this query does')
        ])

        self.sql_chain = PromptTemplate(
            template=self._get_sql_template(),
            input_variables=['question', 'time_context'],
            partial_variables={'format_instructions': sql_parser.get_format_instructions()}
        ) | self.llm | sql_parser

        answer_parser = StructuredOutputParser.from_response_schemas([
            ResponseSchema(name='answer', description='Clear answer based on results'),
            ResponseSchema(name='data_quality', description='Quality concerns or None')
        ])

        self.answer_chain = PromptTemplate(
            template="""Analyze these query results and answer the question.

Question: {question}
Results: {results}

{format_instructions}""",
            input_variables=['question', 'results'],
            partial_variables={'format_instructions': answer_parser.get_format_instructions()}
        ) | self.llm | answer_parser

        print("Ready\n")

    def _get_sql_template(self):
        return """Generate a SQLite SELECT query for indoor location analytics.

DATABASE SCHEMA:
- zones(zone_id, name, floor)
- entities(entity_id, name, type)
- pings(ping_id, entity_id, zone_id, rssi, timestamp)
- zone_events(event_id, entity_id, zone_id, event_type, timestamp)

RULES:
- Only SELECT queries
- Use BETWEEN for timestamps
- Use LIKE '%name%' for flexible matching
- JOIN pings to entities to zones for location queries

EXAMPLES:
Q: Who was in Kitchen today?
A: SELECT DISTINCT e.name FROM pings p JOIN entities e ON p.entity_id=e.entity_id JOIN zones z ON p.zone_id=z.zone_id WHERE z.name LIKE '%Kitchen%' AND p.timestamp BETWEEN '2026-02-05 00:00:00' AND '2026-02-05 19:30:00';

Q: Where is Alice?
A: SELECT z.name, z.floor, p.timestamp FROM pings p JOIN zones z ON p.zone_id=z.zone_id JOIN entities e ON p.entity_id=e.entity_id WHERE e.name LIKE '%Alice%' ORDER BY p.timestamp DESC LIMIT 1;

Question: {question}
Time: {time_context}

{format_instructions}"""

    def _extract_time(self, question):
        q = question.lower()
        now = self.current_time

        if 'today' in q:
            start = now.replace(hour=0, minute=0, second=0)
            return start.strftime('%Y-%m-%d %H:%M:%S'), now.strftime('%Y-%m-%d %H:%M:%S')

        if 'yesterday' in q:
            yesterday = now - timedelta(days=1)
            start = yesterday.replace(hour=0, minute=0, second=0)
            end = yesterday.replace(hour=23, minute=59, second=59)
            return start.strftime('%Y-%m-%d %H:%M:%S'), end.strftime('%Y-%m-%d %H:%M:%S')

        match = re.search(r'last (\d+) (minute|hour)s?', q)
        if match:
            delta = timedelta(**{match.group(2) + 's': int(match.group(1))})
            start = now - delta
            return start.strftime('%Y-%m-%d %H:%M:%S'), now.strftime('%Y-%m-%d %H:%M:%S')

        return None, None

    def _clean_sql(self, sql):
        sql = re.sub(r'```sql\n?|```\n?', '', sql).strip()

        if 'SELECT' in sql.upper():
            sql = sql[sql.upper().index('SELECT'):]

        if ';' in sql:
            sql = sql.split(';')[0] + ';'

        if not sql.upper().startswith('SELECT'):
            raise ValueError("Must be SELECT query")

        for bad in ['DROP', 'DELETE', 'INSERT', 'UPDATE', 'ALTER', 'CREATE']:
            if bad in sql.upper():
                raise ValueError(f"Forbidden: {bad}")

        return sql

    def _execute_sql(self, sql):
        with self.engine.connect() as conn:
            result = conn.execute(text(sql))
            rows = result.fetchall()

            if not rows:
                return "No results"

            headers = list(result.keys())
            output = [" | ".join(headers), "-" * 50]
            output.extend([" | ".join(str(v or 'NULL') for v in row) for row in rows[:20]])

            if len(rows) > 20:
                output.append(f"... +{len(rows) - 20} more")

            return "\n".join(output)

    def ask(self, question):
        try:
            start, end = self._extract_time(question)
            time_context = f"BETWEEN '{start}' AND '{end}'" if start else "Current time"

            print("Generating SQL...")
            sql_result = self.sql_chain.invoke({
                'question': question,
                'time_context': time_context
            })

            sql = self._clean_sql(sql_result['sql_query'])
            print(sql_result.get('explanation', 'SQL generated'), "\n")

            print("Executing...")
            results = self._execute_sql(sql)
            print("Done\n")

            print("Answering...")
            answer_result = self.answer_chain.invoke({
                'question': question,
                'results': results
            })

            return {
                'question': question,
                'sql': sql,
                'results': results,
                'answer': answer_result.get('answer', results),
                'quality': answer_result.get('data_quality', 'None')
            }

        except Exception as e:
            return {
                'question': question,
                'error': str(e),
                'answer': f"Error: {e}"
            }

    def show(self, result):
        print("=" * 70)
        print(f"Q: {result['question']}")
        print("=" * 70)

        if 'error' in result:
            print(result['error'])
            return

        print("SQL:\n", result['sql'], "\n")
        print("Results:\n", result['results'], "\n")
        print("Answer:", result['answer'], "\n")

        if result['quality'] != 'None':
            print("Data quality warning:", result['quality'])

        print("=" * 70)


def main():
    print("Ops Assistant - Indoor Location Analytics")
    print("=" * 70)

    if not os.getenv('HUGGINGFACE_API_TOKEN'):
        print("Missing HUGGINGFACE_API_TOKEN in .env")
        return

    if not Path('location_analytics.db').exists():
        print("Database not found")
        print("Run: python3 generate_data.py")
        return

    assistant = OpsAssistant()

    print("Ask questions (or 'exit' to quit):\n")
    print("Examples:")
    print("Who was in Conference Room A today?")
    print("Where is Alice Chen?")
    print("Find floor jumps today")
    print("=" * 70)

    while True:
        try:
            question = input(">> ").strip()

            if question.lower() in ['exit', 'quit', 'q']:
                break

            if not question:
                continue

            result = assistant.ask(question)
            assistant.show(result)

        except KeyboardInterrupt:
            break
        except Exception as e:
            print("Error:", e)


if __name__ == '__main__':
    main()
