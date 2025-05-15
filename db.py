import os
from sqlalchemy import create_engine, Column, Integer, String, Float, DateTime, UniqueConstraint
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker

# Database setup
Base = declarative_base()

db_path = os.path.join(os.path.dirname(__file__), 'signals.db')
engine = create_engine(f"sqlite:///{db_path}", connect_args={"check_same_thread": False})
SessionLocal = sessionmaker(bind=engine)

class Signal(Base):
    __tablename__ = 'signals'
    id = Column(Integer, primary_key=True, index=True)
    time = Column(DateTime, nullable=False)
    symbol = Column(String, index=True)
    side = Column(String)
    pattern = Column(String)
    entry = Column(Float)
    stop = Column(Float)
    tp = Column(Float)
    __table_args__ = (UniqueConstraint('time', 'symbol', 'side', 'entry', name='uix_signal'),)

# Create tables
Base.metadata.create_all(engine)
