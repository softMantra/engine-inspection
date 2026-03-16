import cv2
import numpy as np
import base64
import os
import time
from datetime import datetime
from fastapi import APIRouter, UploadFile, File, WebSocket, WebSocketDisconnect, Depends
from sqlalchemy.orm import Session
from app.database import get_db
from app.models import ResultStatus
from app import crud
from app.ai_engine import AIInspectionEngine

router = APIRouter(prefix="/api/inspection", tags=["inspection"])

# Initialize the AI Engine instance lazily or via app state if needed later
engine = None

def get_engine():
    global engine
    if engine is None:
        engine = AIInspectionEngine()
    return engine

SAVE_DIR = "captures"
os.makedirs(SAVE_DIR, exist_ok=True)
SAVE_COOLDOWN = 5 # only save every 5s if passing/failing on live stream
last_save_time = 0

def convert_base64_to_cv2(base64_string):
    """Converts a Base64 image string to OpenCV BGR format."""
    # Split the "data:image/jpeg;base64," prefix if it exists
    if "," in base64_string:
        base64_string = base64_string.split(",")[1]
    
    img_data = base64.b64decode(base64_string)
    nparr = np.frombuffer(img_data, np.uint8)
    return cv2.imdecode(nparr, cv2.IMREAD_COLOR)

def convert_cv2_to_base64(img_bgr, quality=80):
    """Converts a CV2 image to a base64 string for WebSocket transmission."""
    _, buffer = cv2.imencode('.jpg', img_bgr, [int(cv2.IMWRITE_JPEG_QUALITY), quality])
    base64_str = base64.b64encode(buffer).decode('utf-8')
    return f"data:image/jpeg;base64,{base64_str}"

@router.post("/upload")
async def analyze_image_upload(file: UploadFile = File(...), db: Session = Depends(get_db)):
    contents = await file.read()
    nparr = np.frombuffer(contents, np.uint8)
    img_bgr = cv2.imdecode(nparr, cv2.IMREAD_COLOR)
    
    ai = get_engine()
    annotated_frame, stats = ai.process_frame(img_bgr)
    
    # Save the file
    status = stats.get("status", "UNKNOWN")
    verdict_enum = ResultStatus.PASS if status == "PASS" else ResultStatus.FAIL if status == "FAIL" else ResultStatus.UNKNOWN
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    filename = f"{status}_{timestamp}.jpg"
    filepath = os.path.join(SAVE_DIR, filename)
    
    cv2.imwrite(filepath, annotated_frame)
    
    # DB insert
    crud.create_inspection_result(
        db, 
        verdict=verdict_enum, 
        image_path=filepath,
        pass_count=stats.get("pass_count", 0),
        fail_count=stats.get("fail_count", 0)
    )
    
    # Convert annotated image back to b64 for frontend response
    annotated_b64 = convert_cv2_to_base64(annotated_frame)
    
    return {
        "verdict": status,
        "image": annotated_b64,
        "details": stats
    }

@router.websocket("/ws")
async def live_inspection_ws(websocket: WebSocket, db: Session = Depends(get_db)):
    global last_save_time
    await websocket.accept()
    
    try:
        while True:
            # Receive base64 frame from client
            data = await websocket.receive_text()
            img_bgr = convert_base64_to_cv2(data)
            
            ai = get_engine()
            # Process Frame
            annotated_frame, stats = ai.process_frame(img_bgr)
            status = stats.get("status", "UNKNOWN")
            
            # Save threshold logic (live feeds process many frames)
            current_time = time.time()
            if status in ["PASS", "FAIL"] and (current_time - last_save_time > SAVE_COOLDOWN):
                timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
                filename = f"{status}_{timestamp}.jpg"
                filepath = os.path.join(SAVE_DIR, filename)
                
                cv2.imwrite(filepath, annotated_frame)
                
                verdict_enum = ResultStatus.PASS if status == "PASS" else ResultStatus.FAIL
                crud.create_inspection_result(
                    db, 
                    verdict=verdict_enum, 
                    image_path=filepath,
                    pass_count=stats.get("pass_count", 0),
                    fail_count=stats.get("fail_count", 0)
                )
                last_save_time = current_time
            
            # Send results back
            annotated_b64 = convert_cv2_to_base64(annotated_frame)
            await websocket.send_json({
                "verdict": status,
                "image": annotated_b64,
                "details": stats
            })
            
    except WebSocketDisconnect:
        print("Client disconnected from Live WebSocket.")
