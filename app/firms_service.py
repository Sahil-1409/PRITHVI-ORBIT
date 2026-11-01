import os
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
