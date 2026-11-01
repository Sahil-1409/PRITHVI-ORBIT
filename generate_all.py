import os

print("PRITHVI-ORBIT files banayi ja rahi hain...")

# Folders create karo
os.makedirs("app", exist_ok=True)
os.makedirs("static", exist_ok=True)

# 1. requirements.txt
with open("requirements.txt", "w", encoding="utf-8") as f:
    f.write("""fastapi>=0.110.0
uvicorn>=0.28.0
httpx>=0.27.0
pydantic>=2.6.0
networkx>=3.2.1
python-dotenv>=1.0.1
""")

# 2. .env
with open(".env", "w", encoding="utf-8") as f:
    f.write("""APP_MODE=demo
PORT=8001
FIRMS_MAP_KEY=
GEMINI_API_KEY=
DEMO_SEED=1
""")

# 3. app/models.py
with open("app/models.py", "w", encoding="utf-8") as f:
    f.write('''from pydantic import BaseModel, Field
from typing import Optional

class SOSCreate(BaseModel):
    lat: float = Field(..., ge=-90, le=90)
    lon: float = Field(..., ge=-180, le=180)
    party_size: int = Field(1, ge=1, le=50)
    needs: str = "Standard Evacuation"
    description: Optional[str] = ""
    medical_flag: bool = False
    mobility_flag: bool = False

class FarmerRequestCreate(BaseModel):
    farmer_name: str = Field("Sardar Balwinder Singh", min_length=2)
    contact: str = Field("+91 98765 43210")
    lat: float = 30.7046
    lon: float = 76.7179
    acres: float = Field(..., gt=0, le=500)
    service_type: str = "Biomass Baler Unit"

class ClosureToggleRequest(BaseModel):
    from_node: str
    to_node: str
    blocked: bool = True
    reason: str = "Simulated Flood Inundation & Road Cut"

class ShelterUpdate(BaseModel):
    status: str
    current_occupancy: Optional[int] = None

class BroadcastSimulation(BaseModel):
    radius_km: float = 15.0
    channel: str = "SMS & WhatsApp Vernacular Broadcast"
    district: str = "Mohali-Ludhiana Airshed Belt"
''')

# 4. app/database.py
with open("app/database.py", "w", encoding="utf-8") as f:
    f.write('''import sqlite3
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
''')

# 5. app/rescue_engine.py
with open("app/rescue_engine.py", "w", encoding="utf-8") as f:
    f.write('''import networkx as nx
import math
from app.database import get_db

def haversine_km(lat1, lon1, lat2, lon2):
    R = 6371.0
    dlat = math.radians(lat2 - lat1)
    dlon = math.radians(lon2 - lon1)
    a = math.sin(dlat / 2)**2 + math.cos(math.radians(lat1)) * math.cos(math.radians(lat2)) * math.sin(dlon / 2)**2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(1 - a))
    return round(R * c, 2)

class RescueRoutingEngine:
    def __init__(self):
        self.G = nx.Graph()
        self._build_punjab_network()

    def _build_punjab_network(self):
        nodes = {
            "MOHALI_CENTER": {"lat": 30.7046, "lon": 76.7179, "label": "Mohali Sector 62 Main Hub"},
            "KHARAR_JUNCTION": {"lat": 30.7499, "lon": 76.6411, "label": "Kharar NH-205 Junction"},
            "ROPAR_CROSSING": {"lat": 30.9664, "lon": 76.5331, "label": "Ropar Sutlej Crossing"},
            "FATEHGARH_NORTH": {"lat": 30.6480, "lon": 76.3980, "label": "Sirhind-Fatehgarh Bypass"},
            "LUDHIANA_EAST": {"lat": 30.9010, "lon": 75.8573, "label": "Ludhiana GT Road Corridor"},
            "PATIALA_BYPASS": {"lat": 30.3398, "lon": 76.3869, "label": "Patiala Bypass Junction"},
            "MORINDA_CROSS": {"lat": 30.7932, "lon": 76.4952, "label": "Morinda Inter-District Crossing"}
        }
        for n, attr in nodes.items():
            self.G.add_node(n, **attr)

        edges = [
            ("MOHALI_CENTER", "KHARAR_JUNCTION", 14),
            ("KHARAR_JUNCTION", "ROPAR_CROSSING", 32),
            ("KHARAR_JUNCTION", "MORINDA_CROSS", 18),
            ("MORINDA_CROSS", "FATEHGARH_NORTH", 20),
            ("MORINDA_CROSS", "ROPAR_CROSSING", 25),
            ("FATEHGARH_NORTH", "LUDHIANA_EAST", 45),
            ("ROPAR_CROSSING", "LUDHIANA_EAST", 55),
            ("PATIALA_BYPASS", "FATEHGARH_NORTH", 38),
            ("MOHALI_CENTER", "PATIALA_BYPASS", 42)
        ]
        for u, v, w in edges:
            self.G.add_edge(u, v, weight=w)

    def get_active_closures(self):
        conn = get_db()
        rows = conn.execute("SELECT from_node, to_node, reason FROM road_closures").fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def set_closure(self, from_node: str, to_node: str, blocked: bool, reason: str = ""):
        conn = get_db()
        c = conn.cursor()
        if blocked:
            c.execute("""
                INSERT OR REPLACE INTO road_closures (from_node, to_node, reason, updated_at, is_demo)
                VALUES (?, ?, ?, datetime('now'), 1)
            """, (from_node, to_node, reason or "Simulated Flood Inundation"))
        else:
            c.execute("""
                DELETE FROM road_closures 
                WHERE (from_node = ? AND to_node = ?) OR (from_node = ? AND to_node = ?)
            """, (from_node, to_node, to_node, from_node))
        conn.commit()
        conn.close()

    def find_nearest_node(self, lat: float, lon: float):
        closest_node = None
        min_dist = float("inf")
        for node, data in self.G.nodes(data=True):
            dist = haversine_km(lat, lon, data["lat"], data["lon"])
            if dist < min_dist:
                min_dist = dist
                closest_node = node
        return closest_node, min_dist

    def find_candidate_route(self, origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float):
        closures = self.get_active_closures()
        blocked_pairs = set()
        blocked_reasons = {}
        for cl in closures:
            pair = tuple(sorted([cl["from_node"], cl["to_node"]]))
            blocked_pairs.add(pair)
            blocked_reasons[pair] = cl["reason"]

        active_edges = []
        for u, v, data in self.G.edges(data=True):
            pair = tuple(sorted([u, v]))
            if pair not in blocked_pairs:
                active_edges.append((u, v, data))

        sub_G = self.G.edge_subgraph([e[:2] for e in active_edges])

        origin_node, dist_orig = self.find_nearest_node(origin_lat, origin_lon)
        dest_node, dist_dest = self.find_nearest_node(dest_lat, dest_lon)

        try:
            path = nx.shortest_path(sub_G, source=origin_node, target=dest_node, weight='weight')
            est_minutes = nx.shortest_path_length(sub_G, source=origin_node, target=dest_node, weight='weight')
            
            coords = [[origin_lat, origin_lon]]
            for n in path:
                coords.append([self.G.nodes[n]['lat'], self.G.nodes[n]['lon']])
            coords.append([dest_lat, dest_lon])

            avoided_details = [
                f"{p[0]} <-> {p[1]} ({blocked_reasons[p]})" for p in blocked_pairs
            ]

            return {
                "route_found": True,
                "status": "CANDIDATE_ROUTE_AVAILABLE",
                "disclaimer": "Candidate route based on known closures. Not an operational safety guarantee. Comply with local civil defense instructions.",
                "path_nodes": path,
                "coordinates": coords,
                "estimated_minutes": round(est_minutes + (dist_orig + dist_dest) * 1.5, 1),
                "blocked_edges_avoided": avoided_details,
                "provenance": "DEMO_GRAPH_ALGORITHM"
            }
        except (nx.NetworkXNoPath, nx.NodeNotFound):
            return {
                "route_found": False,
                "status": "NO_SAFE_ROUTE_FOUND",
                "disclaimer": "All candidate routes obstructed by confirmed flood closures. Awaiting civil defense clearance.",
                "path_nodes": [],
                "coordinates": [],
                "estimated_minutes": None,
                "blocked_edges_avoided": list(blocked_reasons.values()),
                "provenance": "DEMO_GRAPH_ALGORITHM"
            }

    def evaluate_rescue_feasibility(self, target_lat: float, target_lon: float, party_size: int, medical_flag: bool = False, mobility_flag: bool = False):
        conn = get_db()
        rows = conn.execute("SELECT * FROM rescue_units").fetchall()
        conn.close()

        ranked = []
        for r in rows:
            unit = dict(r)
            feasible = True
            rejections = []

            if not unit["availability"]:
                feasible = False
                rejections.append("Unit currently engaged in prior active dispatch.")

            if unit["capacity"] < party_size:
                feasible = False
                rejections.append(f"Inadequate capacity ({unit['capacity']} seats vs {party_size} required).")

            if (medical_flag or mobility_flag) and "Medical" not in unit["unit_type"] and "Heavy" not in unit["unit_type"]:
                rejections.append("Unit lacks specialized stretcher/medical life-support apparatus.")

            dist_km = haversine_km(unit["lat"], unit["lon"], target_lat, target_lon)

            ranked.append({
                "unit_id": unit["id"],
                "label": unit["label"],
                "unit_type": unit["unit_type"],
                "capacity": unit["capacity"],
                "distance_km": dist_km,
                "feasible": feasible,
                "rejection_reasons": rejections,
                "provenance": "DEMO_FEASIBILITY_ENGINE"
            })

        ranked.sort(key=lambda x: (not x["feasible"], x["distance_km"]))
        return ranked

rescue_engine = RescueRoutingEngine()
''')

# 6. app/weather_service.py
with open("app/weather_service.py", "w", encoding="utf-8") as f:
    f.write('''import httpx
from datetime import datetime

async def get_weather_data(lat: float = 30.7046, lon: float = 76.7179):
    url = (
        f"https://api.open-meteo.com/v1/forecast?latitude={lat}&longitude={lon}"
        f"&current=temperature_2m,relative_humidity_2m,apparent_temperature,precipitation,wind_speed_10m,wind_direction_10m,weather_code"
        f"&hourly=temperature_2m,precipitation_probability,wind_speed_10m&timezone=auto"
    )
    try:
        async with httpx.AsyncClient(timeout=4.0) as client:
            res = await client.get(url)
            res.raise_for_status()
            data = res.json()
            curr = data.get("current", {})
            return {
                "source": "Open-Meteo REST API",
                "provenance": "FORECAST",
                "is_offline": False,
                "fetched_at": datetime.utcnow().isoformat() + "Z",
                "temperature": curr.get("temperature_2m", 25.2),
                "apparent_temperature": curr.get("apparent_temperature", 26.4),
                "humidity": curr.get("relative_humidity_2m", 48),
                "precipitation": curr.get("precipitation", 0.0),
                "wind_speed": curr.get("wind_speed_10m", 8.4),
                "wind_direction": curr.get("wind_direction_10m", 345),
                "weather_code": curr.get("weather_code", 0)
            }
    except Exception:
        return {
            "source": "Local Seed Meteorological Cache",
            "provenance": "DEMO_OFFLINE_BUFFER",
            "is_offline": True,
            "fetched_at": datetime.utcnow().isoformat() + "Z",
            "temperature": 26.0,
            "apparent_temperature": 27.1,
            "humidity": 52,
            "precipitation": 0.0,
            "wind_speed": 8.0,
            "wind_direction": 340,
            "weather_code": 1
        }
''')

# 7. app/firms_service.py
with open("app/firms_service.py", "w", encoding="utf-8") as f:
    f.write('''import os
import csv
import io
import httpx
from datetime import datetime
from app.database import get_db

async def get_hotspots_data(bbox: str = "73.8,29.5,76.9,32.5"):
    map_key = os.getenv("FIRMS_MAP_KEY", "").strip()
    
    if map_key:
        url = f"https://firms.modaps.eosdis.nasa.gov/api/area/csv/{map_key}/VIIRS_SNPP_NRT/{bbox}/1"
        try:
            async with httpx.AsyncClient(timeout=4.5) as client:
                res = await client.get(url)
                res.raise_for_status()
                reader = csv.DictReader(io.StringIO(res.text))
                points = []
                for row in reader:
                    points.append({
                        "lat": float(row.get("latitude", 0)),
                        "lon": float(row.get("longitude", 0)),
                        "bright_ti4": float(row.get("bright_ti4", 330.0)),
                        "acq_date": row.get("acq_date", datetime.utcnow().strftime("%Y-%m-%d")),
                        "confidence": row.get("confidence", "nominal"),
                        "frp": float(row.get("frp", 12.0)),
                        "source": "NASA FIRMS (VIIRS S-NPP Live)",
                        "provenance": "OBSERVATION"
                    })
                if points:
                    return {
                        "source": "NASA FIRMS Real-Time VIIRS Feed",
                        "provenance": "OBSERVATION",
                        "active_hotspots": len(points),
                        "data": points,
                        "disclaimer": "SATELLITE THERMAL HOTSPOT - NOT CONFIRMED FIRE"
                    }
        except Exception:
            pass

    conn = get_db()
    rows = conn.execute("SELECT lat, lon, source, acquired_at as acq_date, frp, confidence, district FROM hotspot_cache").fetchall()
    conn.close()
    
    data = []
    for r in rows:
        d = dict(r)
        d["bright_ti4"] = 345.5
        d["provenance"] = "DEMO_OFFLINE_BUFFER"
        data.append(d)

    return {
        "source": "NASA FIRMS Punjab Regional Sample (Offline Buffer)",
        "provenance": "DEMO_OFFLINE_BUFFER",
        "active_hotspots": len(data),
        "data": data,
        "disclaimer": "SATELLITE THERMAL HOTSPOT - NOT CONFIRMED FIRE"
    }
''')

# 8. main.py
with open("main.py", "w", encoding="utf-8") as f:
    f.write('''import os
import json
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from dotenv import load_dotenv

load_dotenv()

from app.database import init_db, seed_baseline_data, get_db
from app.models import (
    SOSCreate, FarmerRequestCreate, ClosureToggleRequest, ShelterUpdate, BroadcastSimulation
)
from app.weather_service import get_weather_data
from app.firms_service import get_hotspots_data
from app.rescue_engine import rescue_engine, haversine_km

init_db()
seed_baseline_data(force=False)

app = FastAPI(
    title="PRITHVI-ORBIT Disaster Intelligence & Action Command",
    description="Dual-Role Disaster Management Platform (Citizen Evacuee Portal + Admin Operations)",
    version="2.0.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
def health():
    return {
        "status": "OPERATIONAL",
        "system": "PRITHVI-ORBIT",
        "version": "2.0.0",
        "mode": os.getenv("APP_MODE", "demo"),
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "node": "Chandigarh-Mohali Hub"
    }

@app.get("/api/weather")
async def weather(lat: float = 30.7046, lon: float = 76.7179):
    return await get_weather_data(lat, lon)

@app.get("/api/fires")
async def fires():
    return await get_hotspots_data()

@app.post("/api/sos")
def submit_sos(sos: SOSCreate):
    conn = get_db()
    c = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    
    feasibility = rescue_engine.evaluate_rescue_feasibility(
        sos.lat, sos.lon, sos.party_size, sos.medical_flag, sos.mobility_flag
    )
    
    assigned_unit = None
    for unit in feasibility:
        if unit["feasible"]:
            assigned_unit = unit["unit_id"]
            break

    c.execute("""
        INSERT INTO sos_requests (lat, lon, reported_at, party_size, needs, description, status, assigned_unit_id, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, 'QUEUED', ?, 1)
    """, (sos.lat, sos.lon, now, sos.party_size, sos.needs, sos.description, assigned_unit))
    conn.commit()
    req_id = c.lastrowid
    conn.close()

    return {
        "sos_id": req_id,
        "status": "QUEUED_IN_COMMAND_CONSOLE",
        "assigned_unit": assigned_unit,
        "provenance": "SIMULATED_DEMO",
        "safety_disclaimer": "Simulated drill request. Real emergency services are NOT dispatched.",
        "feasibility_assessment": feasibility
    }

@app.get("/api/shelters/nearest")
def nearest_shelter(lat: float = 30.7046, lon: float = 76.7179):
    conn = get_db()
    rows = conn.execute("SELECT * FROM shelters WHERE status = 'OPEN'").fetchall()
    conn.close()
    
    if not rows:
        raise HTTPException(status_code=404, detail="No verified OPEN shelters currently available.")

    closest = None
    min_dist = float("inf")
    for r in rows:
        s = dict(r)
        d = haversine_km(lat, lon, s["lat"], s["lon"])
        if d < min_dist:
            min_dist = d
            closest = s
            closest["distance_km"] = d

    closest["facilities"] = json.loads(closest["facilities_json"])
    route_info = rescue_engine.find_candidate_route(lat, lon, closest["lat"], closest["lon"])
    gmaps_url = f"https://www.google.com/maps/dir/?api=1&origin={lat},{lon}&destination={closest['lat']},{closest['lon']}"
    
    return {
        "shelter": closest,
        "candidate_route": route_info,
        "google_maps_direct_link": gmaps_url,
        "provenance": "OFFICIAL_CIVIL_DEFENSE_DEMO"
    }

@app.get("/api/sos/active")
def get_active_sos():
    conn = get_db()
    rows = conn.execute("SELECT * FROM sos_requests ORDER BY id DESC").fetchall()
    conn.close()
    return {"provenance": "SIMULATED_DEMO", "requests": [dict(r) for r in rows]}

@app.post("/api/rescue/assign")
def assign_rescue(target_lat: float, target_lon: float, party_size: int, medical: bool = False, mobility: bool = False):
    rankings = rescue_engine.evaluate_rescue_feasibility(target_lat, target_lon, party_size, medical, mobility)
    return {
        "rankings": rankings,
        "provenance": "DEMO_FEASIBILITY_ENGINE"
    }

@app.get("/api/shelters")
def list_all_shelters():
    conn = get_db()
    rows = conn.execute("SELECT * FROM shelters ORDER BY id ASC").fetchall()
    conn.close()
    result = []
    for r in rows:
        d = dict(r)
        d["facilities"] = json.loads(d["facilities_json"])
        result.append(d)
    return {"shelters": result, "provenance": "DEMO_CIVIL_DEFENSE"}

@app.patch("/api/admin/shelters/{shelter_id}")
def update_shelter(shelter_id: int, payload: ShelterUpdate):
    conn = get_db()
    if payload.current_occupancy is not None:
        conn.execute("UPDATE shelters SET status = ?, current_occupancy = ? WHERE id = ?",
                     (payload.status.upper(), payload.current_occupancy, shelter_id))
    else:
        conn.execute("UPDATE shelters SET status = ? WHERE id = ?", (payload.status.upper(), shelter_id))
    conn.commit()
    conn.close()
    return {"status": "UPDATED", "shelter_id": shelter_id, "new_status": payload.status.upper()}

@app.get("/api/admin/closures")
def get_closures():
    return {"closures": rescue_engine.get_active_closures(), "provenance": "DEMO_ROAD_NETWORK"}

@app.post("/api/admin/closures/toggle")
def toggle_closure(req: ClosureToggleRequest):
    rescue_engine.set_closure(req.from_node, req.to_node, req.blocked, req.reason)
    return {
        "status": "STATUS_UPDATED",
        "closure": req.dict(),
        "active_closures": rescue_engine.get_active_closures(),
        "disclaimer": "Candidate route topologies updated across NetworkX graph."
    }

@app.post("/api/farm-requests")
def create_farm_request(req: FarmerRequestCreate):
    conn = get_db()
    c = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    c.execute("""
        INSERT INTO farmer_requests (farmer_name, contact, lat, lon, acres, service_type, status, created_at, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, 'QUEUED', ?, 1)
    """, (req.farmer_name, req.contact, req.lat, req.lon, req.acres, req.service_type, now))
    conn.commit()
    req_id = c.lastrowid
    conn.close()

    incentive = int(req.acres * 1500)
    return {
        "request_id": req_id,
        "status": "DISPATCH_QUEUED",
        "estimated_payout": f"₹{incentive:,}",
        "machinery_assigned": f"Custom Hiring Centre {req.service_type} #14",
        "provenance": "SIMULATED_DEMO",
        "disclaimer": "Simulated bio-pellet supply chain incentive. Forwarded to local KVK depot."
    }

@app.get("/api/farm-requests")
def list_farm_requests():
    conn = get_db()
    rows = conn.execute("SELECT * FROM farmer_requests ORDER BY id DESC").fetchall()
    conn.close()
    return {"provenance": "SIMULATED_DEMO", "requests": [dict(r) for r in rows]}

@app.post("/api/broadcast/simulate")
def simulate_broadcast(req: BroadcastSimulation):
    return {
        "status": "BROADCAST_TRANSMITTED",
        "recipients_reached": 184,
        "radius_km": req.radius_km,
        "channel": req.channel,
        "district": req.district,
        "timestamp": datetime.utcnow().isoformat() + "Z",
        "provenance": "SIMULATED_DEMO",
        "message_preview": (
            "⚠️ KISAN VERNACULAR ALERT: High thermal cluster observed downwind in your block. "
            "Do NOT incinerate paddy straw. Book subsidized Super Seeder & earn ₹1,500/acre via CHC."
        )
    }

@app.post("/api/demo/reset")
def reset_demo():
    seed_baseline_data(force=True)
    return {"status": "SUCCESS", "message": "Baseline demo dataset re-seeded."}

if os.path.exists("static"):
    app.mount("/", StaticFiles(directory="static", html=True), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("main:app", host="127.0.0.1", port=8001, reload=True)
''')

# 9. static/index.html
with open(os.path.join("static", "index.html"), "w", encoding="utf-8") as f:
    f.write('''<!DOCTYPE html>
<html lang="en">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>PRITHVI-ORBIT | Dual-Role Disaster Intelligence & Action Command</title>
  <script src="https://cdn.tailwindcss.com"></script>
  <link rel="stylesheet" href="https://unpkg.com/leaflet@1.9.4/dist/leaflet.css" />
  <script src="https://unpkg.com/leaflet@1.9.4/dist/leaflet.js"></script>
  <style>
    body { background-color: #070D18; color: #EDF4F8; font-family: ui-sans-serif, system-ui, sans-serif; }
    .bg-space { background-color: #070D18; }
    .bg-panel { background-color: #0E1B2F; }
    .bg-card { background-color: #14253F; }
    .border-subtle { border: 1px solid #1E3557; }
    .text-cyan-brand { color: #00F2FE; }
    .badge-obs { background-color: rgba(3, 105, 161, 0.25); color: #38bdf8; border: 1px solid rgba(56, 189, 248, 0.4); }
    .badge-forecast { background-color: rgba(180, 83, 9, 0.25); color: #fbbf24; border: 1px solid rgba(251, 191, 36, 0.4); }
    .badge-official { background-color: rgba(4, 120, 87, 0.25); color: #34d399; border: 1px solid rgba(52, 211, 153, 0.4); }
    .badge-demo { background-color: rgba(239, 68, 68, 0.25); color: #f87171; border: 1px solid rgba(248, 113, 113, 0.4); }
    #map-admin, #map-citizen { height: 100%; width: 100%; border-radius: 12px; }
  </style>
</head>
<body class="h-screen w-screen flex flex-col overflow-hidden select-none">
  <header class="h-[68px] bg-panel border-b border-subtle px-6 flex items-center justify-between shrink-0 z-40">
    <div class="flex items-center space-x-4">
      <div class="flex items-center justify-center h-10 w-10 rounded-xl bg-cyan-950 border border-cyan-800 text-2xl shadow-lg">🛰️</div>
      <div>
        <div class="flex items-center gap-2">
          <h1 class="text-lg font-black tracking-wider text-white">PRITHVI-ORBIT</h1>
          <span class="text-[9px] px-2 py-0.5 rounded font-mono font-bold badge-demo">SIMULATED DRILL</span>
        </div>
        <p class="text-[10px] text-cyan-brand font-mono">Location-Aware Disaster & Stubble Mitigation Command</p>
      </div>
    </div>

    <div class="bg-space border border-subtle p-1 rounded-xl flex items-center gap-1 shadow-inner">
      <button onclick="switchRole('citizen')" id="btn-role-citizen" class="px-4 py-2 rounded-lg text-xs font-bold transition flex items-center gap-2 bg-card text-white border border-cyan-500/30 shadow">
        <span>📱</span> <span>Citizen / Evacuee Portal</span>
      </button>
      <button onclick="switchRole('admin')" id="btn-role-admin" class="px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition flex items-center gap-2">
        <span>🛡️</span> <span>Disaster Command Console</span>
      </button>
    </div>

    <div class="flex items-center space-x-3 text-xs">
      <div class="bg-space border border-subtle px-3 py-1.5 rounded-lg flex items-center gap-2 shadow-sm">
        <span class="h-2 w-2 rounded-full bg-red-500 animate-pulse"></span>
        <span class="text-slate-400">Thermal Hotspots:</span>
        <span id="badge-hotspots-count" class="font-mono font-bold text-amber-400">Loading...</span>
        <span class="text-[8px] px-1 py-0.2 rounded font-mono badge-obs">OBS</span>
      </div>
      <div class="bg-space border border-subtle px-3 py-1.5 rounded-lg flex items-center gap-2 shadow-sm">
        <span class="text-slate-400">Wind:</span>
        <span id="badge-wind-telemetry" class="font-mono font-bold text-cyan-brand">-- km/h</span>
        <span class="text-[8px] px-1 py-0.2 rounded font-mono badge-forecast">FORECAST</span>
      </div>
      <button onclick="resetDemoData()" title="Re-seed Default Drill" class="px-2.5 py-1.5 rounded-lg bg-card hover:bg-slate-700 text-slate-300 text-xs border border-subtle font-mono">
        ↺ Reset
      </button>
    </div>
  </header>

  <!-- VIEW A: CITIZEN PORTAL -->
  <main id="view-citizen" class="flex-1 flex overflow-hidden">
    <div class="w-full md:w-[480px] bg-panel border-r border-subtle flex flex-col justify-between overflow-y-auto p-5 space-y-4 shrink-0">
      <div class="space-y-4">
        <div class="p-3 bg-amber-950/40 border border-amber-600/50 rounded-xl text-[11px] text-amber-200 space-y-1">
          <div class="font-bold flex items-center gap-1.5"><span>⚠️</span> <span>MANDATORY PUBLIC SAFETY NOTICE</span></div>
          <p class="leading-relaxed">Candidate route based on known closures. Not an operational safety guarantee. Comply with local civil defense instructions.</p>
        </div>

        <div class="p-4 bg-card border border-subtle rounded-2xl space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-xs font-bold text-white flex items-center gap-2"><span class="h-2.5 w-2.5 rounded-full bg-emerald-400 animate-ping"></span> Active GPS Coordinates</span>
            <span class="text-[9px] px-2 py-0.5 rounded font-mono badge-official">GPS ACTIVE (±4m)</span>
          </div>
          <div class="grid grid-cols-2 gap-2 text-xs">
            <div class="p-2 bg-space rounded-lg border border-subtle"><span class="text-slate-400 text-[10px] block">LATITUDE</span><span id="user-lat-val" class="font-mono font-bold text-white">30.7046</span></div>
            <div class="p-2 bg-space rounded-lg border border-subtle"><span class="text-slate-400 text-[10px] block">LONGITUDE</span><span id="user-lon-val" class="font-mono font-bold text-white">76.7179</span></div>
          </div>
          <div class="flex gap-2">
            <button onclick="captureCurrentLocation()" class="flex-1 py-2 bg-cyan-950 hover:bg-cyan-900 border border-cyan-700/60 text-cyan-brand rounded-lg text-xs font-bold transition">📍 Re-center Location</button>
            <button onclick="enableManualPinDrop()" class="px-3 py-2 bg-space hover:bg-slate-800 border border-subtle text-slate-300 rounded-lg text-xs font-medium">🗺️ Pin-Drop</button>
          </div>
        </div>

        <button onclick="openModal('modal-distress-sos')" class="w-full py-4 bg-red-600 hover:bg-red-500 active:scale-[0.99] transition rounded-2xl font-black text-sm tracking-wider text-white shadow-xl shadow-red-950/60 flex items-center justify-center gap-3 border border-red-400/40 cursor-pointer">
          <span class="text-2xl animate-bounce">🚨</span> <span>1-TAP FLOOD EMERGENCY SOS</span>
        </button>

        <div class="p-4 bg-card border border-subtle rounded-2xl space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-xs font-bold text-cyan-brand flex items-center gap-1.5"><span>🏕️</span> NEAREST VERIFIED OPEN SHELTER</span>
            <span class="text-[9px] px-2 py-0.5 rounded font-mono badge-official">VERIFIED OPEN</span>
          </div>
          <div id="nearest-shelter-box" class="space-y-2">
            <div class="font-bold text-white text-sm" id="nearest-shelter-title">Finding optimal shelter...</div>
            <div class="text-xs text-slate-400 flex items-center gap-3">
              <span>Distance: <b class="text-white font-mono" id="nearest-shelter-dist">-- km</b></span>
              <span>Available Capacity: <b class="text-emerald-400 font-mono" id="nearest-shelter-cap">--</b></span>
            </div>
            <div id="nearest-shelter-facilities" class="flex flex-wrap gap-1.5 pt-1"></div>
            <div class="pt-2 flex flex-col gap-2">
              <a id="btn-gmaps-link" href="#" target="_blank" class="w-full py-2.5 bg-emerald-600 hover:bg-emerald-500 text-white font-bold rounded-xl text-center text-xs flex items-center justify-center gap-2 shadow">
                <span>↗️</span> Direct Google Maps Navigation
              </a>
              <button onclick="focusEvacuationRoute()" class="w-full py-2 bg-space hover:bg-slate-800 text-cyan-brand border border-cyan-800/60 rounded-xl text-xs font-semibold">
                🛣️ Preview Candidate Evacuation Path
              </button>
            </div>
          </div>
        </div>

        <div class="p-4 bg-card border border-subtle rounded-2xl space-y-2">
          <span class="text-xs font-bold text-amber-400 flex items-center gap-1.5"><span>🔊</span> VERNACULAR AUDIO READOUT</span>
          <p class="text-[11px] text-slate-300">Listen to emergency evacuation and stubble guidance:</p>
          <div class="grid grid-cols-3 gap-2 pt-1">
            <button onclick="speakAdvisory('pa')" class="py-2 bg-space hover:bg-slate-800 border border-subtle rounded-lg text-xs font-bold text-white">ਪੰਜਾਬੀ (PA)</button>
            <button onclick="speakAdvisory('hi')" class="py-2 bg-space hover:bg-slate-800 border border-subtle rounded-lg text-xs font-bold text-white">हिन्दी (HI)</button>
            <button onclick="speakAdvisory('en')" class="py-2 bg-space hover:bg-slate-800 border border-subtle rounded-lg text-xs font-bold text-white">English (EN)</button>
          </div>
        </div>
      </div>
      <div class="pt-4 border-t border-subtle text-[10px] text-slate-500 flex justify-between">
        <span>PRITHVI-ORBIT Evacuee Deck</span><span>Version 2.0 • Hackathon Build</span>
      </div>
    </div>
    <div class="flex-1 p-4 relative bg-space"><div id="map-citizen"></div></div>
  </main>

  <!-- VIEW B: ADMIN CONSOLE -->
  <main id="view-admin" class="flex-1 flex overflow-hidden hidden">
    <div class="w-full md:w-[580px] bg-panel border-r border-subtle flex flex-col justify-between overflow-y-auto p-5 space-y-5 shrink-0">
      <div class="space-y-5">
        <div class="flex justify-between items-center border-b border-subtle pb-3">
          <div><h2 class="text-sm font-black tracking-wide text-white flex items-center gap-2"><span>🛡️</span> EMERGENCY OPERATIONS CONSOLE</h2></div>
          <span class="text-[9px] px-2 py-0.5 rounded font-mono badge-demo font-bold">ADMIN ACTIVE</span>
        </div>

        <div class="space-y-2.5">
          <div class="flex justify-between items-center">
            <span class="text-xs font-bold text-white flex items-center gap-1.5"><span>📋</span> LIVE CITIZEN SOS INCIDENT QUEUE</span>
            <button onclick="loadAdminSOSQueue()" class="text-[10px] text-cyan-brand hover:underline font-mono">Refresh Queue</button>
          </div>
          <div id="admin-sos-container" class="space-y-2 max-h-52 overflow-y-auto pr-1"></div>
        </div>

        <div class="p-4 bg-card border border-subtle rounded-2xl space-y-3">
          <div class="flex justify-between items-center">
            <span class="text-xs font-bold text-amber-400 flex items-center gap-1.5"><span>🚧</span> DYNAMIC ROAD CLOSURE SIMULATOR (NETWORKX)</span>
          </div>
          <div class="space-y-2 text-xs">
            <div class="p-2.5 bg-space rounded-xl border border-subtle flex justify-between items-center">
              <div><b class="text-white block">Kharar Junction &harr; Ropar Crossing</b><span class="text-[10px] text-slate-400 font-mono">NH-205 Lowland Culvert Segment</span></div>
              <button onclick="toggleRoadClosure('KHARAR_JUNCTION', 'ROPAR_CROSSING', this)" id="btn-toggle-kharar-ropar" class="px-3 py-1.5 rounded-lg text-xs font-bold bg-red-950 text-red-300 border border-red-700">FLOODED (CUT)</button>
            </div>
            <div class="p-2.5 bg-space rounded-xl border border-subtle flex justify-between items-center">
              <div><b class="text-white block">Mohali Center &harr; Kharar Junction</b><span class="text-[10px] text-slate-400 font-mono">Airport Road Arterial Extension</span></div>
              <button onclick="toggleRoadClosure('MOHALI_CENTER', 'KHARAR_JUNCTION', this)" id="btn-toggle-mohali-kharar" class="px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-950 text-emerald-300 border border-emerald-700">CLEAR (OPEN)</button>
            </div>
          </div>
        </div>

        <div class="p-4 bg-card border border-subtle rounded-2xl space-y-3">
          <div class="flex justify-between items-center"><span class="text-xs font-bold text-amber-500 flex items-center gap-1.5"><span>🔥</span> FARM FIRE STUBBLE MITIGATION & BROADCAST</span></div>
          <div class="grid grid-cols-2 gap-2">
            <button onclick="openModal('modal-farmer-request')" class="py-2.5 px-3 bg-emerald-600 hover:bg-emerald-500 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-2"><span>🚜</span> Book Baler / Seeder</button>
            <button onclick="triggerSimulatedBroadcast()" class="py-2.5 px-3 bg-amber-600 hover:bg-amber-500 text-white rounded-xl text-xs font-bold transition flex items-center justify-center gap-2"><span>📡</span> Broadcast Alert (15km)</button>
          </div>
          <div id="broadcast-confirm-msg" class="hidden p-2.5 bg-amber-950/60 border border-amber-700 rounded-xl text-amber-200 text-[11px]"></div>
        </div>

        <div class="space-y-2.5">
          <div class="flex justify-between items-center"><span class="text-xs font-bold text-white flex items-center gap-1.5"><span>🏕️</span> RELIEF SHELTER OPERATIONS STATUS</span></div>
          <div id="admin-shelters-list" class="space-y-2 text-xs"></div>
        </div>
      </div>
      <div class="pt-4 border-t border-subtle text-[10px] text-slate-500 flex justify-between">
        <span>Admin Security: Local Demo Mode</span><span>PRITHVI-ORBIT Command</span>
      </div>
    </div>
    <div class="flex-1 p-4 relative bg-space"><div id="map-admin"></div></div>
  </main>

  <!-- MODAL: SOS -->
  <div id="modal-distress-sos" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-[9999] hidden flex items-center justify-center p-4">
    <div class="bg-panel border border-subtle max-w-md w-full rounded-3xl p-6 text-slate-100 space-y-4 shadow-2xl">
      <div class="flex justify-between items-center border-b border-subtle pb-3">
        <h3 class="font-bold text-base text-red-400">🚨 Citizen Distress SOS Request</h3>
        <button onclick="closeModal('modal-distress-sos')" class="text-slate-400 text-xl font-bold">&times;</button>
      </div>
      <div class="space-y-3 text-xs">
        <div>
          <label class="block text-slate-400 mb-1">Target Coordinates</label>
          <input type="text" id="input-sos-coords" value="30.7046, 76.7179" readonly class="w-full bg-space border border-subtle p-2.5 rounded-xl font-mono text-cyan-brand">
        </div>
        <div>
          <label class="block text-slate-400 mb-1">Party Size</label>
          <input type="number" id="input-sos-party" value="5" min="1" max="40" class="w-full bg-space border border-subtle p-2.5 rounded-xl text-white font-bold">
        </div>
        <div class="grid grid-cols-2 gap-2">
          <label class="flex items-center gap-2 p-2.5 bg-space rounded-xl border border-subtle cursor-pointer">
            <input type="checkbox" id="chk-sos-medical" class="rounded bg-card text-red-500">
            <span>Critical Medical</span>
          </label>
          <label class="flex items-center gap-2 p-2.5 bg-space rounded-xl border border-subtle cursor-pointer">
            <input type="checkbox" id="chk-sos-mobility" class="rounded bg-card text-red-500">
            <span>Wheelchair / Infant</span>
          </label>
        </div>
        <div>
          <label class="block text-slate-400 mb-1">Urgent Remarks</label>
          <input type="text" id="input-sos-desc" placeholder="Water reached ground floor" class="w-full bg-space border border-subtle p-2.5 rounded-xl text-white">
        </div>
        <div id="sos-dispatch-result" class="hidden p-3 bg-red-950/60 border border-red-700/60 rounded-xl space-y-1 text-red-200"></div>
      </div>
      <div class="flex gap-2 pt-2">
        <button onclick="dispatchCitizenSOS()" class="flex-1 py-3 bg-red-600 hover:bg-red-500 font-bold rounded-xl text-white text-xs">Transmit Emergency Dispatch Call</button>
        <button onclick="closeModal('modal-distress-sos')" class="py-3 px-5 bg-card rounded-xl text-xs">Dismiss</button>
      </div>
    </div>
  </div>

  <!-- MODAL: FARMER -->
  <div id="modal-farmer-request" class="fixed inset-0 bg-black/80 backdrop-blur-sm z-[9999] hidden flex items-center justify-center p-4">
    <div class="bg-panel border border-subtle max-w-md w-full rounded-3xl p-6 text-slate-100 space-y-4 shadow-2xl">
      <div class="flex justify-between items-center border-b border-subtle pb-3">
        <h3 class="font-bold text-base text-emerald-400">🚜 Residue Machinery & Incentive Booking</h3>
        <button onclick="closeModal('modal-farmer-request')" class="text-slate-400 text-xl font-bold">&times;</button>
      </div>
      <div class="space-y-3 text-xs">
        <div><label class="block text-slate-400 mb-1">Farmer Full Name</label><input type="text" id="input-farm-name" value="Sardar Gurmeet Singh" class="w-full bg-space border border-subtle p-2.5 rounded-xl text-white"></div>
        <div><label class="block text-slate-400 mb-1">Mobile / WhatsApp</label><input type="text" id="input-farm-contact" value="+91 98140 12345" class="w-full bg-space border border-subtle p-2.5 rounded-xl text-white"></div>
        <div><label class="block text-slate-400 mb-1">Residue Field Acreage</label><input type="number" id="input-farm-acres" value="8" min="1" max="200" class="w-full bg-space border border-subtle p-2.5 rounded-xl text-white font-bold"></div>
        <div>
          <label class="block text-slate-400 mb-1">Equipment</label>
          <select id="select-farm-service" class="w-full bg-space border border-subtle p-2.5 rounded-xl text-white">
            <option value="Biomass Baler Unit">High-Speed Biomass Baler (₹1,500/Acre)</option>
            <option value="Super Seeder Combine">Super Seeder (In-Situ Wheat Sowing)</option>
          </select>
        </div>
        <div><label class="block text-slate-400 mb-1">Guaranteed Incentive</label><input type="text" id="input-farm-payout-calc" value="₹12,000" readonly class="w-full bg-emerald-950/50 border border-emerald-700/60 p-2.5 rounded-xl font-bold text-emerald-300"></div>
        <div id="farm-booking-result" class="hidden p-3 bg-emerald-950/60 border border-emerald-700/60 rounded-xl space-y-1 text-emerald-200"></div>
      </div>
      <div class="flex gap-2 pt-2">
        <button onclick="submitFarmerBooking()" class="flex-1 py-3 bg-emerald-600 hover:bg-emerald-500 font-bold rounded-xl text-white text-xs">Confirm Machinery Allocation</button>
        <button onclick="closeModal('modal-farmer-request')" class="py-3 px-5 bg-card rounded-xl text-xs">Close</button>
      </div>
    </div>
  </div>

  <script>
    let currentRole = 'citizen';
    let userCoords = [30.7046, 76.7179];
    let mapCitizen = null, mapAdmin = null;
    let citizenRouteLayer = null, adminRouteLayer = null;
    let cachedNearestShelter = null;

    window.addEventListener('DOMContentLoaded', () => {
      initCitizenMap();
      fetchTelemetry();
      fetchNearestShelter();
      setupCalculators();
    });

    function initCitizenMap() {
      mapCitizen = L.map('map-citizen', { zoomControl: false }).setView(userCoords, 9);
      L.control.zoom({ position: 'bottomright' }).addTo(mapCitizen);
      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri World Imagery', maxZoom: 18
      }).addTo(mapCitizen);
      citizenRouteLayer = L.layerGroup().addTo(mapCitizen);
      L.circleMarker(userCoords, { radius: 9, fillColor: "#00F2FE", color: "#FFFFFF", weight: 2, fillOpacity: 0.95 }).addTo(mapCitizen).bindPopup("<b>📍 Your Active Location</b><br/>Mohali-Kharar Sector").openPopup();
    }

    function initAdminMap() {
      if (mapAdmin) return;
      mapAdmin = L.map('map-admin', { zoomControl: false }).setView([30.75, 76.4], 9);
      L.control.zoom({ position: 'bottomright' }).addTo(mapAdmin);
      L.tileLayer('https://server.arcgisonline.com/ArcGIS/rest/services/World_Imagery/MapServer/tile/{z}/{y}/{x}', {
        attribution: 'Tiles &copy; Esri World Imagery', maxZoom: 18
      }).addTo(mapAdmin);
      adminRouteLayer = L.layerGroup().addTo(mapAdmin);

      fetch('/api/fires').then(r => r.json()).then(res => {
        (res.data || []).forEach(p => {
          L.circleMarker([p.lat, p.lon], { radius: 8, fillColor: "#EF4444", color: "#FFFFFF", weight: 1.5, fillOpacity: 0.9 }).addTo(mapAdmin).bindPopup(`
            <div style="font-family:system-ui; font-size:11px;">
              <b style="color:#DC2626;">🛰️ Satellite Hotspot</b><br/>
              <b>Coords:</b> ${p.lat.toFixed(3)}, ${p.lon.toFixed(3)}<br/>
              <b>FRP:</b> ${p.frp} MW &bull; <b>Confidence:</b> ${p.confidence}<br/>
              <span style="background:#0369a1; color:white; padding:1px 4px; border-radius:3px; font-size:9px;">[OBSERVATION]</span>
            </div>
          `);
        });
      });
    }

    function switchRole(role) {
      currentRole = role;
      document.getElementById('view-citizen').classList.toggle('hidden', role !== 'citizen');
      document.getElementById('view-admin').classList.toggle('hidden', role === 'citizen');
      document.getElementById('btn-role-citizen').className = role === 'citizen' ? "px-4 py-2 rounded-lg text-xs font-bold transition flex items-center gap-2 bg-card text-white border border-cyan-500/30 shadow" : "px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition flex items-center gap-2";
      document.getElementById('btn-role-admin').className = role === 'admin' ? "px-4 py-2 rounded-lg text-xs font-bold transition flex items-center gap-2 bg-card text-white border border-cyan-500/30 shadow" : "px-4 py-2 rounded-lg text-xs font-semibold text-slate-400 hover:text-white transition flex items-center gap-2";
      
      if (role === 'citizen') {
        setTimeout(() => mapCitizen.invalidateSize(), 100);
      } else {
        initAdminMap();
        setTimeout(() => mapAdmin.invalidateSize(), 100);
        loadAdminSOSQueue();
        loadAdminShelters();
      }
    }

    function fetchTelemetry() {
      fetch('/api/weather').then(r => r.json()).then(w => {
        document.getElementById('badge-wind-telemetry').innerText = `${w.wind_speed} km/h (${w.wind_direction}°)`;
      });
      fetch('/api/fires').then(r => r.json()).then(f => {
        document.getElementById('badge-hotspots-count').innerText = `${f.active_hotspots} Hotspots`;
      });
    }

    function captureCurrentLocation() {
      if (navigator.geolocation) {
        navigator.geolocation.getCurrentPosition((pos) => {
          userCoords = [pos.coords.latitude, pos.coords.longitude];
          document.getElementById('user-lat-val').innerText = userCoords[0].toFixed(4);
          document.getElementById('user-lon-val').innerText = userCoords[1].toFixed(4);
          document.getElementById('input-sos-coords').value = `${userCoords[0].toFixed(4)}, ${userCoords[1].toFixed(4)}`;
          mapCitizen.setView(userCoords, 10);
          fetchNearestShelter();
        });
      }
    }

    function enableManualPinDrop() {
      alert("Click on map to drop your distress location pin.");
      mapCitizen.once('click', (e) => {
        userCoords = [e.latlng.lat, e.latlng.lng];
        document.getElementById('user-lat-val').innerText = userCoords[0].toFixed(4);
        document.getElementById('user-lon-val').innerText = userCoords[1].toFixed(4);
        document.getElementById('input-sos-coords').value = `${userCoords[0].toFixed(4)}, ${userCoords[1].toFixed(4)}`;
        fetchNearestShelter();
      });
    }

    function fetchNearestShelter() {
      fetch(`/api/shelters/nearest?lat=${userCoords[0]}&lon=${userCoords[1]}`).then(r => r.json()).then(data => {
        cachedNearestShelter = data;
        const s = data.shelter;
        document.getElementById('nearest-shelter-title').innerText = s.label;
        document.getElementById('nearest-shelter-dist').innerText = `${s.distance_km} km`;
        document.getElementById('nearest-shelter-cap').innerText = `${s.capacity - s.current_occupancy} beds available`;
        document.getElementById('nearest-shelter-facilities').innerHTML = s.facilities.map(f => `<span class="text-[9px] px-2 py-0.5 rounded bg-space border border-subtle text-slate-300">${f}</span>`).join('');
        document.getElementById('btn-gmaps-link').href = data.google_maps_direct_link;

        citizenRouteLayer.clearLayers();
        L.circleMarker([s.lat, s.lon], { radius: 10, fillColor: "#10B981", color: "#FFFFFF", weight: 2, fillOpacity: 0.95 }).addTo(citizenRouteLayer).bindPopup(`<b>🏕️ Open Shelter</b><br/>${s.label}`);

        if (data.candidate_route && data.candidate_route.route_found) {
          const poly = L.polyline(data.candidate_route.coordinates, { color: '#00F2FE', weight: 4.5, dashArray: '6, 6' }).addTo(citizenRouteLayer);
          mapCitizen.fitBounds(poly.getBounds(), { padding: [50, 50] });
        }
      });
    }

    function focusEvacuationRoute() {
      if (cachedNearestShelter && cachedNearestShelter.candidate_route) {
        alert(`Candidate Route Time: ~${cachedNearestShelter.candidate_route.estimated_minutes} mins.\nAvoided Flooded Cuts: ${cachedNearestShelter.candidate_route.blocked_edges_avoided.join(', ')}`);
      }
    }

    function dispatchCitizenSOS() {
      const party = parseInt(document.getElementById('input-sos-party').value);
      const med = document.getElementById('chk-sos-medical').checked;
      const mob = document.getElementById('chk-sos-mobility').checked;
      const desc = document.getElementById('input-sos-desc').value;

      fetch('/api/sos', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ lat: userCoords[0], lon: userCoords[1], party_size: party, medical_flag: med, mobility_flag: mob, description: desc })
      }).then(r => r.json()).then(d => {
        const box = document.getElementById('sos-dispatch-result');
        box.classList.remove('hidden');
        const topUnit = d.feasibility_assessment[0];
        box.innerHTML = `
          <div class="font-bold">✅ Incident #${d.sos_id} Transmitted!</div>
          <div class="text-[11px]">Assigned Asset: <b>${topUnit.label}</b> (${topUnit.distance_km} km away).</div>
        `;
      });
    }

    function loadAdminSOSQueue() {
      fetch('/api/sos/active').then(r => r.json()).then(d => {
        const c = document.getElementById('admin-sos-container');
        c.innerHTML = d.requests.length ? d.requests.map(req => `
          <div class="p-3 bg-space rounded-xl border border-subtle">
            <div class="flex justify-between items-center"><b class="text-white">SOS Incident #${req.id}</b><span class="text-[9px] px-1.5 py-0.5 rounded badge-demo">${req.status}</span></div>
            <div class="text-[11px] text-slate-300">Party: ${req.party_size} persons &bull; Coords: ${req.lat.toFixed(3)}, ${req.lon.toFixed(3)}</div>
            <div class="text-[10px] text-cyan-brand font-mono">Assigned Asset: ${req.assigned_unit_id || 'Feasibility Evaluating'}</div>
          </div>
        `).join('') : '<div class="p-3 bg-card rounded-xl text-slate-400 text-xs">No active incidents queued.</div>';
      });
    }

    function toggleRoadClosure(fromN, toN, btn) {
      const isBlocked = btn.innerText.includes("CUT");
      fetch('/api/admin/closures/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ from_node: fromN, to_node: toN, blocked: !isBlocked, reason: "Simulated Embankment Breach" })
      }).then(r => r.json()).then(() => {
        btn.className = !isBlocked ? "px-3 py-1.5 rounded-lg text-xs font-bold bg-red-950 text-red-300 border border-red-700" : "px-3 py-1.5 rounded-lg text-xs font-bold bg-emerald-950 text-emerald-300 border border-emerald-700";
        btn.innerText = !isBlocked ? "FLOODED (CUT)" : "CLEAR (OPEN)";
        fetchNearestShelter();
      });
    }

    function loadAdminShelters() {
      fetch('/api/shelters').then(r => r.json()).then(d => {
        document.getElementById('admin-shelters-list').innerHTML = d.shelters.map(s => `
          <div class="p-3 bg-space rounded-xl border border-subtle flex justify-between items-center">
            <div><b class="text-white block">${s.label}</b><span class="text-[10px] text-slate-400">Occupancy: ${s.current_occupancy} / ${s.capacity} beds</span></div>
            <div class="flex gap-1.5">
              <button onclick="changeShelterStatus(${s.id}, 'OPEN')" class="px-2 py-1 rounded text-[10px] font-bold ${s.status === 'OPEN' ? 'bg-emerald-900 text-emerald-300 border border-emerald-600' : 'bg-card text-slate-400'}">OPEN</button>
              <button onclick="changeShelterStatus(${s.id}, 'CLOSED')" class="px-2 py-1 rounded text-[10px] font-bold ${s.status === 'CLOSED' ? 'bg-red-900 text-red-300 border border-red-600' : 'bg-card text-slate-400'}">CLOSED</button>
            </div>
          </div>
        `).join('');
      });
    }

    function changeShelterStatus(id, st) {
      fetch(`/api/admin/shelters/${id}`, { method: 'PATCH', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ status: st }) }).then(() => {
        loadAdminShelters();
        fetchNearestShelter();
      });
    }

    function setupCalculators() {
      document.getElementById('input-farm-acres').addEventListener('input', (e) => {
        const acres = Number(e.target.value) || 0;
        document.getElementById('input-farm-payout-calc').value = `₹${(acres * 1500).toLocaleString('en-IN')}`;
      });
    }

    function submitFarmerBooking() {
      fetch('/api/farm-requests', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          farmer_name: document.getElementById('input-farm-name').value,
          contact: document.getElementById('input-farm-contact').value,
          acres: parseFloat(document.getElementById('input-farm-acres').value),
          service_type: document.getElementById('select-farm-service').value
        })
      }).then(r => r.json()).then(d => {
        const box = document.getElementById('farm-booking-result');
        box.classList.remove('hidden');
        box.innerHTML = `✅ <b>Allocation Confirmed (#${d.request_id})</b><br/>Incentive: ${d.estimated_payout} &bull; ${d.machinery_assigned}`;
      });
    }

    function triggerSimulatedBroadcast() {
      fetch('/api/broadcast/simulate', { method: 'POST', headers: { 'Content-Type': 'application/json' }, body: JSON.stringify({ radius_km: 15.0 }) }).then(r => r.json()).then(d => {
        const msg = document.getElementById('broadcast-confirm-msg');
        msg.classList.remove('hidden');
        msg.innerHTML = `📡 <b>Broadcast Sent!</b> Transmitted to <b>${d.recipients_reached} registered farmers</b>.`;
        setTimeout(() => msg.classList.add('hidden'), 5000);
      });
    }

    function speakAdvisory(lang) {
      if (!('speechSynthesis' in window)) return;
      window.speechSynthesis.cancel();
      let text = lang === 'pa' ? "ਸਾਵਧਾਨ! ਹੜ੍ਹ ਅਤੇ ਪਰਾਲੀ ਦੇ ਧੂੰਏਂ ਕਾਰਨ ਨਜ਼ਦੀਕੀ ਰਾਹਤ ਕੈਂਪ ਵਿੱਚ ਪਹੁੰਚੋ। ਪਰਾਲੀ ਨੂੰ ਅੱਗ ਨਾ ਲਗਾਓ, ਸਰਕਾਰੀ ਬੇਲਰ ਬੁੱਕ ਕਰੋ।" : (lang === 'hi' ? "सावधान! बाढ़ एवं पराली धुएं की स्थिति में नजदीकी राहत शिविर की ओर प्रस्थान करें। अवशेष न जलाएं, बेलर मशीनरी का लाभ उठाएं।" : "Emergency Advisory: Please proceed to your nearest verified relief shelter. Do not burn crop residue.");
      let utter = new SpeechSynthesisUtterance(text);
      utter.lang = lang === 'pa' ? 'pa-IN' : (lang === 'hi' ? 'hi-IN' : 'en-IN');
      window.speechSynthesis.speak(utter);
    }

    function resetDemoData() {
      if (confirm("Reset local drill dataset?")) fetch('/api/demo/reset', { method: 'POST' }).then(() => location.reload());
    }

    function openModal(id) { document.getElementById(id).classList.remove('hidden'); }
    function closeModal(id) { document.getElementById(id).classList.add('hidden'); }
  </script>
</body>
</html>
''')

print("✅ SARI 7 FILES SUCCESSFULLY CREATE HO GAYI HAIN!")