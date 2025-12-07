import requests
import json

import os
# Defaults for running INSIDE the container
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000/api/v1")

def test_endpoint(name, url, payload):
    print(f"\n--- Testing {name} ---")
    try:
        resp = requests.post(url, json=payload)
        print(f"Status: {resp.status_code}")
        if resp.status_code == 200:
            data = resp.json()
            if isinstance(data, list):
                print(f"Result count: {len(data)}")
            else:
                print("Result is a dictionary/object")
            # Print first item or snippet
            print(f"Response snippet: {str(data)[:200]}...")
        else:
            print(f"Error: {resp.text}")
    except Exception as e:
        print(f"Exception: {e}")

def main():
    # Payload for match/inicial and match/augmented
    match_payload = {
        "nit_empresa": "9004300063", 
        "top_k": 3,
        "min_score": 0.1 # Low score to try and get DB matches if possible
    }

    # Payload for analisis/precios
    analysis_payload = {
        "nit_empresa": "9004300063",
        "top_k": 5,
        "sector_keywords": ["Agro", "Cultivos"] # Guessed keywords for VERAGRO
    }

    test_endpoint("Match Inicial", f"{BASE_URL}/opportunities/match/inicial", match_payload)
    test_endpoint("Match Augmented", f"{BASE_URL}/opportunities/match/augmented", match_payload)
    test_endpoint("Analisis Precios", f"{BASE_URL}/opportunities/analisis/precios", analysis_payload)

if __name__ == "__main__":
    main()
