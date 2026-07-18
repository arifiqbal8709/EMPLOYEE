from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from backend.app.core.config import settings

# Setup SQLAlchemy connection engine for PostgreSQL
engine = create_engine(
    settings.DATABASE_URL,
    # Pool configurations
    pool_pre_ping=True,
    pool_size=10,
    max_overflow=20
)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

def get_db():
    """
    Database session dependency provider.
    Yields session and closes it after the API call completes.
    """
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()
