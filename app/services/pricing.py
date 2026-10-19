from sqlalchemy.orm import Session
from app.database.models import PricingTier

class PricingService:
    @staticmethod
    def calculate_price(db: Session, service_id: str, total_pages: int) -> float:
        """Finds the correct pricing tier for the requested amount of pages."""
        
        # Query the database for the active tier that matches the page count
        tier = db.query(PricingTier).filter(
            PricingTier.service_id == service_id,
            PricingTier.min_qty <= total_pages,
            (PricingTier.max_qty >= total_pages) | (PricingTier.max_qty.is_(None))
        ).first()
        
        if not tier:
            raise ValueError(f"No active pricing tier found for {service_id} at {total_pages} pages.")
            
        return float(tier.price_per_unit * total_pages)