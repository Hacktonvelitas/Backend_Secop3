import requests
import os
import sys

# Configuration
BASE_URL = os.getenv("BASE_URL", "http://localhost:8000/api/v1/opportunities")
NIT = "9004300063"  # VERAGRO SAS

def test_endpoint(name, url):
    print(f"\n--- Testing {name} ---")
    print(f"URL: {url}")
    try:
        response = requests.get(url)
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            data = response.json()
            if isinstance(data, list):
                print(f"Result count: {len(data)}")
                print(f"Response snippet: {str(data)[:200]}...")
            else:
                print("Result is a dictionary/object")
                print(f"Response snippet: {str(data)[:200]}...")
        else:
            print(f"Error: {response.text}")
            
    except Exception as e:
        print(f"Request failed: {e}")

if __name__ == "__main__":
    # 0. Company Info
    test_endpoint("Company Info", f"{BASE_URL}/{NIT}/company")

    # 1. Match Inicial
    test_endpoint("Match Inicial", f"{BASE_URL}/{NIT}/match?top_k=3")

    # 2. Match Augmented
    test_endpoint("Match Augmented", f"{BASE_URL}/{NIT}/match-ai?top_k=3")

    # 3. Market Analysis
    test_endpoint("Analisis Precios", f"{BASE_URL}/{NIT}/market-analysis?top_k_analysis=50")
