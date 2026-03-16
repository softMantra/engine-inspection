from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app import crud

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])

@router.get("/stats")
def get_stats(db: Session = Depends(get_db)):
    return crud.get_telemetry_stats(db)

@router.get("/history")
def get_history(limit: int = 50, db: Session = Depends(get_db)):
    logs = crud.get_recent_inspections(db, limit)
    # Serialize logs
    return [
        {
            "id": log.id,
            "timestamp": log.timestamp.isoformat() if log.timestamp else None,
            "verdict": log.verdict.value,
            "image_path": log.image_path
        }
        for log in logs
    ]
