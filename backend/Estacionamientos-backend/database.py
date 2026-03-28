from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

from core.config import DATABASE_CLOUD_URL, DATABASE_URL

engine = create_engine(DATABASE_URL, echo=True, pool_pre_ping=True)
engine_cloud = create_engine(DATABASE_CLOUD_URL, echo=True, pool_pre_ping=True)

SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)
SessionCloud = sessionmaker(autocommit=False, autoflush=False, bind=engine_cloud)

Base = declarative_base()


def get_db():
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def get_cloud_db():
    db = SessionCloud()
    try:
        yield db
    finally:
        db.close()
