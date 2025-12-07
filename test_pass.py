from app.core.security import hash_password
try:
    print(f"Hashing 'password123'...")
    h = hash_password("password123")
    print(f"Hash: {h}")
except Exception as e:
    print(f"Error: {e}")
