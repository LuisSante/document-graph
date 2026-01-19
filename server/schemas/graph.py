from pydantic import BaseModel, Field
from typing import Any, List, Dict
from .document import Paragraph

class Edge(BaseModel):
    source: str
    target: str
    type: str
    score: float | None = None

class Graph(BaseModel):
    nodes: List[Paragraph]
    edges: List[Edge]
