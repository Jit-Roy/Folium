import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from core.models import Base

DB_PATH = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'learning_notebook.db')
engine = create_engine(f'sqlite:///{DB_PATH}', echo=False)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

def init_db():
    Base.metadata.create_all(bind=engine)

def get_session():
    return SessionLocal()
