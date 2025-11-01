# wickly/models.py
from sqlalchemy.orm import declarative_base, relationship
from sqlalchemy import Column, Integer, String, ForeignKey

Base = declarative_base()

class Detection(Base):
    __tablename__ = "detections"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    timeframe = Column(String(8), nullable=False, default="1D")

class Backtest(Base):
    __tablename__ = "backtests"
    id = Column(Integer, primary_key=True)
    detection_id = Column(Integer, ForeignKey("detections.id"), nullable=False)
    status = Column(String(20), default="queued")
    detection = relationship("Detection")

class Alert(Base):
    __tablename__ = "alerts"
    id = Column(Integer, primary_key=True)
    symbol = Column(String(20), nullable=False, index=True)
    rule = Column(String(64), nullable=False)  # e.g., "cross_above_ema20"