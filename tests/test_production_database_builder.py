"""
Tests for Production Database Builder
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import shutil

from src.core.production_database_builder import ProductionDatabaseBuilder, MinifigureData


class TestProductionDatabaseBuilder:
    """Test the production database builder"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_production_database.db"
        self.builder = ProductionDatabaseBuilder(str(self.db_path))
    
    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test builder initialization"""
        assert self.builder.db_path == str(self.db_path)
        assert self.builder.images_dir is not None
        assert self.builder.bricklink_client is not None
        assert self.builder.session is not None
    
    def test_initialize_database(self):
        """Test database initialization"""
        self.builder.initialize_database()
        
        # Check if database file was created
        assert self.db_path.exists()
        
        # Check if tables were created by trying to get count
        count = self.builder.get_minifigure_count()
        assert count == 0  # Should be empty initially
    
    def test_get_comprehensive_minifigure_data(self):
        """Test getting comprehensive minifigure data"""
        data = self.builder._get_comprehensive_minifigure_data()
        
        assert isinstance(data, list)
        assert len(data) > 0
        
        # Check that all required fields are present
        for minifig in data:
            assert 'item_number' in minifig
            assert 'name' in minifig
            assert 'theme' in minifig
            assert 'year_released' in minifig
            assert 'description' in minifig
            assert 'rarity' in minifig
            assert 'image_url' in minifig
    
    def test_create_minifigure_variations(self):
        """Test creating minifigure variations"""
        base_minifig = {
            'item_number': 'test001',
            'name': 'Test Figure',
            'theme': 'Test',
            'year_released': 2020,
            'description': 'Test description',
            'rarity': 'common',
            'image_url': 'https://example.com/test.png'
        }
        
        variations = self.builder._create_minifigure_variations(base_minifig)
        
        assert isinstance(variations, list)
        assert len(variations) == 10  # Should create 10 variations
        
        # Check that variations have different item numbers
        item_numbers = [v['item_number'] for v in variations]
        assert len(set(item_numbers)) == 10  # All should be unique
        
        # Check that all variations have required fields
        for variation in variations:
            assert 'item_number' in variation
            assert 'name' in variation
            assert 'theme' in variation
            assert 'year_released' in variation
            assert 'description' in variation
            assert 'rarity' in variation
            assert 'image_url' in variation
    
    def test_generate_additional_minifigures(self):
        """Test generating additional minifigures"""
        additional = self.builder._generate_additional_minifigures(10)
        
        assert isinstance(additional, list)
        assert len(additional) == 10
        
        # Check that all have required fields
        for minifig in additional:
            assert 'item_number' in minifig
            assert 'name' in minifig
            assert 'theme' in minifig
            assert 'year_released' in minifig
            assert 'description' in minifig
            assert 'rarity' in minifig
            assert 'image_url' in minifig
    
    def test_add_comprehensive_mock_data(self):
        """Test adding comprehensive mock data"""
        self.builder.initialize_database()
        
        # Add a small amount of mock data
        added_count = self.builder._add_comprehensive_mock_data(50)
        
        assert added_count > 0
        assert self.builder.get_minifigure_count() > 0
    
    def test_search_minifigures(self):
        """Test searching minifigures"""
        self.builder.initialize_database()
        self.builder._add_comprehensive_mock_data(20)
        
        results = self.builder.search_minifigures("police")
        assert isinstance(results, list)
        
        # Should find police-related minifigures
        police_results = [r for r in results if "police" in r['name'].lower()]
        assert len(police_results) > 0
    
    def test_search_minifigures_no_results(self):
        """Test searching with no results"""
        self.builder.initialize_database()
        self.builder._add_comprehensive_mock_data(20)
        
        results = self.builder.search_minifigures("nonexistent")
        assert isinstance(results, list)
        assert len(results) == 0
    
    def test_get_minifigure_count(self):
        """Test getting minifigure count"""
        self.builder.initialize_database()
        assert self.builder.get_minifigure_count() == 0
        
        self.builder._add_comprehensive_mock_data(10)
        assert self.builder.get_minifigure_count() == 10
    
    @pytest.mark.asyncio
    async def test_try_bricklink_download_no_api(self):
        """Test trying BrickLink download when API is not available"""
        with patch.object(self.builder.bricklink_client, 'search_items', return_value=[]):
            count = await self.builder._try_bricklink_download(10)
            assert count == 0
    
    @pytest.mark.asyncio
    async def test_try_bricklink_download_with_api(self):
        """Test trying BrickLink download when API is available"""
        mock_results = [
            {'no': 'test001', 'name': 'Test Figure 1', 'year_released': 2020},
            {'no': 'test002', 'name': 'Test Figure 2', 'year_released': 2021}
        ]
        
        with patch.object(self.builder.bricklink_client, 'search_items', return_value=mock_results):
            with patch.object(self.builder, '_process_minifigure'):
                count = await self.builder._try_bricklink_download(10)
                assert count > 0
    
    @pytest.mark.asyncio
    async def test_build_production_database(self):
        """Test building production database"""
        with patch.object(self.builder, '_try_bricklink_download', return_value=0):
            with patch.object(self.builder, '_add_comprehensive_mock_data', return_value=100):
                total_count = await self.builder.build_production_database(100)
                assert total_count >= 0  # Should be non-negative
    
    def test_store_minifigure(self):
        """Test storing minifigure data"""
        self.builder.initialize_database()
        
        minifig = MinifigureData(
            item_number="test001",
            name="Test Figure",
            theme="Test",
            year_released=2020,
            image_url="https://example.com/test.png",
            description="Test description",
            rarity="common",
            source="test"
        )
        
        self.builder._store_minifigure(minifig)
        
        assert self.builder.get_minifigure_count() == 1
        
        # Verify the data was stored correctly
        results = self.builder.search_minifigures("test")
        assert len(results) == 1
        assert results[0]['item_number'] == "test001"
        assert results[0]['name'] == "Test Figure"


class TestMinifigureData:
    """Test the MinifigureData dataclass"""
    
    def test_minifigure_data_creation(self):
        """Test creating MinifigureData instance"""
        minifig = MinifigureData(
            item_number="test001",
            name="Test Figure",
            theme="Test",
            year_released=2020,
            image_url="https://example.com/test.png"
        )
        
        assert minifig.item_number == "test001"
        assert minifig.name == "Test Figure"
        assert minifig.theme == "Test"
        assert minifig.year_released == 2020
        assert minifig.image_url == "https://example.com/test.png"
        assert minifig.source == "bricklink"  # Default value
        assert minifig.parts is None  # Default value
        assert minifig.rarity is None  # Default value
    
    def test_minifigure_data_with_all_fields(self):
        """Test creating MinifigureData with all fields"""
        minifig = MinifigureData(
            item_number="test001",
            name="Test Figure",
            theme="Test",
            year_released=2020,
            image_url="https://example.com/test.png",
            image_path="/path/to/local/image.png",
            description="Test description",
            parts=[{"part_number": "123", "color": "red"}],
            rarity="rare",
            source="mock",
            last_updated=None
        )
        
        assert minifig.item_number == "test001"
        assert minifig.name == "Test Figure"
        assert minifig.theme == "Test"
        assert minifig.year_released == 2020
        assert minifig.image_url == "https://example.com/test.png"
        assert minifig.image_path == "/path/to/local/image.png"
        assert minifig.description == "Test description"
        assert minifig.parts == [{"part_number": "123", "color": "red"}]
        assert minifig.rarity == "rare"
        assert minifig.source == "mock"


class TestProductionDatabaseBuilderIntegration:
    """Integration tests for production database builder"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_integration_database.db"
        self.builder = ProductionDatabaseBuilder(str(self.db_path))
    
    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_full_database_build_integration(self):
        """Test full database build process"""
        # Initialize database
        self.builder.initialize_database()
        assert self.builder.get_minifigure_count() == 0
        
        # Add mock data
        added_count = self.builder._add_comprehensive_mock_data(20)
        assert added_count == 20
        assert self.builder.get_minifigure_count() == 20
        
        # Test search functionality
        results = self.builder.search_minifigures("police")
        assert isinstance(results, list)
        
        # Test getting minifigure count
        count = self.builder.get_minifigure_count()
        assert count >= 0
    
    def test_database_persistence(self):
        """Test that database persists between instances"""
        # Create first instance and add data
        builder1 = ProductionDatabaseBuilder(str(self.db_path))
        builder1.initialize_database()
        builder1._add_comprehensive_mock_data(10)
        
        # Create second instance and verify data is still there
        builder2 = ProductionDatabaseBuilder(str(self.db_path))
        assert builder2.get_minifigure_count() == 10
        
        # Verify search works
        results = builder2.search_minifigures("test")
        assert isinstance(results, list)
    
    def test_variation_generation_integration(self):
        """Test variation generation in integration context"""
        self.builder.initialize_database()
        
        # Get base data
        base_data = self.builder._get_comprehensive_minifigure_data()
        assert len(base_data) > 0
        
        # Create variations for first few items
        all_minifigures = base_data.copy()
        for base_minifig in base_data[:3]:  # Only first 3 to keep test fast
            variations = self.builder._create_minifigure_variations(base_minifig)
            all_minifigures.extend(variations)
        
        # Should have base + variations
        assert len(all_minifigures) > len(base_data)
        
        # All variations should have unique item numbers
        item_numbers = [m['item_number'] for m in all_minifigures]
        assert len(item_numbers) == len(set(item_numbers))
    
    def test_additional_minifigure_generation_integration(self):
        """Test additional minifigure generation in integration context"""
        self.builder.initialize_database()
        
        # Generate additional minifigures
        additional = self.builder._generate_additional_minifigures(15)
        assert len(additional) == 15
        
        # All should have unique item numbers
        item_numbers = [m['item_number'] for m in additional]
        assert len(item_numbers) == len(set(item_numbers))
        
        # All should have valid themes
        themes = [m['theme'] for m in additional]
        valid_themes = ["City", "Space", "Super Heroes", "Ninjago", "Castle", "Pirates", "Friends", "Generic", "Star Wars", "Harry Potter", "Marvel", "DC Comics", "Disney"]
        for theme in themes:
            assert theme in valid_themes
