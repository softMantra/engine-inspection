import os
import threading
from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from app.database import Base, engine
from app.routes_dashboard import router as dashboard_router
from app.routes_inspection import router as inspection_router

Base.metadata.create_all(bind=engine)

app = FastAPI(title="Engine Inspection System")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/health")
def health_check():
    return JSONResponse({"status": "ok"})

app.include_router(dashboard_router)
app.include_router(inspection_router)

app.mount("/static", StaticFiles(directory="static"), name="static")


@app.get("/")
def serve_index():
    return FileResponse(os.path.join("static", "index.html"))


@app.get("/{catchall:path}")
def serve_static_fallback(catchall: str):
    path = os.path.join("static", catchall)
    if os.path.isfile(path):
        return FileResponse(path)
    return FileResponse(os.path.join("static", "index.html"))


# ── Background model warm-up so loading YOLO + ViT doesn't block startup
def _warmup_models():
    try:
        from app.routes_inspection import get_engine
        print("[startup] Warming up AI models in background...")
        get_engine()
        print("[startup] AI models ready.")
    except Exception as exc:
        print(f"[startup] Model warm-up failed (non-fatal): {exc}")


@app.on_event("startup")
def startup_event():
    thread = threading.Thread(target=_warmup_models, daemon=True)
    thread.start()
