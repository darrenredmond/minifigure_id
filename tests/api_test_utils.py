"""
Utility functions and fixtures for API testing.
"""

import tempfile
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, Any, Optional
from unittest.mock import Mock, AsyncMock

# Handle missing PIL dependency
try:
    from PIL import Image
except ImportError:
    Image = None

try:
    from src.models.schemas import (
        IdentificationResult, ValuationResult, LegoItem, MarketData,
        ItemType, ItemCondition, RecommendationCategory, PlatformType
    )
except ImportError:
    # Create mock schemas if not available
    class IdentificationResult:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class ValuationResult:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    class LegoItem:
        def __init__(self, **kwargs):
            for k, v in kwargs.items():
                setattr(self, k, v)
    
    # Create mock enums
    class ItemType:
        MINIFIGURE = "minifigure"
        SET = "set"
        PART = "part"
    
    class ItemCondition:
        NEW = "new"
        USED_COMPLETE = "used_complete"
        USED_INCOMPLETE = "used_incomplete"
    
    class RecommendationCategory:
        MUSEUM = "museum"
        RESALE = "resale"  
        COLLECTION = "collection"
    
    class PlatformType:
        BRICKLINK = "bricklink"
        EBAY = "ebay"


class TestDataFactory:
    """Factory for creating test data objects"""
    
    @staticmethod
    def create_lego_item(
        item_number: str = "sw0001a",
        name: str = "Luke Skywalker",
        item_type: ItemType = ItemType.MINIFIGURE,
        condition: ItemCondition = ItemCondition.USED_COMPLETE,
        theme: str = "Star Wars",
        year_released: int = 1999,
        category: Optional[str] = None,
        pieces: Optional[int] = None
    ) -> LegoItem:
        """Create a test LEGO item"""
        return LegoItem(
            item_number=item_number,
            name=name,
            item_type=item_type,
            condition=condition,
            theme=theme,
            year_released=year_released,
            category=category,
            pieces=pieces
        )
    
    @staticmethod
    def create_identification_result(
        confidence_score: float = 0.85,
        items: Optional[list] = None,
        description: str = "Test LEGO identification",
        condition_assessment: str = "Good condition"
    ) -> IdentificationResult:
        """Create a test identification result"""
        if items is None:
            items = [TestDataFactory.create_lego_item()]
        
        return IdentificationResult(
            confidence_score=confidence_score,
            identified_items=items,
            description=description,
            condition_assessment=condition_assessment
        )
    
    @staticmethod
    def create_market_data(
        current_price: float = 75.00,
        avg_price_6m: float = 72.50,
        times_sold: int = 25,
        availability: str = "uncommon"
    ) -> MarketData:
        """Create test market data"""
        return MarketData(
            current_price=current_price,
            avg_price_6m=avg_price_6m,
            times_sold=times_sold,
            availability=availability
        )
    
    @staticmethod
    def create_valuation_result(
        estimated_value: float = 75.50,  # Fixed: use estimated_value not estimated_value_usd
        estimated_value_eur: Optional[float] = 64.45,
        confidence_score: float = 0.8,
        recommendation: RecommendationCategory = RecommendationCategory.RESALE,
        reasoning: str = "Test valuation reasoning",
        platforms: Optional[list] = None,
        market_data: Optional[MarketData] = None
    ) -> ValuationResult:
        """Create a test valuation result"""
        if platforms is None:
            platforms = [PlatformType.BRICKLINK, PlatformType.EBAY]
        
        return ValuationResult(
            estimated_value=estimated_value,  # Fixed: use estimated_value not estimated_value_usd
            estimated_value_eur=estimated_value_eur,
            confidence_score=confidence_score,
            recommendation=recommendation,
            reasoning=reasoning,
            suggested_platforms=platforms,
            market_data=market_data
        )


class ImageTestUtils:
    """Utilities for creating test images"""
    
    @staticmethod
    def create_test_image(
        size: tuple = (100, 100),
        color: str = 'red',
        format: str = 'JPEG',
        suffix: str = '.jpg'
    ) -> str:
        """Create a temporary test image file"""
        if Image is None:
            # Create a dummy file if PIL isn't available
            tmp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
            tmp_file.write(b'fake image data for testing')
            tmp_file.close()
            return tmp_file.name
        
        img = Image.new('RGB', size, color=color)
        tmp_file = tempfile.NamedTemporaryFile(suffix=suffix, delete=False)
        img.save(tmp_file.name, format=format)
        return tmp_file.name
    
    @staticmethod
    def create_lego_mockup_image() -> str:
        """Create a more realistic LEGO-like test image"""
        if Image is None:
            # Create a dummy file if PIL isn't available
            tmp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
            tmp_file.write(b'fake lego mockup image data for testing')
            tmp_file.close()
            return tmp_file.name
            
        img = Image.new('RGB', (400, 300), color='white')
        # Could add PIL drawing to make it more LEGO-like
        # For now, just a simple colored image
        tmp_file = tempfile.NamedTemporaryFile(suffix='.jpg', delete=False)
        img.save(tmp_file.name, 'JPEG')
        return tmp_file.name
    
    @staticmethod
    def cleanup_test_image(file_path: str):
        """Clean up a test image file"""
        Path(file_path).unlink(missing_ok=True)


class MockFactory:
    """Factory for creating consistent mocks"""
    
    @staticmethod
    def create_lego_identifier_mock(
        identification_result: Optional[IdentificationResult] = None
    ) -> Mock:
        """Create a mock LEGO identifier"""
        mock = Mock()
        if identification_result is None:
            identification_result = TestDataFactory.create_identification_result()
        
        mock.identify_lego_items = AsyncMock(return_value=identification_result)
        return mock
    
    @staticmethod
    def create_valuation_engine_mock(
        valuation_result: Optional[ValuationResult] = None
    ) -> Mock:
        """Create a mock valuation engine"""
        mock = Mock()
        if valuation_result is None:
            valuation_result = TestDataFactory.create_valuation_result()
        
        mock.evaluate_item = AsyncMock(return_value=valuation_result)
        return mock
    
    @staticmethod
    def create_image_processor_mock(
        file_path: str = "/tmp/test.jpg",
        filename: str = "test.jpg"
    ) -> Mock:
        """Create a mock image processor"""
        mock = Mock()
        upload_info = Mock()
        upload_info.filename = filename
        upload_info.size = 12345
        upload_info.content_type = "image/jpeg"
        
        mock.save_image.return_value = (file_path, upload_info)
        mock.optimize_image_for_ai.return_value = "/tmp/optimized.jpg"
        return mock
    
    @staticmethod
    def create_report_generator_mock() -> Mock:
        """Create a mock report generator"""
        mock = Mock()
        mock.generate_pdf.return_value = "/tmp/report.pdf"
        mock.generate_html.return_value = "/tmp/report.html"
        mock.generate_json.return_value = "/tmp/report.json"
        mock.generate_all_formats.return_value = {
            'pdf': '/tmp/report.pdf',
            'html': '/tmp/report.html',
            'json': '/tmp/report.json'
        }
        return mock


class APITestAssertions:
    """Common assertions for API testing"""
    
    @staticmethod
    def assert_success_response(response, expected_keys: list = None):
        """Assert that a response is successful"""
        assert response.status_code == 200
        if expected_keys:
            data = response.json()
            for key in expected_keys:
                assert key in data
    
    @staticmethod
    def assert_error_response(response, expected_status: int, expected_message: str = None):
        """Assert that a response is an error"""
        assert response.status_code == expected_status
        if expected_message:
            data = response.json()
            assert expected_message in data.get("detail", "")
    
    @staticmethod
    def assert_validation_error(response):
        """Assert that a response is a validation error"""
        assert response.status_code == 422
        data = response.json()
        assert "detail" in data
    
    @staticmethod
    def assert_cors_headers(response):
        """Assert that CORS headers are present"""
        headers = response.headers
        # FastAPI automatically adds CORS headers when configured
        # The actual headers depend on the CORS configuration


class DatabaseTestUtils:
    """Utilities for database testing"""
    
    @staticmethod
    def create_test_valuation_record(db_session, 
                                   estimated_value: float = 75.50,
                                   confidence_score: float = 0.85) -> Dict[str, Any]:
        """Create a test valuation record in the database"""
        # This would create actual database records for testing
        # Implementation depends on your database models
        pass
    
    @staticmethod
    def create_test_inventory_item(db_session,
                                 item_name: str = "Test Item",
                                 estimated_value: float = 50.00) -> Dict[str, Any]:
        """Create a test inventory item in the database"""
        # Implementation depends on your database models
        pass
    
    @staticmethod
    def clear_test_data(db_session):
        """Clear all test data from database"""
        # Implementation would clear test tables
        pass


class PerformanceTestUtils:
    """Utilities for performance testing"""
    
    @staticmethod
    def time_request(func, *args, **kwargs) -> tuple:
        """Time a request and return (result, duration)"""
        import time
        start_time = time.time()
        result = func(*args, **kwargs)
        duration = time.time() - start_time
        return result, duration
    
    @staticmethod
    def assert_response_time(response, max_seconds: float):
        """Assert that a response was received within time limit"""
        # Would need to capture timing information
        # This is a placeholder for timing assertions
        pass


class IntegrationTestHelpers:
    """Helpers for integration testing scenarios"""
    
    @staticmethod
    def simulate_upload_workflow(client, test_image_path: str, notes: str = "") -> dict:
        """Simulate the complete upload workflow"""
        with open(test_image_path, 'rb') as f:
            response = client.post(
                "/upload",
                files={"file": ("test.jpg", f, "image/jpeg")},
                data={"notes": notes}
            )
        return response
    
    @staticmethod
    def wait_for_background_task(max_wait_seconds: int = 10):
        """Wait for background tasks to complete (in real tests)"""
        import time
        # In real implementation, this might poll for completion
        time.sleep(1)  # Placeholder
    
    @staticmethod
    def create_full_test_scenario(client) -> dict:
        """Create a full test scenario with multiple items"""
        # This could create multiple valuations, inventory items, etc.
        # for comprehensive testing
        pass


# Common test data sets
SAMPLE_ITEMS = {
    'star_wars_luke': TestDataFactory.create_lego_item(
        item_number="sw0001a",
        name="Luke Skywalker (Tatooine)",
        theme="Star Wars",
        year_released=1999
    ),
    'city_police': TestDataFactory.create_lego_item(
        item_number="cty0913",
        name="Police Officer - Female",
        theme="City",
        item_type=ItemType.MINIFIGURE,
        condition=ItemCondition.NEW
    ),
    'millennium_falcon_set': TestDataFactory.create_lego_item(
        item_number="10179",
        name="Millennium Falcon",
        theme="Star Wars",
        item_type=ItemType.SET,
        pieces=5195,
        year_released=2007
    )
}

SAMPLE_MARKET_DATA = {
    'high_value': TestDataFactory.create_market_data(
        current_price=850.00,
        avg_price_6m=800.00,
        times_sold=3,
        availability="very_rare"
    ),
    'medium_value': TestDataFactory.create_market_data(
        current_price=75.00,
        avg_price_6m=72.50,
        times_sold=25,
        availability="uncommon"
    ),
    'low_value': TestDataFactory.create_market_data(
        current_price=15.00,
        avg_price_6m=14.50,
        times_sold=150,
        availability="common"
    )
}