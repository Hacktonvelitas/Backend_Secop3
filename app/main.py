from __future__ import annotations

from fastapi import FastAPI, Depends
from sqlalchemy.orm import Session
from sqlalchemy import text

from app.api.deps import get_db
from app.api.v1.router import api_router
from app.core.cors import setup_cors

api = FastAPI(title="Licita API", version="1.0.0")
setup_cors(api)

@api.get("/health")
def health(db: Session = Depends(get_db)):
    db.execute(text("SELECT 1"))
    return {"status": "ok"}

@api.get("/")
def index():
    return {
        "name": "Licita API",
        "version": "1.0.0",
        "docs": "/docs"
    }

# Include API Router
api.include_router(api_router, prefix="/api/v1")
