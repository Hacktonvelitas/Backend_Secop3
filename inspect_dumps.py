from sqlalchemy import create_engine, inspect, text
from app.core.config import settings

# Force disable SSL for local check if needed, or rely on the env var if set correctly in this context
# The docker-compose has sslmode=disable, but running locally might need it too if we connect to localhost:5432
# However, inside the container (where I'll run this), it connects to 'db'.
# I'll run this inside the container.

def inspect_db():
    # Use the connection string from settings, but ensure we are using the one that works inside the container
    # settings.database_url should be correct if env vars are passed.
    print(f"Connecting to DB...")
    engine = create_engine(settings.database_url)
    
    inspector = inspect(engine)
    table_names = inspector.get_table_names()
    
    print(f"Found {len(table_names)} tables.")
    print("-" * 30)
    
    for table in table_names:
        try:
            with engine.connect() as conn:
                count = conn.execute(text(f'SELECT count(*) FROM "{table}"')).scalar()
                print(f"Table: {table:<30} | Rows: {count}")
        except Exception as e:
            print(f"Table: {table:<30} | Error counting rows: {e}")

if __name__ == "__main__":
    inspect_db()
