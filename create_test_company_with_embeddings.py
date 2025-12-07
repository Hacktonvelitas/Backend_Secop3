import os
import sys
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Add project root to path
sys.path.append(os.getcwd())

from app.db.session import SessionLocal
from app.models.empresa import Companies
from app.services.embedding_service import EmbeddingService

def create_test_company():
    session = SessionLocal()
    embedding_service = EmbeddingService()

    # Realistic Company Data (Software/Technology)
    company_data = {
        "nit": "901234567",
        "razon_social": "SOLUCIONES TECNOLOGICAS INNOVADORAS SAS",
        "muncomercial": "Bogota",
        "ciiu1": "6201", # Actividades de desarrollo de sistemas informáticos (planificación, análisis, diseño, programación, pruebas)
        "ciiu2": "6202", # Actividades de consultoría informática y actividades de administración de instalaciones informáticas
        "ciiu3": "6311", # Procesamiento de datos, alojamiento (hosting) y actividades relacionadas
        "ciiu4": "4651", # Comercio al por mayor de computadores, equipo periférico y programas de informática
    }

    print(f"Generating embeddings for {company_data['razon_social']}...")

    # Generate Embeddings
    razon_social_emb = embedding_service.generate_embedding(company_data["razon_social"])
    ciiu1_emb = embedding_service.generate_embedding(company_data["ciiu1"])
    ciiu2_emb = embedding_service.generate_embedding(company_data["ciiu2"])
    ciiu3_emb = embedding_service.generate_embedding(company_data["ciiu3"])
    ciiu4_emb = embedding_service.generate_embedding(company_data["ciiu4"])

    print("Embeddings generated.")

    # Check if exists
    existing_company = session.query(Companies).filter(Companies.nit == company_data["nit"]).first()
    
    if existing_company:
        print("Company already exists. Updating...")
        existing_company.razon_social = company_data["razon_social"]
        existing_company.muncomercial = company_data["muncomercial"]
        existing_company.ciiu1 = company_data["ciiu1"]
        existing_company.ciiu2 = company_data["ciiu2"]
        existing_company.ciiu3 = company_data["ciiu3"]
        existing_company.ciiu4 = company_data["ciiu4"]
        existing_company.razon_social_embedding = razon_social_emb
        existing_company.ciiu1_embedding = ciiu1_emb
        existing_company.ciiu2_embedding = ciiu2_emb
        existing_company.ciiu3_embedding = ciiu3_emb
        existing_company.ciiu4_embedding = ciiu4_emb
    else:
        print("Creating new company...")
        new_company = Companies(
            nit=company_data["nit"],
            razon_social=company_data["razon_social"],
            muncomercial=company_data["muncomercial"],
            ciiu1=company_data["ciiu1"],
            ciiu2=company_data["ciiu2"],
            ciiu3=company_data["ciiu3"],
            ciiu4=company_data["ciiu4"],
            razon_social_embedding=razon_social_emb,
            ciiu1_embedding=ciiu1_emb,
            ciiu2_embedding=ciiu2_emb,
            ciiu3_embedding=ciiu3_emb,
            ciiu4_embedding=ciiu4_emb
        )
        session.add(new_company)

    session.commit()
    print(f"Company {company_data['razon_social']} (NIT: {company_data['nit']}) saved successfully with embeddings.")
    session.close()

if __name__ == "__main__":
    create_test_company()
