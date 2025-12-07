import os
import numpy as np
import json
from sqlalchemy import create_engine, text

engine = create_engine(os.getenv('DATABASE_URL'))

# Generate a random embedding vector of dimension 768 and format as PostgreSQL array string
vec = np.random.rand(768).astype(np.float32)
vec_str = '[' + ','.join(map(str, vec.tolist())) + ']'

with engine.connect() as conn:
    # Check if company already exists
    existing = conn.execute(text("SELECT id FROM companies WHERE nit = :nit"), {"nit": "900123456"}).fetchone()
    if existing:
        print('Company already exists, updating embedding')
        conn.execute(text("UPDATE companies SET razon_social_embedding = (:vec)::vector WHERE nit = :nit"), {"vec": vec_str, "nit": "900123456"})
    else:
        # Insert dummy company with proper vector casting
        conn.execute(text("""
            INSERT INTO companies (razon_social, nit, razon_social_embedding)
            VALUES (:razon_social, :nit, (:vec)::vector)
        """), {
            "razon_social": "Empresa de Prueba SAS",
            "nit": "900123456",
            "vec": vec_str
        })
    conn.commit()
    print('Dummy company inserted/updated')
