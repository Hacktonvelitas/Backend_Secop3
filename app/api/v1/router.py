from fastapi import APIRouter
from app.api.v1.endpoints import licitaciones, opportunities, pipelines, ai, auth, empresas, storage

api_router = APIRouter()

api_router.include_router(auth.router, prefix="/auth", tags=["auth"])
api_router.include_router(empresas.router, prefix="/empresas", tags=["empresas"])
api_router.include_router(licitaciones.router, prefix="/licitaciones", tags=["licitaciones"])
api_router.include_router(opportunities.router, prefix="/opportunities", tags=["opportunities"])
api_router.include_router(pipelines.router, prefix="/pipelines", tags=["pipelines"])
api_router.include_router(storage.router, prefix="/storage", tags=["storage"])
api_router.include_router(ai.router, prefix="/ai", tags=["ai"])
