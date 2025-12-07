from sqlalchemy import create_engine, text
from app.core.config import settings
import numpy as np

def inspect_schema():
    print("Connecting to DB...")
    engine = create_engine(settings.database_url)
    
    with engine.connect() as conn:
        # Check columns of 'chunks'
        print("\n--- Table: chunks ---")
        try:
            res = conn.execute(text("SELECT * FROM chunks LIMIT 1"))
            if res.returns_rows:
                keys = res.keys()
                print(f"Columns: {list(keys)}")
                row = res.fetchone()
                if row:
                    # Check vector dim
                    # Assuming 'embedding' or similar column name. Let's find it.
                    vec_col = None
                    for k in keys:
                        if 'vec' in k.lower() or 'embedding' in k.lower():
                            vec_col = k
                            break
                    
                    if vec_col:
                        vec_val = getattr(row, vec_col)
                        # pgvector returns string or list
                        if isinstance(vec_val, str):
                            dim = len(vec_val.split(','))
                        elif isinstance(vec_val, list):
                            dim = len(vec_val)
                        else:
                            dim = "Unknown type"
                        print(f"Vector column '{vec_col}' dimension: {dim}")
                    else:
                        print("No vector column found in 'chunks'")
        except Exception as e:
            print(f"Error reading chunks: {e}")

        # Check columns of 'licitacion'
        print("\n--- Table: licitacion ---")
        try:
            res = conn.execute(text("SELECT * FROM licitacion LIMIT 1"))
            keys = res.keys()
            print(f"Columns: {list(keys)}")
        except Exception as e:
            print(f"Error reading licitacion: {e}")

        # Check columns of 'companies'
        print("\n--- Table: companies ---")
        try:
            res = conn.execute(text("SELECT * FROM companies LIMIT 1"))
            keys = res.keys()
            print(f"Columns: {list(keys)}")
            row = res.fetchone()
            if row:
                 # Check vector dim
                vec_col = 'razon_social_embedding'
                if vec_col in keys:
                    vec_val = getattr(row, vec_col)
                    if isinstance(vec_val, str):
                        dim = len(vec_val.split(','))
                    elif isinstance(vec_val, list):
                        dim = len(vec_val)
                    else:
                         dim = "Unknown type"
                    print(f"Vector column '{vec_col}' dimension: {dim}")
        except Exception as e:
             print(f"Error reading companies: {e}")

if __name__ == "__main__":
    inspect_schema()
