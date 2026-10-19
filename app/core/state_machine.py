from enum import Enum
import asyncio
from typing import Optional, Callable, Awaitable

class KioskState(Enum):
    BOOTING = "BOOTING"
    READY = "READY"                      
    JOB_CONFIG = "JOB_CONFIG"            
    WAITING_PAYMENT = "WAITING_PAYMENT"  
    PROCESSING = "PROCESSING"            
    ERROR = "ERROR"                      
    MAINTENANCE = "MAINTENANCE"          

class KioskStateMachine:
    def __init__(self):
        self.state: KioskState = KioskState.BOOTING
        
        self.current_job_id: Optional[str] = None
        self.current_file_path: Optional[str] = None
        self.job_type: str = "PRINT"
        self.copies: int = 1
        self.color_mode: str = "BW"
        self.page_range: str = ""
        
        self.required_amount: float = 0.0
        self.inserted_amount: float = 0.0
        
        self.on_state_change: Optional[Callable[[dict], Awaitable[None]]] = None
        self.on_payment_complete: Optional[Callable[[], Awaitable[None]]] = None

    async def _broadcast(self):
        if self.on_state_change:
            payload = {
                "state": self.state.value,
                "job_id": self.current_job_id,
                "required": self.required_amount,
                "inserted": self.inserted_amount
            }
            await self.on_state_change(payload)

    async def set_state(self, new_state: KioskState):
        self.state = new_state
        print(f"[STATE MACHINE] Transitioned to {new_state.value}")
        await self._broadcast()

    async def start_payment_phase(self, job_id: str, required_amount: float, file_path: str, copies: int, color_mode: str, job_type: str = "PRINT", page_range: str = ""):
        if self.state not in [KioskState.READY, KioskState.JOB_CONFIG]:
            raise ValueError(f"Cannot start payment from state {self.state}")
        
        self.current_job_id = job_id
        self.required_amount = required_amount
        self.inserted_amount = 0.0
        self.current_file_path = file_path
        self.copies = copies
        self.color_mode = color_mode
        self.job_type = job_type
        self.page_range = page_range
        
        await self.set_state(KioskState.WAITING_PAYMENT)

    async def handle_coin_inserted(self, amount: float):
        if self.state != KioskState.WAITING_PAYMENT:
            return
            
        self.inserted_amount += amount
        print(f"[PAYMENT] Inserted: {self.inserted_amount} / {self.required_amount}")
        
        if self.inserted_amount >= self.required_amount:
            await self.set_state(KioskState.PROCESSING)
            if self.on_payment_complete:
                await self.on_payment_complete()
        else:
            await self._broadcast()

    async def reset_to_ready(self):
        self.current_job_id = None
        self.current_file_path = None
        self.job_type = "PRINT"
        self.copies = 1
        self.color_mode = "BW"
        self.page_range = ""
        self.required_amount = 0.0
        self.inserted_amount = 0.0
        await self.set_state(KioskState.READY)

vending_state = KioskStateMachine()