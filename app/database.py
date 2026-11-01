import sqlite3
import os
import json
from datetime import datetime

DB_PATH = os.path.join(os.path.dirname(__file__), "..", "prithvi_orbit.db")

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()
    cursor.executescript("""
    CREATE TABLE IF NOT EXISTS locations (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        region TEXT NOT NULL
    );

    CREATE TABLE IF NOT EXISTS hotspot_cache (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        source TEXT NOT NULL,
        acquired_at TEXT NOT NULL,
        frp REAL,
        confidence TEXT,
        district TEXT,
        fetched_at TEXT NOT NULL,
        is_demo INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS sos_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        reported_at TEXT NOT NULL,
        party_size INTEGER NOT NULL,
        needs TEXT NOT NULL,
        description TEXT,
        status TEXT DEFAULT 'QUEUED',
        assigned_unit_id TEXT DEFAULT NULL,
        is_demo INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS rescue_units (
        id TEXT PRIMARY KEY,
        label TEXT NOT NULL,
        unit_type TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        capacity INTEGER NOT NULL,
        equipment_json TEXT NOT NULL,
        availability INTEGER DEFAULT 1,
        is_demo INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS shelters (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        label TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        status TEXT DEFAULT 'OPEN',
        capacity INTEGER NOT NULL,
        current_occupancy INTEGER DEFAULT 0,
        facilities_json TEXT NOT NULL,
        verified_by TEXT NOT NULL,
        verified_at TEXT NOT NULL,
        is_demo INTEGER DEFAULT 1
    );

    CREATE TABLE IF NOT EXISTS road_closures (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        from_node TEXT NOT NULL,
        to_node TEXT NOT NULL,
        reason TEXT NOT NULL,
        updated_at TEXT NOT NULL,
        is_demo INTEGER DEFAULT 1,
        UNIQUE(from_node, to_node)
    );

    CREATE TABLE IF NOT EXISTS farmer_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        farmer_name TEXT NOT NULL,
        contact TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        acres REAL NOT NULL,
        service_type TEXT NOT NULL,
        status TEXT DEFAULT 'QUEUED',
        created_at TEXT NOT NULL,
        is_demo INTEGER DEFAULT 1
    );
    """)
    conn.commit()
    conn.close()

def seed_baseline_data(force=False):
    conn = get_db()
    c = conn.cursor()
    
    if force:
        c.execute("DELETE FROM shelters")
        c.execute("DELETE FROM rescue_units")
        c.execute("DELETE FROM road_closures")
        c.execute("DELETE FROM hotspot_cache")
        c.execute("DELETE FROM locations")
        conn.commit()

    c.execute("SELECT COUNT(*) as cnt FROM shelters")
    if c.fetchone()["cnt"] == 0:
        shelters_data = [
            ("Mohali Sector 65 Multipurpose Relief Complex", 30.6860, 76.7350, "OPEN", 350, 110,
             json.dumps(["RO Clean Water", "24/7 Medical Triage", "DG Backup Generator", "Infant Baby Food"]),
             "Mohali District Collectorate / SDM Office", "2026-10-31 08:30"),
            ("Kharar Model Senior Secondary School Relief Hub", 30.7490, 76.6450, "OPEN", 220, 95,
             json.dumps(["Community Mess", "Bedding & Blankets", "Medical Officer On-Duty", "Wheelchair Ramps"]),
             "Kharar Civil Defense Coordinator", "2026-10-31 09:15"),
            ("Ropar Sutlej High Embankment Camp", 30.9650, 76.5300, "NEAR FULL", 120, 112,
             json.dumps(["High-Ground Tents", "First Aid Kit", "Emergency Rations"]),
             "Ropar Disaster Nodal Desk", "2026-10-31 07:45"),
            ("Fatehgarh Sahib Gurdwara Relief Community Center", 30.6480, 76.3980, "OPEN", 400, 130,
             json.dumps(["24/7 Hot Langar Meals", "Shelter Hall", "Clean Washrooms", "Paramedic Volunteer Team"]),
             "District Administration Fatehgarh Sahib", "2026-10-31 10:00")
        ]
        c.executemany("""
            INSERT INTO shelters (label, lat, lon, status, capacity, current_occupancy, facilities_json, verified_by, verified_at, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, shelters_data)

    c.execute("SELECT COUNT(*) as cnt FROM rescue_units")
    if c.fetchone()["cnt"] == 0:
        units_data = [
            ("NDRF_ZODIAC_01", "7th Bn NDRF Inflatable Zodiac", "Watercraft (Inflatable Zodiac)", 30.7300, 76.7000, 8,
             json.dumps(["Outboard Motor", "Life Jackets", "Stretcher", "First Aid Trauma Kit", "Night Searchlight"]), 1),
            ("SDRF_4X4_HEAVY_02", "Punjab SDRF High-Clearance Wader Truck", "4x4 High-Clearance Truck", 30.6500, 76.4000, 15,
             json.dumps(["Winch Cable", "High Snorkel Exhaust", "Chainsaws", "Submersible Pumps"]), 1),
            ("CIVIL_DEFENSE_AMB_03", "District Disaster Medical Rover", "Medical Evacuation Ambulance", 30.9100, 75.8600, 3,
             json.dumps(["Portable Oxygen", "Defibrillator", "Wheelchair Lifter", "Emergency IV Fluids"]), 1),
            ("VOLUNTEER_BOAT_04", "Ropar River Patrol Motor Launch", "Shallow River Rescue Boat", 30.9664, 76.5331, 6,
             json.dumps(["Thermal Blankets", "Rescue Ropes", "Handheld Megaphone"]), 0)
        ]
        c.executemany("""
            INSERT INTO rescue_units (id, label, unit_type, lat, lon, capacity, equipment_json, availability, is_demo)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
        """, units_data)

    c.execute("SELECT COUNT(*) as cnt FROM hotspot_cache")
    if c.fetchone()["cnt"] == 0:
        hotspots = [
            (31.634, 74.872, "NASA VIIRS S-NPP", "2026-10-31 07:45", 22.4, "high", "Amritsar Rural"),
            (31.326, 75.576, "NASA VIIRS NOAA-20", "2026-10-31 07:45", 31.8, "high", "Jalandhar West"),
            (30.901, 75.857, "NASA VIIRS S-NPP", "2026-10-31 07:45", 14.2, "nominal", "Ludhiana Agro Belt"),
            (30.339, 76.386, "NASA VIIRS NOAA-20", "2026-10-31 07:45", 18.6, "nominal", "Patiala Nabha Road"),
            (30.704, 76.717, "NASA VIIRS S-NPP", "2026-10-31 07:45", 16.9, "high", "Mohali / Kharar Rural"),
            (31.147, 75.341, "NASA VIIRS NOAA-20", "2026-10-31 07:45", 36.5, "high", "Moga Harvesting Sector")
        ]
        now_str = datetime.utcnow().isoformat() + "Z"
        for h in hotspots:
            c.execute("""
                INSERT INTO hotspot_cache (lat, lon, source, acquired_at, frp, confidence, district, fetched_at, is_demo)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, 1)
            """, (h[0], h[1], h[2], h[3], h[4], h[5], h[6], now_str))

    c.execute("SELECT COUNT(*) as cnt FROM road_closures")
    if c.fetchone()["cnt"] == 0:
        c.execute("""
            INSERT INTO road_closures (from_node, to_node, reason, updated_at, is_demo)
            VALUES (?, ?, ?, ?, 1)
        """, ("KHARAR_JUNCTION", "ROPAR_CROSSING", "NH-205 Flash Inundation & Culvert Embankment Breach", "2026-10-31 08:00"))

    conn.commit()
    conn.close()
