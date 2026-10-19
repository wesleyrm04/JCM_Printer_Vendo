from fastapi import APIRouter, HTTPException, Depends
from sqlalchemy.orm import Session
from pydantic import BaseModel
import uuid
import asyncio
import os

from app.core.state_machine import vending_state, KioskState
from app.services.usb_manager import USBManager, TEMP_WORKSPACE
from app.services.nas_manager import NASManager
from app.hardware.epson_printer import EpsonPrinter
from app.hardware.epson_scanner import EpsonScanner
from app.database.database import get_db
from app.services.pricing import PricingService
from app.database import models
from app.utils.page_parser import get_actual_pages_to_print # NEW IMPORT

job_router = APIRouter()
printer = EpsonPrinter()
scanner = EpsonScanner()

# --- Schemas ---
class AnalyzeRequest(BaseModel):
    file_path: str
    source: str 

class JobCreateRequest(BaseModel):
    file_path: str
    source: str 
    copies: int
    color_mode: str  
    page_range: str = "" # NEW FIELD

class CopyCreateRequest(BaseModel):
    copies: int
    color_mode: str

class JobResponse(BaseModel):
    job_id: str
    required_amount: float
    status: str

class CoinInsertRequest(BaseModel):
    amount: float

# --- Execution Callback ---
async def execute_machine_job():
    if vending_state.job_type == "COPY":
        print("[SYSTEM] Executing Photocopy Scan...")
        scan_filename = f"scan_{uuid.uuid4().hex}.jpg"
        vending_state.current_file_path = os.path.join(TEMP_WORKSPACE, scan_filename)
        
        success = await asyncio.to_thread(scanner.scan_document, vending_state.current_file_path)
        
        if not success:
            print("[SYSTEM] Scanning failed.")
            await vending_state.set_state(KioskState.ERROR)
            await asyncio.sleep(4)
            USBManager.cleanup_workspace()
            await vending_state.reset_to_ready()
            return

    print(f"[SYSTEM] Spooling to printer: {vending_state.current_file_path}")
    
    success = printer.print_document(
        file_path=vending_state.current_file_path,
        copies=vending_state.copies, 
        color_mode=vending_state.color_mode,
        page_range=vending_state.page_range
    )
    
    if success:
        print("[SYSTEM] Job spooled successfully.")
        await asyncio.sleep(5) 
    else:
        print("[SYSTEM] Print job failed at the spooler.")
        await vending_state.set_state(KioskState.ERROR)
        await asyncio.sleep(4)

    print("[SYSTEM] Cleaning up workspace...")
    USBManager.cleanup_workspace()
    await vending_state.reset_to_ready()

vending_state.on_payment_complete = execute_machine_job

# --- Endpoints ---
@job_router.get("/status")
async def get_system_status():
    return {
        "state": vending_state.state.value,
        "current_job_id": vending_state.current_job_id,
        "amount_required": vending_state.required_amount,
        "amount_inserted": vending_state.inserted_amount
    }

@job_router.get("/usb/files")
async def list_usb_files():
    try:
        files = USBManager.scan_usb_files()
        return {"status": "success", "file_count": len(files), "files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@job_router.get("/nas/files")
async def search_nas_files(query: str = ""):
    try:
        files = NASManager.search_files(query)
        return {"status": "success", "file_count": len(files), "files": files}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@job_router.post("/usb/analyze")
async def analyze_file(request: AnalyzeRequest):
    try:
        pages = USBManager.get_page_count(request.file_path)
        return {"status": "success", "pages": pages}
    except Exception as e:
        raise HTTPException(status_code=400, detail=str(e))

@job_router.post("/jobs/copy", response_model=JobResponse)
async def create_copy_job(request: CopyCreateRequest, db: Session = Depends(get_db)):
    if vending_state.state not in [KioskState.READY, KioskState.JOB_CONFIG]:
        raise HTTPException(status_code=400, detail="Machine is busy.")

    job_id = str(uuid.uuid4())
    total_pages_to_print = 1 * request.copies 
    service_id = "PRINT_BW" if request.color_mode == 'BW' else "PRINT_COLOR"
    
    total_price = PricingService.calculate_price(db, service_id, total_pages_to_print)
        
    db_job = models.Job(id=job_id, service_id=service_id, total_units=total_pages_to_print, calculated_price=total_price, status="WAITING_PAYMENT")
    db.add(db_job)
    db.commit()

    await vending_state.start_payment_phase(
        job_id=job_id, required_amount=total_price, file_path="", copies=request.copies, color_mode=request.color_mode, job_type="COPY"
    )

    return JobResponse(job_id=job_id, required_amount=total_price, status="WAITING_PAYMENT")

@job_router.post("/jobs", response_model=JobResponse)
async def create_job(request: JobCreateRequest, db: Session = Depends(get_db)):
    if vending_state.state not in [KioskState.READY, KioskState.JOB_CONFIG]:
        raise HTTPException(status_code=400, detail="Machine is busy.")

    total_document_pages = USBManager.get_page_count(request.file_path)
    
    # Calculate EXACT pages based on the range provided
    actual_pages_to_print = get_actual_pages_to_print(request.page_range, total_document_pages)

    if request.source == "USB":
        safe_local_path = USBManager.isolate_file_for_printing(request.file_path)
    else:
        safe_local_path = NASManager.isolate_file_for_printing(request.file_path)

    job_id = str(uuid.uuid4())
    final_total_pages = actual_pages_to_print * request.copies
    service_id = "PRINT_BW" if request.color_mode == 'BW' else "PRINT_COLOR"
    
    try:
        total_price = PricingService.calculate_price(db, service_id, final_total_pages)
    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
        
    db_job = models.Job(id=job_id, service_id=service_id, total_units=final_total_pages, calculated_price=total_price, status="WAITING_PAYMENT")
    db.add(db_job)
    db.commit()

    await vending_state.start_payment_phase(
        job_id=job_id, required_amount=total_price, file_path=safe_local_path, copies=request.copies, color_mode=request.color_mode, job_type="PRINT", page_range=request.page_range
    )

    return JobResponse(job_id=job_id, required_amount=total_price, status="WAITING_PAYMENT")

@job_router.post("/jobs/insert-coin")
async def manual_coin_insert(request: CoinInsertRequest):
    if vending_state.state != KioskState.WAITING_PAYMENT:
        raise HTTPException(status_code=400, detail="Not currently accepting coins.")
    await vending_state.handle_coin_inserted(request.amount)
    return {"status": "accepted"}

@job_router.post("/jobs/cancel")
async def cancel_job(db: Session = Depends(get_db)):
    if vending_state.state != KioskState.WAITING_PAYMENT:
        raise HTTPException(status_code=400, detail="No active payment session.")
    
    if vending_state.current_job_id:
        db_job = db.query(models.Job).filter(models.Job.id == vending_state.current_job_id).first()
        if db_job:
            db_job.status = "CANCELLED"
            db.commit()
    
    USBManager.cleanup_workspace()
    await vending_state.reset_to_ready()
    return {"status": "CANCELLED"}