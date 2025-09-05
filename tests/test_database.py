import pytest
import tempfile
import json
from datetime import datetime
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from unittest.mock import Mock, patch

from src.database.database import DatabaseManager
from src.database.models import Base, ValuationRecord, InventoryItem, SaleRecord
from src.database.repository import ValuationRepository
from src.models.schemas import (
    ValuationReport, IdentificationResult, ValuationResult,
    LegoItem, ItemType, ItemCondition, RecommendationCategory, 
    PlatformType, MarketData
)


class TestDatabaseModels:
    """Test database model definitions and relationships"""
    
    @pytest.fixture
    def test_engine(self):
        """Create in-memory SQLite database for testing"""
        engine = create_engine("sqlite:///:memory:")
        Base.metadata.create_all(engine)
        return engine
    
    @pytest.fixture
    def test_session(self, test_engine):
        """Create test database session"""
        Session = sessionmaker(bind=test_engine)
        session = Session()
        yield session
        session.close()
    
    def test_valuation_record_creation(self, test_session):
        """Test creating a valuation record"""
        valuation = ValuationRecord(
            image_filename="test.jpg",
            original_filename="test_original.jpg",
            identification_data={"confidence_score": 0.9},
            confidence_score=0.9,
            estimated_value=100.0,
            valuation_confidence=0.85,
            recommendation_category="museum",
            reasoning="High value item"
        )
        
        test_session.add(valuation)
        test_session.commit()
        
        assert valuation.id is not None
        assert valuation.confidence_score == 0.9
        assert valuation.estimated_value == 100.0
        assert valuation.created_at is not None
    
    def test_inventory_item_creation(self, test_session):
        """Test creating an inventory item"""
        item = InventoryItem(
            item_number="sw0001a",
            item_name="Luke Skywalker",
            item_type="minifigure",
            condition="used_complete",
            year_released=1999,
            theme="Star Wars",
            estimated_value=50.0,
            status="in_inventory"
        )
        
        test_session.add(item)
        test_session.commit()
        
        assert item.id is not None
        assert item.item_name == "Luke Skywalker"
        assert item.estimated_value == 50.0
    
    def test_sale_record_creation(self, test_session):
        """Test creating a sale record"""
        sale = SaleRecord(
            inventory_item_id=1,
            valuation_record_id=1,
            sale_price=75.50,
            platform_sold="ebay",
            buyer_info="anonymous_buyer_123",
            sold_date=datetime.now(),
            platform_fees=7.55,
            shipping_cost=5.00,
            net_profit=62.95
        )
        
        test_session.add(sale)
        test_session.commit()
        
        assert sale.id is not None
        assert sale.sale_price == 75.50
        assert sale.platform_sold == "ebay"
    
    def test_relationships(self, test_session):
        """Test relationships between models"""
        # Create related records
        valuation = ValuationRecord(
            image_filename="test.jpg",
            identification_data={},
            confidence_score=0.9,
            estimated_value=100.0
        )
        
        test_session.add(valuation)
        test_session.commit()
        
        item = InventoryItem(
            item_name="Test Item",
            item_type="minifigure",
            valuation_record_id=valuation.id,
            estimated_value=100.0
        )
        
        test_session.add(item)
        test_session.commit()
        
        sale = SaleRecord(
            inventory_item_id=item.id,
            valuation_record_id=valuation.id,
            sale_price=120.0,
            sold_date=datetime.now()
        )
        
        test_session.add(sale)
        test_session.commit()
        
        # Test relationships via IDs
        assert item.valuation_record_id == valuation.id
        assert sale.valuation_record_id == valuation.id
        assert sale.inventory_item_id == item.id


class TestValuationRepository:
    """Test repository pattern implementation"""
    
    @pytest.fixture
    def test_db(self):
        """Create test database manager"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        db_manager = DatabaseManager(f"sqlite:///{db_path}")
        db_manager.init_db()
        yield db_manager
        
        # Cleanup
        import os
        os.unlink(db_path)
    
    @pytest.fixture
    def repository(self, test_db):
        """Create repository instance"""
        return ValuationRepository(test_db)
    
    @pytest.fixture
    def sample_report(self):
        """Create sample valuation report"""
        identification = IdentificationResult(
            confidence_score=0.85,
            identified_items=[
                LegoItem(
                    item_number="sw0001a",
                    name="Luke Skywalker",
                    item_type=ItemType.MINIFIGURE,
                    condition=ItemCondition.USED_COMPLETE,
                    year_released=1999,
                    theme="Star Wars"
                )
            ],
            description="Luke Skywalker minifigure",
            condition_assessment="Good condition"
        )
        
        valuation = ValuationResult(
            estimated_value=50.0,
            confidence_score=0.8,
            recommendation=RecommendationCategory.RESALE,
            reasoning="Good market demand",
            suggested_platforms=[PlatformType.EBAY, PlatformType.BRICKLINK],
            market_data=MarketData(
                current_price=45.0,
                avg_price_6m=48.0,
                times_sold=25,
                availability="common"
            )
        )
        
        return ValuationReport(
            image_filename="test.jpg",
            upload_timestamp=datetime.now(),
            identification=identification,
            valuation=valuation
        )
    
    def test_save_valuation(self, repository, sample_report):
        """Test saving valuation to database"""
        valuation_id = repository.save_valuation(sample_report)
        
        assert valuation_id is not None
        assert isinstance(valuation_id, int)
        assert valuation_id > 0
    
    def test_get_valuation(self, repository, sample_report):
        """Test retrieving valuation from database"""
        valuation_id = repository.save_valuation(sample_report)
        
        # Test retrieval within the same session context
        with repository.db_manager.get_session_context() as session:
            retrieved = session.query(ValuationRecord).filter(
                ValuationRecord.id == valuation_id
            ).first()
            
            assert retrieved is not None
            assert retrieved.estimated_value == 50.0
            assert retrieved.confidence_score == 0.85  # identification confidence
            assert retrieved.recommendation_category == "resale"
    
    def test_get_nonexistent_valuation(self, repository):
        """Test retrieving non-existent valuation"""
        retrieved = repository.get_valuation(99999)
        assert retrieved is None
    
    def test_list_valuations(self, repository, sample_report):
        """Test listing valuations with pagination"""
        # Save multiple valuations
        for i in range(5):
            repository.save_valuation(sample_report)
        
        # Test pagination
        valuations = repository.list_valuations(limit=3, offset=0)
        assert len(valuations) == 3
        
        valuations = repository.list_valuations(limit=10, offset=3)
        assert len(valuations) == 2
    
    def test_search_valuations(self, repository):
        """Test searching valuations"""
        # Create valuations with different items
        report1 = self._create_report_with_item("Luke Skywalker", "sw0001a")
        report2 = self._create_report_with_item("Darth Vader", "sw0002") 
        report3 = self._create_report_with_item("Luke Skywalker", "sw0001b")
        
        repository.save_valuation(report1)
        repository.save_valuation(report2)
        repository.save_valuation(report3)
        
        # Search for Luke - access attributes within session
        with repository.db_manager.get_session_context() as session:
            results = session.query(ValuationRecord).filter(
                ValuationRecord.reasoning.contains("Good demand")
            ).all()
            # All our test reports have "Good demand" reasoning
            assert len(results) == 3
            
        # Search for specific reasoning text
        with repository.db_manager.get_session_context() as session:
            results = session.query(ValuationRecord).filter(
                ValuationRecord.reasoning.contains("demand")
            ).all() 
            assert len(results) == 3
    
    def test_get_statistics(self, repository, sample_report):
        """Test getting valuation statistics"""
        # Save multiple valuations
        for i in range(3):
            repository.save_valuation(sample_report)
        
        stats = repository.get_statistics()
        
        assert stats['total_valuations'] == 3
        assert stats['average_value'] == 50.0
        assert stats['total_value'] == 150.0
    
    def test_save_market_data(self, repository):
        """Test saving market data"""
        market_data = MarketData(
            current_price=30.0,
            avg_price_6m=35.0,
            times_sold=15,
            availability="uncommon"
        )
        
        # First save a valuation
        valuation_id = repository.save_valuation(self._create_simple_report())
        
        # Save market data
        market_id = repository.save_market_data(
            valuation_id=valuation_id,
            item_number="sw0001a",
            item_name="Luke Skywalker",
            market_data=market_data
        )
        
        assert market_id is not None
        assert isinstance(market_id, int)
    
    def test_update_valuation_status(self, repository, sample_report):
        """Test updating valuation status"""
        valuation_id = repository.save_valuation(sample_report)
        
        # Update status
        success = repository.update_valuation_status(valuation_id, "reviewed")
        assert success is True
        
        # Verify update within session
        with repository.db_manager.get_session_context() as session:
            valuation = session.query(ValuationRecord).filter(
                ValuationRecord.id == valuation_id
            ).first()
            assert valuation.status == "reviewed"
    
    def test_delete_valuation(self, repository, sample_report):
        """Test deleting valuation"""
        valuation_id = repository.save_valuation(sample_report)
        
        # Delete
        success = repository.delete_valuation(valuation_id)
        assert success is True
        
        # Verify deletion
        valuation = repository.get_valuation(valuation_id)
        assert valuation is None
    
    def _create_report_with_item(self, name, item_number):
        """Helper to create report with specific item"""
        identification = IdentificationResult(
            confidence_score=0.85,
            identified_items=[
                LegoItem(
                    item_number=item_number,
                    name=name,
                    item_type=ItemType.MINIFIGURE,
                    condition=ItemCondition.USED_COMPLETE
                )
            ],
            description=f"{name} minifigure",
            condition_assessment="Good"
        )
        
        valuation = ValuationResult(
            estimated_value=50.0,
            confidence_score=0.8,
            recommendation=RecommendationCategory.RESALE,
            reasoning="Good demand",
            suggested_platforms=[PlatformType.EBAY]
        )
        
        return ValuationReport(
            image_filename="test.jpg",
            upload_timestamp=datetime.now(),
            identification=identification,
            valuation=valuation
        )
    
    def _create_simple_report(self):
        """Helper to create simple report"""
        return self._create_report_with_item("Test Item", "test001")


class TestDatabaseManager:
    """Test database manager functionality"""
    
    def test_init_db(self):
        """Test database initialization"""
        with tempfile.NamedTemporaryFile(suffix='.db', delete=False) as tmp:
            db_path = tmp.name
        
        db_manager = DatabaseManager(f"sqlite:///{db_path}")
        db_manager.init_db()
        
        # Verify tables were created
        with db_manager.get_session_context() as session:
            # Try to query - should not raise
            session.query(ValuationRecord).count()
            session.query(InventoryItem).count()
            session.query(SaleRecord).count()
        
        # Cleanup
        import os
        os.unlink(db_path)
    
    def test_get_session_context_manager(self):
        """Test session context manager"""
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.init_db()
        
        with db_manager.get_session_context() as session:
            assert session is not None
            # Session should be active
            assert session.is_active
    
    def test_transaction_rollback(self):
        """Test transaction rollback on error"""
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.init_db()
        
        try:
            with db_manager.get_session_context() as session:
                valuation = ValuationRecord(
                    image_filename="test.jpg",
                    identification_data={},
                    confidence_score=0.9,
                    estimated_value=100.0
                )
                session.add(valuation)
                
                # Force an error
                raise ValueError("Test error")
        except ValueError:
            pass
        
        # Verify nothing was committed
        with db_manager.get_session_context() as session:
            count = session.query(ValuationRecord).count()
            assert count == 0
    
    def test_concurrent_sessions(self):
        """Test handling multiple concurrent sessions"""
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.init_db()
        
        # Create multiple sessions
        sessions = []
        for i in range(3):
            session = db_manager.Session()
            sessions.append(session)
            
            # Each session should be independent
            valuation = ValuationRecord(
                image_filename=f"test{i}.jpg",
                identification_data={"session": i},
                confidence_score=0.9,
                estimated_value=100.0 * (i + 1)
            )
            session.add(valuation)
            session.commit()
            session.close()
        
        # Verify all were saved
        with db_manager.get_session_context() as session:
            count = session.query(ValuationRecord).count()
            assert count == 3
            
            valuations = session.query(ValuationRecord).all()
            values = [v.estimated_value for v in valuations]
            assert sorted(values) == [100.0, 200.0, 300.0]


class TestDatabaseIntegration:
    """Integration tests for database operations"""
    
    @pytest.fixture
    def integrated_system(self):
        """Create integrated database system"""
        db_manager = DatabaseManager("sqlite:///:memory:")
        db_manager.init_db()
        repository = ValuationRepository(db_manager)
        return db_manager, repository
    
    def test_full_workflow(self, integrated_system):
        """Test complete database workflow"""
        db_manager, repository = integrated_system
        
        # Create and save multiple reports
        reports = []
        for i in range(3):
            report = self._create_test_report(f"Item {i}", 50.0 * (i + 1))
            valuation_id = repository.save_valuation(report)
            reports.append(valuation_id)
        
        # Test retrieval
        for i, val_id in enumerate(reports):
            valuation = repository.get_valuation(val_id)
            assert valuation is not None
            assert valuation['estimated_value'] == 50.0 * (i + 1)
        
        # Test statistics
        stats = repository.get_statistics()
        assert stats['total_valuations'] == 3
        assert stats['total_value'] == 300.0  # 50 + 100 + 150
        assert stats['average_value'] == 100.0
        
        # Test search
        results = repository.search_valuations("Test reasoning")
        assert len(results) == 3
        
        # Test deletion
        repository.delete_valuation(reports[0])
        remaining = repository.list_valuations()
        assert len(remaining) == 2
    
    def _create_test_report(self, item_name, value):
        """Helper to create test report"""
        identification = IdentificationResult(
            confidence_score=0.85,
            identified_items=[
                LegoItem(
                    name=item_name,
                    item_type=ItemType.MINIFIGURE,
                    condition=ItemCondition.USED_COMPLETE
                )
            ],
            description=f"{item_name} description",
            condition_assessment="Good"
        )
        
        valuation = ValuationResult(
            estimated_value=value,
            confidence_score=0.8,
            recommendation=RecommendationCategory.RESALE,
            reasoning="Test reasoning",
            suggested_platforms=[PlatformType.EBAY]
        )
        
        return ValuationReport(
            image_filename="test.jpg",
            upload_timestamp=datetime.now(),
            identification=identification,
            valuation=valuation
        )


if __name__ == "__main__":
    pytest.main([__file__, "-v"])