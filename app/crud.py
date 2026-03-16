from sqlalchemy.orm import Session
from . import models
from datetime import datetime

def create_inspection_result(db: Session, verdict: models.ResultStatus, image_path: str = None, pass_count: int = 0, fail_count: int = 0):
    db_result = models.InspectionResult(
        verdict=verdict, 
        image_path=image_path,
        pass_count=pass_count,
        fail_count=fail_count
    )
    db.add(db_result)
    db.commit()
    db.refresh(db_result)
    return db_result

def get_recent_inspections(db: Session, limit: int = 50):
    return db.query(models.InspectionResult).order_by(models.InspectionResult.timestamp.desc()).limit(limit).all()

def get_telemetry_stats(db: Session):
    total = db.query(models.InspectionResult).count()
    passed = db.query(models.InspectionResult).filter(models.InspectionResult.verdict == models.ResultStatus.PASS).count()
    failed = db.query(models.InspectionResult).filter(models.InspectionResult.verdict == models.ResultStatus.FAIL).count()
    
    return {
        "total": total,
        "pass": passed,
        "fail": failed
    }
