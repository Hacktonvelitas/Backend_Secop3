import requests
import json
import os
import numpy as np
from sqlalchemy import create_engine, text
import time

# Configuration
# Defaults for running INSIDE the container
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000/api/v1")
# Default DB URL for internal access (host=licita_db)
DB_URL = os.getenv("DATABASE_URL", "postgresql://postgres:postgres@licita_db:5432/licitaciones_db")
# From previous `docker ps`: licita_db is on 5432.

DUMMY_NIT = "999999999"
DUMMY_LIC_ID = 999999
DUMMY_CHUNK_ID = "chunk_999999_0"

def get_db_connection():
    # We might need to adjust host/port if running from outside
    # For now assuming localhost:5432 works as per docker ps
    engine = create_engine(DB_URL)
    return engine.connect()

def generate_vector(dim=768):
    return np.random.rand(dim).astype(np.float32).tolist()

def vec_to_str(vec):
    return str(vec)

def insert_dummy_data():
    print("Inserting dummy data...")
    conn = get_db_connection()
    trans = conn.begin()
    
    try:
        # 1. Insert Company
        vec_company = generate_vector()
        sql_company = text("""
            INSERT INTO public.companies (id, nit, razon_social, razon_social_embedding)
            VALUES (:id, :nit, :name, :vec)
            ON CONFLICT (id) DO NOTHING
        """)
        conn.execute(sql_company, {
            "id": 999999,
            "nit": DUMMY_NIT, 
            "name": "Dummy Verification Corp", 
            "vec": vec_to_str(vec_company)
        })
        
        # 2. Insert Licitacion
        sql_lic = text("""
            INSERT INTO public.licitacion (id, entidad, objeto, cuantia, fecha_public, estado)
            VALUES (:id, :entidad, :objeto, :cuantia, :fecha, :estado)
            ON CONFLICT (id) DO NOTHING
        """)
        conn.execute(sql_lic, {
            "id": DUMMY_LIC_ID,
            "entidad": "Entidad Dummy",
            "objeto": "Objeto Dummy para Verificacion",
            "cuantia": 100000000,
            "fecha": "2024-01-01",
            "estado": "Publicado"
        })
        
        # 3. Insert Chunk (Similar vector)
        # Create a vector very close to company vector
        vec_chunk = vec_company # Identical for max similarity
        
        sql_chunk = text("""
            INSERT INTO public.chunks (chunk_id, lic_id, text, embedding_vec)
            VALUES (:cid, :lid, :txt, :vec)
            ON CONFLICT (chunk_id) DO NOTHING
        """)
        conn.execute(sql_chunk, {
            "cid": DUMMY_CHUNK_ID,
            "lid": str(DUMMY_LIC_ID),
            "txt": "Este es un chunk dummy que deberia hacer match con la empresa dummy.",
            "vec": vec_to_str(vec_chunk)
        })
        
        trans.commit()
        print("Dummy data inserted.")
        return True
    except Exception as e:
        trans.rollback()
        print(f"Error inserting data: {e}")
        return False
    finally:
        conn.close()

def cleanup_dummy_data():
    print("Cleaning up dummy data...")
    conn = get_db_connection()
    trans = conn.begin()
    try:
        conn.execute(text("DELETE FROM public.chunks WHERE chunk_id = :cid"), {"cid": DUMMY_CHUNK_ID})
        conn.execute(text("DELETE FROM public.licitacion WHERE id = :id"), {"id": DUMMY_LIC_ID})
        conn.execute(text("DELETE FROM public.companies WHERE nit = :nit"), {"nit": DUMMY_NIT})
        trans.commit()
        print("Cleanup complete.")
    except Exception as e:
        trans.rollback()
        print(f"Error cleaning up: {e}")
    finally:
        conn.close()

def test_match():
    print("Testing match/inicial endpoint...")
    payload = {
        "nit_empresa": DUMMY_NIT,
        "top_k": 5,
        "min_score": 0.8
    }
    
    try:
        # Test Initial Match
        resp = requests.post(f"{BASE_URL}/opportunities/match/inicial", json=payload)
        if resp.status_code == 200:
            results = resp.json()
            print(f"Matches found: {len(results)}")
            found = False
            for r in results:
                # Compare as strings to be safe
                if str(r.get('licitacion_id')) == str(DUMMY_LIC_ID):
                    print("SUCCESS: Dummy licitacion found in match/inicial!")
                    found = True
                    break
            if not found:
                print("FAILURE: Dummy licitacion NOT found in match/inicial.")
                print("Results:", json.dumps(results, indent=2))
        else:
            print(f"FAILURE: match/inicial returned {resp.status_code}")
            print(resp.text)

        # Test Augmented Match
        print("\nTesting match/augmented endpoint...")
        resp_aug = requests.post(f"{BASE_URL}/opportunities/match/augmented", json=payload)
        if resp_aug.status_code == 200:
            results_aug = resp_aug.json()
            print(f"Augmented Matches found: {len(results_aug)}")
            found_aug = False
            for r in results_aug:
                # Augmented result has 'base_match' or flat structure? 
                # Checking schema: returns [asdict(r) for r in results] where r is AugmentedMatchResult
                # AugmentedMatchResult has 'base_match': MatchResult
                # So we look inside 'base_match'
                base = r.get('base_match', {})
                if str(base.get('licitacion_id')) == str(DUMMY_LIC_ID):
                    print("SUCCESS: Dummy licitacion found in match/augmented!")
                    found_aug = True
                    break
            if not found_aug:
                print("FAILURE: Dummy licitacion NOT found in match/augmented.")
                print("Results:", json.dumps(results_aug, indent=2))
        else:
            print(f"FAILURE: match/augmented returned {resp_aug.status_code}")
            print(resp_aug.text)

    except Exception as e:
        print(f"Exception during test: {e}")

if __name__ == "__main__":
    if insert_dummy_data():
        # Give DB a moment? Usually not needed for transactional inserts but safe
        time.sleep(1)
        test_match()
        cleanup_dummy_data()
