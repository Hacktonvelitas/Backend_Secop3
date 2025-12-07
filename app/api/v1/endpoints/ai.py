from typing import Optional
from fastapi import APIRouter, HTTPException
from pydantic import BaseModel
from app.IA.query_data import process_query
from app.IA.red_contac import process_query_graph

router = APIRouter()

class AIQueryRequest(BaseModel):
    prompt: str
    session_id: Optional[str] = None
    debug: Optional[bool] = False

class GraphQuery(BaseModel):
    query_text: str
    debug: bool = False

@router.post("/query")
def ai_query(payload: AIQueryRequest):
    if not payload.prompt:
        raise HTTPException(status_code=400, detail="Prompt required")
    return process_query(payload.prompt, session_id=payload.session_id, debug=payload.debug)

@router.post("/graphs/assistant")
def graphs_assistant(body: GraphQuery):
    return process_query_graph(body.query_text, debug=body.debug)
