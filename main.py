import os
import json
import socket
from datetime import datetime
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
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
from pydantic import BaseModel
from typing import Optional

init_db()
seed_baseline_data(force=False)

def init_advanced_tables():
    conn = get_db()
    c = conn.cursor()
    c.execute("""
    CREATE TABLE IF NOT EXISTS fire_sos_requests (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_name TEXT NOT NULL,
        user_phone TEXT NOT NULL,
        fire_cause TEXT NOT NULL,
        lat REAL NOT NULL,
        lon REAL NOT NULL,
        remarks TEXT,
        status TEXT DEFAULT 'PENDING_DISPATCH',
        assigned_team TEXT,
        created_at TEXT NOT NULL,
        is_demo INTEGER DEFAULT 1
    );
    """)
    conn.commit()
    conn.close()

init_advanced_tables()

app = FastAPI(
    title="PRITHVI-ORBIT Command Core",
    description="Synchronized Multi-Role Emergency Platform",
    version="2.6.0"
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

class FireSOSCreate(BaseModel):
    user_name: str
    user_phone: str
    fire_cause: str
    lat: float
    lon: float
    remarks: Optional[str] = ""

class FireAssignPayload(BaseModel):
    team_name: str

class ParaliSellCreate(BaseModel):
    farmer_name: str
    farmer_phone: str
    lat: float
    lon: float
    acres: float
    straw_type: str = "Basmati / Non-Basmati Paddy"

class OrderStatusUpdate(BaseModel):
    status: str

class AssignRescuePayload(BaseModel):
    unit_id: str

@app.get("/")
def serve_index():
    return FileResponse("static/index.html")

@app.get("/api/health")
def health():
    return {"status": "OPERATIONAL", "timestamp": datetime.utcnow().isoformat() + "Z"}

@app.get("/api/network-ip")
def get_network_ip():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        s.connect(("8.8.8.8", 80))
        local_ip = s.getsockname()[0]
        s.close()
    except Exception:
        local_ip = "127.0.0.1"
    return {"local_ip": local_ip, "port": 8001, "shareable_url": f"http://{local_ip}:8001"}

@app.get("/api/weather")
async def weather(lat: float = 30.7046, lon: float = 76.7179):
    return await get_weather_data(lat, lon)

@app.get("/api/fires")
async def fires():
    return await get_hotspots_data()

@app.get("/api/flood-zones")
def get_flood_zones():
    return {
        "flood_zones": [
            {
                "id": "ZONE_SUTLEJ_ROPAR",
                "label": "Ropar Sutlej Lowland Embankment",
                "domain": "Sutlej River Basin",
                "lat": 30.9664,
                "lon": 76.5331,
                "water_level": "3.8m (Above Danger Mark)",
                "status": "ACTIVE_FLOOD_INUNDATION"
            },
            {
                "id": "ZONE_GHAGGAR_PATIALA",
                "label": "Ghaggar River Culvert Overflow",
                "domain": "Ghaggar Basin Corridors",
                "lat": 30.3398,
                "lon": 76.3869,
                "water_level": "2.1m (Rapidly Rising)",
                "status": "MODERATE_SUBMERGENCE"
            },
            {
                "id": "ZONE_KHARAR_LOWLAND",
                "label": "Kharar NH-205 Drainage Breach",
                "domain": "NH-205 Lowland Culverts",
                "lat": 30.7499,
                "lon": 76.6411,
                "water_level": "1.5m Roadway Cut",
                "status": "ROAD_JAM_FLOODED"
            }
        ]
    }

# --- AgniNetra Fire SOS Endpoints ---
@app.post("/api/fire-sos")
def report_fire_sos(req: FireSOSCreate):
    conn = get_db()
    c = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    c.execute("""
        INSERT INTO fire_sos_requests (user_name, user_phone, fire_cause, lat, lon, remarks, status, created_at, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, 'PENDING_DISPATCH', ?, 1)
    """, (req.user_name, req.user_phone, req.fire_cause, req.lat, req.lon, req.remarks, now))
    conn.commit()
    req_id = c.lastrowid
    conn.close()
    return {"fire_sos_id": req_id, "status": "PENDING_DISPATCH", "reported_at": now}

# Returns only unassigned fire alerts for active screen
@app.get("/api/fire-sos/active")
def get_active_fire_sos(include_assigned: bool = False):
    conn = get_db()
    if include_assigned:
        rows = conn.execute("SELECT * FROM fire_sos_requests ORDER BY id DESC").fetchall()
    else:
        rows = conn.execute("SELECT * FROM fire_sos_requests WHERE status = 'PENDING_DISPATCH' ORDER BY id DESC").fetchall()
    conn.close()
    return {"fire_requests": [dict(r) for r in rows]}

@app.post("/api/fire-sos/{fire_id}/assign")
def assign_fire_team(fire_id: int, payload: FireAssignPayload):
    conn = get_db()
    conn.execute("""
        UPDATE fire_sos_requests 
        SET status = 'TEAM_DISPATCHED', assigned_team = ? 
        WHERE id = ?
    """, (payload.team_name, fire_id))
    conn.commit()
    conn.close()
    return {"status": "SUCCESS", "fire_id": fire_id, "assigned_team": payload.team_name}

# --- Flood SOS & Rescue Fleet Dispatch ---
@app.post("/api/sos")
def submit_sos(sos: SOSCreate):
    conn = get_db()
    c = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    
    feasibility = rescue_engine.evaluate_rescue_feasibility(
        sos.lat, sos.lon, sos.party_size, sos.medical_flag, sos.mobility_flag
    )
    top_unit = feasibility[0] if feasibility else None
    assigned_unit_id = top_unit["unit_id"] if top_unit else "NDRF_ZODIAC_01"

    c.execute("""
        INSERT INTO sos_requests (lat, lon, reported_at, party_size, needs, description, status, assigned_unit_id, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, 'QUEUED', ?, 1)
    """, (sos.lat, sos.lon, now, sos.party_size, sos.needs, sos.description, assigned_unit_id))
    conn.commit()
    req_id = c.lastrowid
    conn.close()

    dist = top_unit["distance_km"] if top_unit else 4.2
    eta_mins = round((dist / 35.0) * 60 + 8)

    return {
        "sos_id": req_id,
        "status": "QUEUED",
        "assigned_unit": top_unit["label"] if top_unit else "NDRF Tactical Unit",
        "unit_id": assigned_unit_id,
        "distance_km": dist,
        "eta_minutes": eta_mins,
        "reported_at": now
    }

# Active Flood SOS: Assigned ya Dispatched requests active queue se filter ho jayengi
@app.get("/api/sos/active")
def get_active_sos(fresh_only: bool = True):
    conn = get_db()
    # Sirf wo requests dikhayenge jo abhi dispatch nahi hui hain
    if fresh_only:
        rows = conn.execute("""
            SELECT * FROM sos_requests 
            WHERE status NOT IN ('RESCUE_DISPATCHED', 'RESOLVED') 
            ORDER BY id DESC
        """).fetchall()
    else:
        rows = conn.execute("SELECT * FROM sos_requests ORDER BY id DESC").fetchall()
    conn.close()
    return {"requests": [dict(r) for r in rows]}

@app.post("/api/sos/{sos_id}/assign")
def assign_sos_team(sos_id: int, payload: AssignRescuePayload):
    conn = get_db()
    c = conn.cursor()
    c.execute("""
        UPDATE sos_requests 
        SET status = 'RESCUE_DISPATCHED', assigned_unit_id = ?
        WHERE id = ?
    """, (payload.unit_id, sos_id))
    conn.commit()  # Database commit ensure kiya gaya
    conn.close()
    return {"status": "SUCCESS", "sos_id": sos_id, "assigned_unit": payload.unit_id}

@app.get("/api/rescue/navigate/{sos_id}")
def generate_rescue_navigation(sos_id: int):
    conn = get_db()
    sos_row = conn.execute("SELECT * FROM sos_requests WHERE id = ?", (sos_id,)).fetchone()
    if not sos_row:
        conn.close()
        raise HTTPException(status_code=404, detail="SOS record not found")
    
    sos = dict(sos_row)
    unit_id = sos.get("assigned_unit_id") or "NDRF_ZODIAC_01"
    unit_row = conn.execute("SELECT * FROM rescue_units WHERE id = ?", (unit_id,)).fetchone()
    conn.close()

    unit_lat, unit_lon = (unit_row["lat"], unit_row["lon"]) if unit_row else (30.7300, 76.7000)
    unit_label = unit_row["label"] if unit_row else "NDRF Base Sector 62"

    route_info = rescue_engine.find_candidate_route(unit_lat, unit_lon, sos["lat"], sos["lon"])
    gmaps_nav = f"https://www.google.com/maps/dir/?api=1&origin={unit_lat},{unit_lon}&destination={sos['lat']},{sos['lon']}&travelmode=driving"

    return {
        "sos_id": sos_id,
        "victim_coords": [sos["lat"], sos["lon"]],
        "party_size": sos["party_size"],
        "assigned_unit": unit_label,
        "unit_coords": [unit_lat, unit_lon],
        "candidate_route": route_info,
        "google_maps_direct_link": gmaps_nav
    }

# --- Parali Orders Management ---
@app.post("/api/parali/sell")
def sell_parali(req: ParaliSellCreate):
    conn = get_db()
    c = conn.cursor()
    now = datetime.utcnow().isoformat() + "Z"
    payout = int(req.acres * 1500)
    c.execute("""
        INSERT INTO farmer_requests (farmer_name, contact, lat, lon, acres, service_type, status, created_at, is_demo)
        VALUES (?, ?, ?, ?, ?, ?, 'PENDING_APPROVAL', ?, 1)
    """, (req.farmer_name, req.farmer_phone, req.lat, req.lon, req.acres, f"Parali Kharid ({req.straw_type})", now))
    conn.commit()
    req_id = c.lastrowid
    conn.close()
    return {
        "order_id": req_id,
        "farmer_name": req.farmer_name,
        "acres": req.acres,
        "payout": f"₹{payout:,}",
        "status": "PENDING_APPROVAL"
    }

@app.get("/api/parali/orders")
def get_parali_orders():
    conn = get_db()
    rows = conn.execute("""
        SELECT * FROM farmer_requests 
        WHERE status IN ('PENDING_APPROVAL', 'ONGOING_COLLECTION', 'BUYER_MATCHED')
        ORDER BY id DESC
    """).fetchall()
    conn.close()
    return {"orders": [dict(r) for r in rows]}

# User specific endpoint to fetch latest order status (to track if REJECTED or APPROVED)
@app.get("/api/parali/user-status")
def get_user_parali_status(phone: str):
    conn = get_db()
    row = conn.execute("SELECT * FROM farmer_requests WHERE contact = ? ORDER BY id DESC LIMIT 1", (phone,)).fetchone()
    conn.close()
    if not row:
        return {"found": False}
    return {"found": True, "order": dict(row)}

@app.patch("/api/parali/orders/{order_id}")
def update_parali_status(order_id: int, payload: OrderStatusUpdate):
    conn = get_db()
    conn.execute("UPDATE farmer_requests SET status = ? WHERE id = ?", (payload.status.upper(), order_id))
    conn.commit()
    conn.close()
    return {"status": "UPDATED", "order_id": order_id, "new_status": payload.status.upper()}

# --- Shelters & Closures ---
@app.get("/api/shelters")
def list_shelters():
    conn = get_db()
    rows = conn.execute("SELECT * FROM shelters ORDER BY id ASC").fetchall()
    conn.close()
    res = []
    for r in rows:
        d = dict(r)
        d["facilities"] = json.loads(d["facilities_json"])
        res.append(d)
    return {"shelters": res}

@app.patch("/api/admin/shelters/{shelter_id}")
def toggle_shelter_status(shelter_id: int, payload: ShelterUpdate):
    conn = get_db()
    conn.execute("UPDATE shelters SET status = ? WHERE id = ?", (payload.status.upper(), shelter_id))
    conn.commit()
    conn.close()
    return {"status": "UPDATED", "shelter_id": shelter_id, "new_status": payload.status.upper()}

@app.get("/api/admin/closures")
def get_closures():
    return {"closures": rescue_engine.get_active_closures()}

@app.post("/api/admin/closures/toggle")
def toggle_closure(req: ClosureToggleRequest):
    rescue_engine.set_closure(req.from_node, req.to_node, req.blocked, req.reason)
    return {"status": "UPDATED", "closure": req.dict(), "active_closures": rescue_engine.get_active_closures()}

@app.post("/api/routes/candidate")
def get_candidate_route(origin_lat: float, origin_lon: float, dest_lat: float, dest_lon: float):
    return rescue_engine.find_candidate_route(origin_lat, origin_lon, dest_lat, dest_lon)

if os.path.exists("static"):
    app.mount("/static", StaticFiles(directory="static"), name="static")

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(
        "main:app",
        host="0.0.0.0",
        port=8001,
        reload=False,
        timeout_keep_alive=99990,
        timeout_graceful_shutdown=30
    )