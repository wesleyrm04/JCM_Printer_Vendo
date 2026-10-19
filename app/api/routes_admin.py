from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
from typing import List

from app.database.database import get_db
from app.database import models
from app.core.state_machine import vending_state

admin_router = APIRouter()

# --- Schemas ---
class PricingUpdateRequest(BaseModel):
    price_per_unit: float

# --- Endpoints ---
@admin_router.get("/dashboard-stats")
async def get_dashboard_stats(db: Session = Depends(get_db)):
    """Returns high-level stats for the admin dashboard."""
    # Calculate total revenue from COMPLETED jobs (we use WAITING_PAYMENT in our mock test right now)
    # For now, let's just sum all jobs that aren't CANCELLED or ERROR
    valid_jobs = db.query(models.Job).filter(models.Job.status.not_in(["CANCELLED", "ERROR"])).all()
    
    total_revenue = sum(job.calculated_price for job in valid_jobs)
    total_jobs = len(valid_jobs)
    
    return {
        "kiosk_state": vending_state.state.value,
        "total_revenue": total_revenue,
        "total_jobs": total_jobs
    }

@admin_router.get("/pricing")
async def get_all_pricing(db: Session = Depends(get_db)):
    """Gets all pricing tiers and their associated services."""
    tiers = db.query(models.PricingTier).all()
    result = []
    for t in tiers:
        service = db.query(models.Service).filter(models.Service.id == t.service_id).first()
        result.append({
            "id": t.id,
            "service_name": service.name if service else "Unknown",
            "min_qty": t.min_qty,
            "max_qty": t.max_qty or "Infinity",
            "price_per_unit": t.price_per_unit
        })
    return result

@admin_router.put("/pricing/{tier_id}")
async def update_pricing(tier_id: int, request: PricingUpdateRequest, db: Session = Depends(get_db)):
    """Updates the price of a specific tier."""
    tier = db.query(models.PricingTier).filter(models.PricingTier.id == tier_id).first()
    if not tier:
        raise HTTPException(status_code=404, detail="Pricing tier not found")
        
    tier.price_per_unit = request.price_per_unit
    db.commit()
    return {"status": "success", "message": "Price updated successfully"}

@admin_router.get("/history")
async def get_job_history(db: Session = Depends(get_db), limit: int = 50):
    """Gets recent transaction history."""
    jobs = db.query(models.Job).order_by(models.Job.created_at.desc()).limit(limit).all()
    result = []
    for j in jobs:
        service = db.query(models.Service).filter(models.Service.id == j.service_id).first()
        result.append({
            "job_id": j.id[:8] + "...", # Truncate for display
            "service": service.name if service else "Unknown",
            "pages": j.total_units,
            "price": j.calculated_price,
            "status": j.status,
            "date": j.created_at.strftime("%Y-%m-%d %H:%M:%S")
        })
    return result