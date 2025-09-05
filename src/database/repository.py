from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func
from datetime import datetime
import json

from .models import ValuationRecord, InventoryItem, SaleRecord
from src.models.schemas import ValuationReport, IdentificationResult, ValuationResult


class ValuationRepository:
    """Repository for valuation record operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_valuation_record(self, report: ValuationReport) -> ValuationRecord:
        """Create a new valuation record from a ValuationReport"""

        # Serialize complex objects to JSON
        identification_data = {
            "confidence_score": report.identification.confidence_score,
            "identified_items": [
                item.dict() for item in report.identification.identified_items
            ],
            "description": report.identification.description,
            "condition_assessment": report.identification.condition_assessment,
        }

        market_data = (
            report.valuation.market_data.dict()
            if report.valuation.market_data
            else None
        )

        record = ValuationRecord(
            image_filename=report.image_filename,
            original_filename=report.image_filename,  # Could be different
            upload_timestamp=report.upload_timestamp,
            identification_data=identification_data,
            confidence_score=report.identification.confidence_score,
            estimated_value=report.valuation.estimated_value,
            valuation_confidence=report.valuation.confidence_score,
            recommendation_category=report.valuation.recommendation.value,
            reasoning=report.valuation.reasoning,
            suggested_platforms=[p.value for p in report.valuation.suggested_platforms],
            market_data=market_data,
            notes=report.notes,
        )

        self.db.add(record)
        self.db.commit()
        self.db.refresh(record)

        return record

    def get_valuation_record(self, record_id: int) -> Optional[ValuationRecord]:
        """Get a valuation record by ID"""
        return (
            self.db.query(ValuationRecord)
            .filter(ValuationRecord.id == record_id)
            .first()
        )

    def list_valuation_records(
        self, skip: int = 0, limit: int = 100
    ) -> List[ValuationRecord]:
        """List valuation records with pagination"""
        return self.db.query(ValuationRecord).offset(skip).limit(limit).all()

    def search_by_value_range(
        self, min_value: float, max_value: float
    ) -> List[ValuationRecord]:
        """Search records by estimated value range"""
        return (
            self.db.query(ValuationRecord)
            .filter(
                ValuationRecord.estimated_value >= min_value,
                ValuationRecord.estimated_value <= max_value,
            )
            .all()
        )

    def get_high_value_items(self, threshold: float = 100.0) -> List[ValuationRecord]:
        """Get items above a certain value threshold"""
        return (
            self.db.query(ValuationRecord)
            .filter(ValuationRecord.estimated_value >= threshold)
            .order_by(ValuationRecord.estimated_value.desc())
            .all()
        )

    def update_notes(self, record_id: int, notes: str) -> bool:
        """Update notes for a valuation record"""
        record = self.get_valuation_record(record_id)
        if record:
            record.notes = notes
            record.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False


class InventoryRepository:
    """Repository for inventory item operations"""

    def __init__(self, db: Session):
        self.db = db

    def create_from_valuation(
        self, valuation_record: ValuationRecord, location: str = ""
    ) -> InventoryItem:
        """Create an inventory item from a valuation record"""

        # Extract first identified item for inventory
        identification_data = valuation_record.identification_data
        first_item = None
        if identification_data and identification_data.get("identified_items"):
            first_item = identification_data["identified_items"][0]

        item = InventoryItem(
            item_number=first_item.get("item_number") if first_item else None,
            item_name=first_item.get("name") if first_item else "Unknown LEGO Item",
            item_type=first_item.get("item_type") if first_item else "unknown",
            condition=first_item.get("condition") if first_item else "unknown",
            year_released=first_item.get("year_released") if first_item else None,
            theme=first_item.get("theme") if first_item else None,
            category=first_item.get("category") if first_item else None,
            pieces=first_item.get("pieces") if first_item else None,
            estimated_value=valuation_record.estimated_value,
            current_market_price=valuation_record.estimated_value,
            last_price_update=datetime.utcnow(),
            location=location,
            valuation_record_id=valuation_record.id,
        )

        self.db.add(item)
        self.db.commit()
        self.db.refresh(item)

        return item

    def list_inventory(self, status: Optional[str] = None) -> List[InventoryItem]:
        """List inventory items, optionally filtered by status"""
        query = self.db.query(InventoryItem)
        if status:
            query = query.filter(InventoryItem.status == status)
        return query.order_by(InventoryItem.estimated_value.desc()).all()

    def get_inventory_summary(self) -> Dict[str, Any]:
        """Get inventory summary statistics"""
        total_items = self.db.query(InventoryItem).count()
        total_value = (
            self.db.query(func.sum(InventoryItem.estimated_value)).scalar() or 0
        )

        by_status = (
            self.db.query(InventoryItem.status, func.count(InventoryItem.id))
            .group_by(InventoryItem.status)
            .all()
        )

        return {
            "total_items": total_items,
            "total_estimated_value": total_value,
            "items_by_status": dict(by_status),
        }

    def update_location(self, item_id: int, location: str) -> bool:
        """Update the location of an inventory item"""
        item = self.db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        if item:
            item.location = location
            item.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False

    def mark_as_sold(self, item_id: int) -> bool:
        """Mark an inventory item as sold"""
        item = self.db.query(InventoryItem).filter(InventoryItem.id == item_id).first()
        if item:
            item.status = "sold"
            item.updated_at = datetime.utcnow()
            self.db.commit()
            return True
        return False


class SaleRepository:
    """Repository for sale record operations"""

    def __init__(self, db: Session):
        self.db = db

    def record_sale(
        self,
        inventory_item_id: int,
        sale_price: float,
        platform: str,
        buyer_info: str = "",
        platform_fees: float = 0.0,
        shipping_cost: float = 0.0,
    ) -> SaleRecord:
        """Record a sale"""

        # Calculate net profit
        net_profit = sale_price - platform_fees - shipping_cost

        sale = SaleRecord(
            inventory_item_id=inventory_item_id,
            sale_price=sale_price,
            platform_sold=platform,
            buyer_info=buyer_info,
            sold_date=datetime.utcnow(),
            platform_fees=platform_fees,
            shipping_cost=shipping_cost,
            net_profit=net_profit,
        )

        self.db.add(sale)
        self.db.commit()
        self.db.refresh(sale)

        return sale

    def get_sales_summary(self) -> Dict[str, Any]:
        """Get sales summary statistics"""
        total_sales = self.db.query(SaleRecord).count()
        total_revenue = self.db.query(func.sum(SaleRecord.sale_price)).scalar() or 0
        total_profit = self.db.query(func.sum(SaleRecord.net_profit)).scalar() or 0

        return {
            "total_sales": total_sales,
            "total_revenue": total_revenue,
            "total_profit": total_profit,
        }
