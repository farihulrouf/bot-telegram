# app/database/db.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Definisikan Base untuk model
Base = declarative_base()

# Gantilah dengan URL database Anda
DATABASE_URL = "sqlite:///./test.db"  
engine = create_engine(DATABASE_URL)
# app/database/db.py
from sqlalchemy import create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, Session
from fastapi import Depends

DATABASE_URL = "sqlite:///./test.db"  # Gantilah dengan URL database Anda

# Buat engine dan session
engine = create_engine(DATABASE_URL)
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

Base = declarative_base()

# Dependency untuk mendapatkan session database
def get_db() -> Session:
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()

# Buat semua tabel yang didefinisikan dalam Base
def create_tables():
    Base.metadata.create_all(bind=engine)

# Kelas session untuk interaksi dengan database
SessionLocal = sessionmaker(autocommit=False, autoflush=False, bind=engine)

# Panggil fungsi untuk membuat tabel
create_tables()
