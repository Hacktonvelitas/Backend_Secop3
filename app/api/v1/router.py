from fastapi import APIRouter
from app.api.v1.endpoints import licitaciones, opportunities, pipelines, ai

api_router = APIRouter()

api_router.include_router(licitaciones.router, prefix="/licitaciones", tags=["licitaciones"])
api_router.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
api_router.include_router(pipelines.router, prefix="/pipelines", tags=["pipelines"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
