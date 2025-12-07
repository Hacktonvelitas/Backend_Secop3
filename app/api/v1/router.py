from fastapi import APIRouter
from app.api.v1.endpoints import licitaciones

api_router = APIRouter()
api_router.include_router(licitaciones.router, prefix="/licitaciones", tags=["licitaciones"])
# api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
