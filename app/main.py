from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
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

app.include_router(dashboard_router)
app.include_router(inspection_router)

app.mount("/static", StaticFiles(directory="static"), name="static")

import os
from fastapi.responses import FileResponse

@app.get("/")
def serve_index():
    return FileResponse(os.path.join("static", "index.html"))

@app.get("/{catchall:path}")
def serve_static_fallback(catchall: str):
    path = os.path.join("static", catchall)
    if os.path.isfile(path):
         return FileResponse(path)
    return FileResponse(os.path.join("static", "index.html"))
