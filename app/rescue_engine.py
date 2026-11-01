import networkx as nx
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
