from pydantic import BaseModel, Field
from typing import Any, List, Dict
from .document import Paragraph
from .contradiction import Contradiction

class Edge(BaseModel):
    source: str
    target: str
    type: str
    score: float | None = None
    ref_label: str | None = None
    ref_value: str | None = None

class Graph(BaseModel):
    nodes: List[Paragraph]
    edges: List[Edge]
    contradictions: List[Contradiction] = []
