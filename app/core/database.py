from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings

# Usar sync engine para compatibilidad con repositorios actuales
# Si settings.database_url empieza con postgresql+asyncpg, cambiar a postgresql
db_url = settings.database_url.replace("postgresql+asyncpg", "postgresql")

engine = create_engine(db_url, pool_pre_ping=True)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
