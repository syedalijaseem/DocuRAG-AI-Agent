from pydantic import BaseModel
from typing import Optional

class RAGChunkAndSrc(BaseModel):
    chunks: list[dict]  
    source_id: Optional[str] = None

class RAGUpsertResult(BaseModel):
    ingested: int

class RAGSearchResult(BaseModel):
    contexts: list[str]
    sources: list[str]

class RAGQueryResult(BaseModel):
    answer: str
    sources: list[str]
    num_contexts: int