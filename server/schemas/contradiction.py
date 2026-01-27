from pydantic import BaseModel
from typing import Optional, Literal

class Contradiction(BaseModel):
    source: str
    target: str
    type: str
    confidence: float
    edge_type: str
    edge_score: Optional[float] = None
    
    evidence_a: str = ""
    evidence_b: str = ""
    
    evidence_a_bbox: list[float] | None = None
    evidence_b_bbox: list[float] | None = None
    
    evidence_a_page: int | None = None
    evidence_b_page: int | None = None
    
    summary: str = ""
    score: float = 0.0