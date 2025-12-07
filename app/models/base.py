from sqlalchemy.orm import DeclarativeBase
import os

class Base(DeclarativeBase):
    pass

# Tamaño del vector según entorno (default 1536 segun DDL)
EMBED_DIMS = int(os.getenv("EMBED_DIMS", "1536"))
