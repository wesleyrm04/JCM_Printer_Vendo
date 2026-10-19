from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from sqlalchemy.ext.declarative import declarative_base
import os

# Create a 'data' folder in the root directory to hold our SQLite database file
os.makedirs("data", exist_ok=True)
SQLALCHEMY_DATABASE_URL = "sqlite:///./data/jcm_vendo.db"

# check_same_thread=False is needed in FastAPI for SQLite
engine = create_engine(
    SQLALCHEMY_DATABASE_URL, connect_args={"check_same_thread": False}
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
Base = declarative_base()

# Dependency used by FastAPI to get the database session
def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()