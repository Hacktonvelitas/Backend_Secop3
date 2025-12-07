import os
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    total = conn.execute(text('SELECT COUNT(*) FROM chunks')).scalar()
    non_null = conn.execute(text('SELECT COUNT(*) FROM chunks WHERE embedding_vec IS NOT NULL')).scalar()
    print('Total rows in chunks:', total)
    print('Rows with non-null embedding_vec:', non_null)
