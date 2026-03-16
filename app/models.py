from sqlalchemy import Column, Integer, String, DateTime, Enum
from sqlalchemy.sql import func
from .database import Base
import enum

class ResultStatus(str, enum.Enum):
    PASS = "PASS"
    FAIL = "FAIL"
    UNKNOWN = "UNKNOWN"

class InspectionResult(Base):
    __tablename__ = "inspection_results"

    id = Column(Integer, primary_key=True, index=True)
    timestamp = Column(DateTime(timezone=True), server_default=func.now())
    verdict = Column(Enum(ResultStatus), nullable=False)
    image_path = Column(String, nullable=True) # E.g. "captures/PASS_2026...jpg"
    
    # Additional metadata if needed
    pass_count = Column(Integer, default=0)
    fail_count = Column(Integer, default=0)
