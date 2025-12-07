import os
from sqlalchemy import create_engine, text
engine = create_engine(os.getenv('DATABASE_URL'))
with engine.connect() as conn:
    rows = conn.execute(text("SELECT nit, razon_social FROM companies WHERE nit='900123456'"))
    print('Rows for nit 900123456:', rows.fetchall())
    # also count total rows
    total = conn.execute(text('SELECT COUNT(*) FROM companies')).scalar()
    print('Total companies rows:', total)
