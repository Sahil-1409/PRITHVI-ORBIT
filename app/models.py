from pydantic import BaseModel, Field
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
