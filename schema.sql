
CREATE TABLE IF NOT EXISTS zones (
    zone_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    floor INTEGER NOT NULL
);

--Entities
CREATE TABLE IF NOT EXISTS entities (
    entity_id INTEGER PRIMARY KEY,
    name TEXT NOT NULL,
    type TEXT NOT NULL CHECK(type IN ('person', 'asset'))
);

-- Pings
CREATE TABLE IF NOT EXISTS pings (
    ping_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    zone_id INTEGER NOT NULL,
    rssi INTEGER NOT NULL, 
    timestamp DATETIME NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
);

-- Zone 
CREATE TABLE IF NOT EXISTS zone_events (
    event_id INTEGER PRIMARY KEY AUTOINCREMENT,
    entity_id INTEGER NOT NULL,
    zone_id INTEGER NOT NULL,
    event_type TEXT NOT NULL CHECK(event_type IN ('ENTER', 'EXIT')),
    timestamp DATETIME NOT NULL,
    FOREIGN KEY (entity_id) REFERENCES entities(entity_id),
    FOREIGN KEY (zone_id) REFERENCES zones(zone_id)
);

CREATE INDEX IF NOT EXISTS idx_pings_entity_time ON pings(entity_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_pings_zone_time ON pings(zone_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_events_entity_time ON zone_events(entity_id, timestamp);
CREATE INDEX IF NOT EXISTS idx_events_zone_time ON zone_events(zone_id, timestamp);
