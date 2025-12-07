import os
import sys
import json
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.getcwd())

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from app.core.config import settings
from app.services.operaciones.match_inicial import obtener_oportunidades_empresa

def run_match():
    print("--- Running Match Test ---")
    
    # Use settings for DB URL to be consistent
    engine = create_engine(settings.database_url)
    Session = sessionmaker(bind=engine)
    session = Session()

    NIT = "901234567" # The NIT from create_test_company_with_embeddings.py

    print(f"Searching opportunities for Company NIT: {NIT}")

    try:
        results = obtener_oportunidades_empresa(
            session=session,
            nit_empresa=NIT,
            top_k=5,
            min_score=0.0, # Get everything to see if it works
            sector_filter=None,
            exclusion_filter=None,
            location_filter=None,
            rango_cuantia=None,
            fecha_inicio=None,
            n_clusters=1,
        )

        print(f"Found {len(results)} matches.")
        
        for i, r in enumerate(results):
            print(f"\nMatch #{i+1}:")
            # 'r' is likely a dictionary or object, let's try to print it nicely
            print(r)

    except Exception as e:
        print(f"Error running match: {e}")
    finally:
        session.close()

if __name__ == "__main__":
    run_match()
