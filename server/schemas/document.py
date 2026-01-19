from pydantic import BaseModel
from typing import Literal, List, Optional

class DatasetDocument(BaseModel):
    id: str
    name: str
    origin: Literal['dataset', 'upload']
    processed: bool

class Paragraph(BaseModel):
    id: str
    documentId: str
    page: int
    paragraph_enum: int
    text: str
    bbox: List[float]  # [x0, y0, x1, y1]
    relationsCount: int = 0
