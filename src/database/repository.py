from typing import List, Optional, Dict, Any
from sqlalchemy.orm import Session
from sqlalchemy import func, desc, or_
from datetime import datetime
import json

from .models import ValuationRecord, InventoryItem, SaleRecord
from src.models.schemas import ValuationReport, IdentificationResult, ValuationResult, MarketData


class ValuationRepository:
    """Repository for valuation record operations"""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def save_valuation(self, report: ValuationReport) -> int:
        """Save a valuation report to the database"""
        with self.db_manager.get_session_context() as session:
            # Serialize complex objects to JSON
            identification_data = {
                "confidence_score": report.identification.confidence_score,
                "identified_items": [
                    item.model_dump() for item in report.identification.identified_items
                ],
                "description": report.identification.description,
                "condition_assessment": report.identification.condition_assessment,
            }

            market_data = None
            if report.valuation.market_data:
                market_data = report.valuation.market_data.model_dump()

            record = ValuationRecord(
                image_filename=report.image_filename,
                original_filename=report.image_filename,
                identification_data=identification_data,
                confidence_score=report.identification.confidence_score,
                estimated_value=report.valuation.estimated_value,
                valuation_confidence=report.valuation.confidence_score,
                recommendation_category=report.valuation.recommendation.value,
                reasoning=report.valuation.reasoning,
                suggested_platforms=[p.value for p in report.valuation.suggested_platforms],
                market_data=market_data,
                upload_timestamp=report.upload_timestamp,
                created_at=datetime.utcnow()
            )

            session.add(record)
            session.flush()  # Get the ID
            return record.id

    def get_valuation(self, valuation_id: int) -> Optional[dict]:
        """Get a valuation record by ID, returned as dict to avoid session issues"""
        with self.db_manager.get_session_context() as session:
            valuation = session.query(ValuationRecord).filter(
                ValuationRecord.id == valuation_id
            ).first()
            if valuation:
                # Return as dict to avoid detached instance issues
                return {
                    'id': valuation.id,
                    'estimated_value': valuation.estimated_value,
                    'confidence_score': valuation.confidence_score,
                    'recommendation_category': valuation.recommendation_category,
                    'reasoning': valuation.reasoning,
                    'image_filename': valuation.image_filename,
                    'created_at': valuation.created_at,
                    'status': valuation.status
                }
            return None

    def list_valuations(self, limit: int = 50, offset: int = 0) -> List[ValuationRecord]:
        """List valuation records with pagination"""
        with self.db_manager.get_session_context() as session:
            return session.query(ValuationRecord).order_by(
                desc(ValuationRecord.created_at)
            ).limit(limit).offset(offset).all()

    def search_valuations(self, search_term: str) -> List[ValuationRecord]:
        """Search valuations by item name or description"""
        with self.db_manager.get_session_context() as session:
            # Search in JSON fields - SQLite doesn't have full JSON support
            # So we'll search in the reasoning and notes fields
            return session.query(ValuationRecord).filter(
                or_(
                    ValuationRecord.reasoning.contains(search_term),
                    ValuationRecord.notes.contains(search_term) if ValuationRecord.notes else False
                )
            ).all()

    def get_statistics(self) -> Dict[str, Any]:
        """Get valuation statistics"""
        with self.db_manager.get_session_context() as session:
            total_valuations = session.query(func.count(ValuationRecord.id)).scalar()
            total_value = session.query(func.sum(ValuationRecord.estimated_value)).scalar() or 0
            average_value = total_value / total_valuations if total_valuations > 0 else 0

            return {
                "total_valuations": total_valuations,
                "total_value": float(total_value),
                "average_value": float(average_value)
            }

    def save_market_data(self, valuation_id: int, item_number: str, item_name: str, market_data: MarketData) -> int:
        """Save market data for a valuation (updates the valuation record)"""
        with self.db_manager.get_session_context() as session:
            valuation = session.query(ValuationRecord).filter(
                ValuationRecord.id == valuation_id
            ).first()
            
            if valuation:
                valuation.market_data = market_data.model_dump()
                session.flush()
                return valuation.id
            return None

    def update_valuation_status(self, valuation_id: int, status: str) -> bool:
        """Update valuation status"""
        with self.db_manager.get_session_context() as session:
            valuation = session.query(ValuationRecord).filter(
                ValuationRecord.id == valuation_id
            ).first()
            
            if valuation:
                valuation.status = status
                valuation.updated_at = datetime.utcnow()
                return True
            return False

    def delete_valuation(self, valuation_id: int) -> bool:
        """Delete a valuation record"""
        with self.db_manager.get_session_context() as session:
            valuation = session.query(ValuationRecord).filter(
                ValuationRecord.id == valuation_id
            ).first()
            
            if valuation:
                session.delete(valuation)
                return True
            return False

    def get_valuations_by_date_range(self, start_date: datetime, end_date: datetime) -> List[ValuationRecord]:
        """Get valuations within a date range"""
        with self.db_manager.get_session_context() as session:
            return session.query(ValuationRecord).filter(
                ValuationRecord.created_at >= start_date,
                ValuationRecord.created_at <= end_date
            ).order_by(desc(ValuationRecord.created_at)).all()

    def get_valuations_by_recommendation(self, recommendation: str) -> List[ValuationRecord]:
        """Get valuations by recommendation category"""
        with self.db_manager.get_session_context() as session:
            return session.query(ValuationRecord).filter(
                ValuationRecord.recommendation_category == recommendation
            ).all()

    def get_high_value_items(self, min_value: float = 100.0) -> List[ValuationRecord]:
        """Get high-value items above a threshold"""
        with self.db_manager.get_session_context() as session:
            return session.query(ValuationRecord).filter(
                ValuationRecord.estimated_value >= min_value
            ).order_by(desc(ValuationRecord.estimated_value)).all()


class InventoryRepository:
    """Repository for inventory item operations"""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def add_item(self, item_data: Dict[str, Any]) -> int:
        """Add an item to inventory"""
        with self.db_manager.get_session_context() as session:
            item = InventoryItem(**item_data)
            session.add(item)
            session.flush()
            return item.id

    def get_item(self, item_id: int) -> Optional[InventoryItem]:
        """Get inventory item by ID"""
        with self.db_manager.get_session_context() as session:
            return session.query(InventoryItem).filter(
                InventoryItem.id == item_id
            ).first()

    def update_item_status(self, item_id: int, status: str) -> bool:
        """Update item status"""
        with self.db_manager.get_session_context() as session:
            item = session.query(InventoryItem).filter(
                InventoryItem.id == item_id
            ).first()
            
            if item:
                item.status = status
                item.updated_at = datetime.utcnow()
                return True
            return False

    def get_available_items(self) -> List[InventoryItem]:
        """Get all available inventory items"""
        with self.db_manager.get_session_context() as session:
            return session.query(InventoryItem).filter(
                InventoryItem.status == "in_inventory"
            ).all()


class SaleRepository:
    """Repository for sale record operations"""

    def __init__(self, db_manager):
        self.db_manager = db_manager

    def record_sale(self, sale_data: Dict[str, Any]) -> int:
        """Record a sale"""
        with self.db_manager.get_session_context() as session:
            # Calculate net profit if not provided
            if 'net_profit' not in sale_data:
                sale_price = sale_data.get('sale_price', 0)
                platform_fees = sale_data.get('platform_fees', 0)
                shipping_cost = sale_data.get('shipping_cost', 0)
                sale_data['net_profit'] = sale_price - platform_fees - shipping_cost

            sale = SaleRecord(**sale_data)
            session.add(sale)
            session.flush()
            return sale.id

    def get_sales_by_date_range(self, start_date: datetime, end_date: datetime) -> List[SaleRecord]:
        """Get sales within a date range"""
        with self.db_manager.get_session_context() as session:
            return session.query(SaleRecord).filter(
                SaleRecord.sold_date >= start_date,
                SaleRecord.sold_date <= end_date
            ).order_by(desc(SaleRecord.sold_date)).all()

    def get_sales_statistics(self) -> Dict[str, Any]:
        """Get sales statistics"""
        with self.db_manager.get_session_context() as session:
            total_sales = session.query(func.count(SaleRecord.id)).scalar()
            total_revenue = session.query(func.sum(SaleRecord.sale_price)).scalar() or 0
            total_profit = session.query(func.sum(SaleRecord.net_profit)).scalar() or 0

            return {
                "total_sales": total_sales,
                "total_revenue": float(total_revenue),
                "total_profit": float(total_profit),
                "average_sale_price": float(total_revenue / total_sales) if total_sales > 0 else 0
            }