from sqlalchemy import MetaData, create_engine
from sqlalchemy.orm import sessionmaker
from .config import DATABASE_URL

engine = create_engine(DATABASE_URL)
metadata = MetaData()
metadata.reflect(bind=engine)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Dependency to get the database session
def get_session():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Dependency to get the metadata
def get_metadata():
    return metadata