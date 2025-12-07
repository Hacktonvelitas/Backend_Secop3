from app.db.session import engine
from app.models.base import Base
# Import all models to ensure they are registered
from app.models import * 

def init_db():
    print("Creating tables...")
    Base.metadata.create_all(bind=engine)
    print("Tables created.")

if __name__ == "__main__":
    init_db()
