import requests
import json

BASE_URL = "http://localhost:8002/api/v1"

def test_fallback():
    print("Testing LLM Fallback...")
    # Use a NIT that likely has no matches in DB but exists in companies table (or use dummy)
    # 900123456 is the dummy one we inserted. If we didn't insert chunks for it, it should trigger fallback.
    match_data = {
        "nit_empresa": "900123456", 
        "top_k": 3,
        "min_score": 0.9 # High score to force fallback if DB matches are low score (though logic is 'if not matches')
    }
    
    resp = requests.post(f"{BASE_URL}/opportunities/match/inicial", json=match_data)
    
    if resp.status_code == 200:
        results = resp.json()
        print(f"Status: {resp.status_code}")
        print(f"Matches found: {len(results)}")
        print(json.dumps(results, indent=2, ensure_ascii=False))
    else:
        print(f"Failed: {resp.status_code} - {resp.text}")

if __name__ == "__main__":
    test_fallback()
