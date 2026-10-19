from sqlalchemy import Column, Integer, String, Float, Boolean, ForeignKey, DateTime
from sqlalchemy.orm import relationship
from datetime import datetime, timezone
import uuid

from app.database.database import Base

def generate_uuid():
    return str(uuid.uuid4())

class Service(Base):
    __tablename__ = 'services'
    
    id = Column(String, primary_key=True) # 'PRINT_BW', 'PRINT_COLOR'
    name = Column(String, nullable=False)
    is_active = Column(Boolean, default=True)

class PricingTier(Base):
    __tablename__ = 'pricing_tiers'
    
    id = Column(Integer, primary_key=True, autoincrement=True)
    service_id = Column(String, ForeignKey('services.id'), nullable=False)
    min_qty = Column(Integer, nullable=False, default=1)
    max_qty = Column(Integer, nullable=True) # Null means infinity
    price_per_unit = Column(Float, nullable=False) 
    
    service = relationship("Service")

class Job(Base):
    __tablename__ = 'jobs'
    
    id = Column(String, primary_key=True, default=generate_uuid)
    service_id = Column(String, ForeignKey('services.id'), nullable=False)
    status = Column(String, default="PENDING") 
    total_units = Column(Integer, nullable=False) 
    calculated_price = Column(Float, nullable=False)
    created_at = Column(DateTime, default=lambda: datetime.now(timezone.utc))