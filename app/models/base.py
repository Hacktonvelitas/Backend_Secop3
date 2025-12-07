from sqlalchemy.orm import DeclarativeBase
import os

class Base(DeclarativeBase):
    pass

EMBED_DIMS_OPENAI = 1536
EMBED_DIMS_LOCAL = 768
