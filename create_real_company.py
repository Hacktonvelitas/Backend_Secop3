import requests
import os
import json

BASE_URL = os.getenv("BASE_URL", "http://localhost:8000/api/v1")
NIT = "901000000"
COMPANY_DATA = {
    "nit": NIT,
    "razon_social": "CONSTRUCTORA Y CONSULTORA DE OBRAS CIVILES SAS",
    "pais": "Colombia",
    "municipio": "Bogota",
    "direccion_legal": "Av. El Dorado # 123",
    "correo_contacto": "contacto@constructora-test.com"
}

def create_company():
    print(f"--- Creating Company: {COMPANY_DATA['razon_social']} ---")
    url = f"{BASE_URL}/empresas/"
    try:
        resp = requests.post(url, json=COMPANY_DATA)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            print("Company created successfully.")
            print(json.dumps(resp.json(), indent=2))
            return True
        else:
            print(f"Error: {resp.text}")
            return False
    except Exception as e:
        print(f"Request failed: {e}")
        return False

if __name__ == "__main__":
    create_company()
