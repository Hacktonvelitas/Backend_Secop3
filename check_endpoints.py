import requests
import json
import sys

BASE_URL = "http://localhost:8002/api/v1"

def log(msg, status="INFO"):
    print(f"[{status}] {msg}")

def check_response(response, expected_code=200):
    if response.status_code != expected_code:
        log(f"Failed: {response.status_code} - {response.text}", "ERROR")
        return False
    return True

def test_flow():
    # 1. Login
    log("Testing Login...")
    login_data = {
        "username": "test@example.com",
        "password": "password123"
    }
    resp = requests.post(f"{BASE_URL}/auth/login", data=login_data)
    if not check_response(resp, 200):
        log("Login failed. Attempting registration...", "WARN")
        reg_data = {
            "email": "test@example.com",
            "password": "password123",
            "nombre_completo": "Test User"
        }
        resp_reg = requests.post(f"{BASE_URL}/auth/register", json=reg_data)
        if check_response(resp_reg, 200):
            log("Registration successful. Retrying login...")
            resp = requests.post(f"{BASE_URL}/auth/login", data=login_data)
            if not check_response(resp, 200):
                return
        else:
            return

    token = resp.json()["access_token"]
    headers = {"Authorization": f"Bearer {token}"}
    log("Login successful.")

    # 2. Create Empresa
    log("Testing Create Empresa...")
    empresa_nit = "900123456"
    empresa_data = {
        "nit": empresa_nit,
        "razon_social": "Empresa de Prueba SAS",
        "municipio": "Bogotá",
        "correo_contacto": "contacto@prueba.com"
    }
    # Check if exists first (GET /empresas/{nit} is not implemented in the list I saw, but let's try POST and handle 400)
    resp = requests.post(f"{BASE_URL}/empresas/", json=empresa_data)
    if resp.status_code == 400 and "already exists" in resp.text:
        log("Empresa already exists, proceeding.")
    elif not check_response(resp, 200):
        log("Create Empresa failed.", "ERROR")
    else:
        log("Empresa created.")

    # 3. Get Empresas
    log("Testing Get Empresas...")
    resp = requests.get(f"{BASE_URL}/empresas/?skip=0&limit=10")
    if check_response(resp, 200):
        log(f"Get Empresas successful. Count: {len(resp.json())}")

    # 4. Match Inicial
    log("Testing Match Inicial...")
    match_data = {
        "nit_empresa": empresa_nit,
        "top_k": 5,
        "min_score": 0.1
    }
    resp = requests.post(f"{BASE_URL}/opportunities/match/inicial", json=match_data)
    check_response(resp, 200)

    # 5. Match Augmented
    log("Testing Match Augmented...")
    resp = requests.post(f"{BASE_URL}/opportunities/match/augmented", json=match_data)
    check_response(resp, 200)

    # 6. Analisis Precios
    log("Testing Analisis Precios...")
    price_data = {
        "nit_empresa": empresa_nit,
        "top_k": 50
    }
    resp = requests.post(f"{BASE_URL}/opportunities/analisis/precios", json=price_data)
    check_response(resp, 200)

if __name__ == "__main__":
    test_flow()
