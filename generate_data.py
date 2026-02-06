import sqlite3
import random
from datetime import datetime, timedelta

def init_database(db_path='location_analytics.db'):
    conn = sqlite3.connect(db_path)
    cursor = conn.cursor()
    
    with open('schema.sql', 'r') as f:
        cursor.executescript(f.read())
    
    conn.commit()
    return conn

def seed_zones(cursor):
    zones = [
        (1, 'Main Entrance', 1),
        (2, 'Lobby', 1),
        (3, 'Conference Room A', 1),
        (4, 'Conference Room B', 2),
        (5, 'Open Workspace', 2),
        (6, 'Kitchen', 2),
        (7, 'Server Room', 3),
        (8, 'Executive Office', 3),
        (9, 'Parking Garage', 0),
        (10, 'Loading Dock', 0)
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO zones VALUES (?, ?, ?)', zones)
    print(f"Created {len(zones)} zones")

def seed_entities(cursor):
    """Create tracked entities"""
    entities = [
        (1, 'Akash Maurya', 'person'),
        (2, 'Babul Kumar', 'person'),
        (3, 'Carry', 'person'),
        (4, 'Durgesh Kumar', 'person'),
        (5, 'Harshit', 'person'),
        (6, 'Laptop-A001', 'asset'),
        (7, 'Projector-P001', 'asset'),
        (8, 'Tablet-T042', 'asset')
    ]
    
    cursor.executemany('INSERT OR REPLACE INTO entities VALUES (?, ?, ?)', entities)
    print(f"Created {len(entities)} entities")

def generate_movement_scenario(cursor, entity_id, zones_path, start_time, duration_minutes, rssi_quality='good'):
    """
    Generate realistic movement through zones with pings and events
    
    Args:
        zones_path: List of (zone_id, dwell_minutes) tuples
        rssi_quality: 'good', 'medium', 'poor', or 'anomaly'
    """
    current_time = start_time
    pings = []
    events = []
    
    for zone_id, dwell_minutes in zones_path:
        events.append((entity_id, zone_id, 'ENTER', current_time.strftime('%Y-%m-%d %H:%M:%S')))
        
        end_time = current_time + timedelta(minutes=dwell_minutes)
        ping_time = current_time
        
        while ping_time < end_time:
            if rssi_quality == 'good':
                rssi = random.randint(-50, -35)
            elif rssi_quality == 'medium':
                rssi = random.randint(-70, -55)
            elif rssi_quality == 'poor':
                rssi = random.randint(-90, -75)
            else:  
                rssi = random.randint(-100, -90)
            
            pings.append((entity_id, zone_id, rssi, ping_time.strftime('%Y-%m-%d %H:%M:%S')))
       
            ping_time += timedelta(seconds=random.randint(30, 90))
        
        events.append((entity_id, zone_id, 'EXIT', end_time.strftime('%Y-%m-%d %H:%M:%S')))
        current_time = end_time
 
    cursor.executemany('INSERT INTO pings (entity_id, zone_id, rssi, timestamp) VALUES (?, ?, ?, ?)', pings)
    cursor.executemany('INSERT INTO zone_events (entity_id, zone_id, event_type, timestamp) VALUES (?, ?, ?, ?)', events)
    
    return len(pings), len(events)

def generate_sample_data(cursor):
    """Generate realistic scenarios"""
    now = datetime.now()
    today_start = now.replace(hour=8, minute=0, second=0, microsecond=0)
    yesterday_start = today_start - timedelta(days=1)
    
    total_pings = 0
    total_events = 0
    
   
    pings, events = generate_movement_scenario(
        cursor, 1,
        [(1, 2), (2, 5), (5, 180), (6, 15), (5, 120), (3, 60), (2, 5), (1, 2)],
        yesterday_start, 384, 'good'
    )
    total_pings += pings
    total_events += events
    
    pings, events = generate_movement_scenario(
        cursor, 2,
        [(1, 2), (2, 3), (5, 120), (6, 10), (2, 5), (1, 2)],
        yesterday_start, 142, 'medium'
    )
    total_pings += pings
    total_events += events
    
    
    pings, events = generate_movement_scenario(
        cursor, 1,
        [(9, 10), (1, 3), (2, 5), (5, 60), (4, 90)],
        today_start - timedelta(minutes=30), 168, 'good'
    )
    total_pings += pings
    total_events += events
    
    pings, events = generate_movement_scenario(
        cursor, 2,
        [(1, 2), (2, 3), (6, 10), (5, 120)],
        today_start + timedelta(minutes=45), 135, 'good'
    )
    total_pings += pings
    total_events += events
    
    pings, events = generate_movement_scenario(
        cursor, 3,
        [(1, 2), (8, 45), (7, 5), (8, 30), (4, 60)],  
        today_start, 142, 'good'
    )
    total_pings += pings
    total_events += events
    
    pings, events = generate_movement_scenario(
        cursor, 4,
        [(1, 2), (7, 180)],
        today_start + timedelta(hours=1), 182, 'poor'
    )
    total_pings += pings
    total_events += events
    
    pings, events = generate_movement_scenario(
        cursor, 5,
        [(1, 2), (3, 30), (2, 5), (1, 2)],
        today_start + timedelta(hours=2), 39, 'good'
    )
    total_pings += pings
    total_events += events
    
    recent_start = now - timedelta(minutes=30)
    
    pings, events = generate_movement_scenario(
        cursor, 1,
        [(6, 10)],
        recent_start, 10, 'good'
    )
    total_pings += pings
    total_events += events
 
    pings, events = generate_movement_scenario(
        cursor, 3,
        [(4, 30)],
        recent_start, 30, 'medium'
    )
    total_pings += pings
    total_events += events
    
    pings, events = generate_movement_scenario(
        cursor, 6,
        [(3, 480)],
        yesterday_start, 480, 'anomaly'
    )
    total_pings += pings
    total_events += events
    
    pings, events = generate_movement_scenario(
        cursor, 7,
        [(10, 30), (4, 300)],
        today_start, 330, 'good'
    )
    total_pings += pings
    total_events += events
    
    print(f"✓ Generated {total_pings} pings and {total_events} zone events")
    print(f"  - Time range: {yesterday_start} to {now}")
    print(f"  - Includes data quality issues: floor jumps, weak RSSI, anomalies")

def main():
    print("🔧 Initializing Indoor Location Analytics Database...\n")
    
    conn = init_database()
    cursor = conn.cursor()
    
    seed_zones(cursor)
    seed_entities(cursor)
    generate_sample_data(cursor)
    
    conn.commit()

    cursor.execute('SELECT COUNT(*) FROM pings')
    ping_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT COUNT(*) FROM zone_events')
    event_count = cursor.fetchone()[0]
    
    cursor.execute('SELECT MIN(timestamp), MAX(timestamp) FROM pings')
    time_range = cursor.fetchone()
    
    print(f"\n Database created: location_analytics.db")
    print(f"\n Summary:")
    print(f"   Zones: 10")
    print(f"   Entities: 8 (5 people, 3 assets)")
    print(f"   Pings: {ping_count}")
    print(f"   Events: {event_count}")
    print(f"   Time range: {time_range[0]} to {time_range[1]}")
    
    conn.close()

if __name__ == '__main__':
    main()
