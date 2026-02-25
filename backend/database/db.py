from sqlalchemy import create_engine, Column, Integer, String
from sqlalchemy.orm import declarative_base, sessionmaker

engine = create_engine("sqlite:///travel.db")
Base = declarative_base()

class TravelHistory(Base):
    __tablename__ = "history"
    id = Column(Integer, primary_key=True)
    query = Column(String)

Base.metadata.create_all(engine)
SessionLocal = sessionmaker(bind=engine)