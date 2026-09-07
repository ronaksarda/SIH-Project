from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.api.auth import router as auth_router
from app.api.scan import router as scan_router
from app.api.reports import router as reports_router
from app.api.dashboard import router as dashboard_router

app = FastAPI(title="Legal Metrology Compliance System API")

# Configure CORS for frontend development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.get("/api/health")
async def health_check():
    return {"status": "ok"}

# Include routers
app.include_router(auth_router, prefix="/api/auth", tags=["auth"])
app.include_router(scan_router, prefix="/api/scan", tags=["scan"])
app.include_router(reports_router, prefix="/api/reports", tags=["reports"])
app.include_router(dashboard_router, prefix="/api/dashboard", tags=["dashboard"])
