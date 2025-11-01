# wicklyu/schemas.py
from pydantic import BaseModel, Field
from typing import Optional

class DetectionIn(BaseModel):
    symbol: str = Field(..., min_length=1, max_length=20)
    timeframe: Optional[str] = Field("1D", pattern=r"^\d+[HDWM]$")

class DetectionOut(BaseModel):
    id: int
    symbol: str
    timeframe: str