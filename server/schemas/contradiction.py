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
    summary: str = ""
    score: float = 0.0