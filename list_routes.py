import sys
import os
sys.path.append('/app')
from app.main import api

print("Registered Routes:")
for route in api.routes:
    print(f"{route.methods} {route.path}")
