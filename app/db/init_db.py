from __future__ import annotations
import logging
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text, select

log = logging.getLogger(__name__)

async def ensure_extensions(db: AsyncSession) -> None:
    stmts = [
        'CREATE EXTENSION IF NOT EXISTS "pgcrypto"',
        'CREATE EXTENSION IF NOT EXISTS "pgvector"',
    ]
    for sql in stmts:
        await db.execute(text(sql))
    await db.commit()
    log.info("DB extensions ensured (pgcrypto, pgvector).")