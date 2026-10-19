from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles
from fastapi.responses import FileResponse
from contextlib import asynccontextmanager
import os

from app.core.state_machine import KioskState, vending_state
from app.api.websockets import ws_router, manager
from app.api.routes_jobs import job_router
from app.api.routes_admin import admin_router  # IMPORT ADMIN ROUTER
from app.database.database import engine, SessionLocal
from app.database import models

def seed_database():
    db = SessionLocal()
    if not db.query(models.Service).first():
        print("[SYSTEM] Seeding Database with default prices...")
        bw_service = models.Service(id="PRINT_BW", name="Black & White Print")
        color_service = models.Service(id="PRINT_COLOR", name="Color Print")
        db.add_all([bw_service, color_service])
        
        tier1 = models.PricingTier(service_id="PRINT_BW", min_qty=1, max_qty=50, price_per_unit=3.00)
        tier2 = models.PricingTier(service_id="PRINT_BW", min_qty=51, max_qty=None, price_per_unit=2.50)
        tier3 = models.PricingTier(service_id="PRINT_COLOR", min_qty=1, max_qty=None, price_per_unit=10.00)
        
        db.add_all([tier1, tier2, tier3])
        db.commit()
    db.close()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("[SYSTEM] Booting JCM Print Vendo Service...")
    await vending_state.set_state(KioskState.BOOTING)
    
    models.Base.metadata.create_all(bind=engine)
    seed_database()
    print("[SYSTEM] Database Initialized & Synced.")
    
    await vending_state.set_state(KioskState.READY)
    print("[SYSTEM] Kiosk is READY.")
    yield
    print("[SYSTEM] Shutting down JCM Print Vendo...")

app = FastAPI(title="JCM Print Vendo", lifespan=lifespan)

app.add_middleware(
    CORSMiddleware, allow_origins=["*"], allow_credentials=True, allow_methods=["*"], allow_headers=["*"],
)

vending_state.on_state_change = manager.broadcast_state

app.include_router(ws_router)
app.include_router(job_router, prefix="/api/v1")
app.include_router(admin_router, prefix="/api/v1/admin") # MOUNT ADMIN API

# Mount the static Kiosk UI folder
os.makedirs("kiosk_ui", exist_ok=True)
app.mount("/static", StaticFiles(directory="kiosk_ui"), name="static")

# Mount the static Admin UI folder
os.makedirs("admin_ui", exist_ok=True)
app.mount("/admin_static", StaticFiles(directory="admin_ui"), name="admin_static")

@app.get("/")
async def serve_ui():
    """Serves the Customer Kiosk UI."""
    return FileResponse("kiosk_ui/index.html")

@app.get("/admin")
async def serve_admin_ui():
    """Serves the Administrator UI."""
    return FileResponse("admin_ui/index.html")