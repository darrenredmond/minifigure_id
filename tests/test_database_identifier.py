"""
Tests for Database-Driven LEGO Identifier
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import shutil

from src.core.database_identifier import DatabaseDrivenIdentifier
from src.core.image_matcher import ImageMatcher, MatchResult
from src.core.mock_database_builder import MockDatabaseBuilder
from src.models.schemas import IdentificationResult, LegoItem, ItemType, ItemCondition


class TestDatabaseDrivenIdentifier:
    """Test the database-driven identifier"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.identifier = DatabaseDrivenIdentifier()
        self.mock_builder = MockDatabaseBuilder()
        self.mock_builder.initialize_database()
        self.mock_builder.populate_sample_data()
    
    def test_init(self):
        """Test identifier initialization"""
        assert self.identifier.image_matcher is not None
        assert self.identifier.ai_identifier is not None
        assert self.identifier.db_builder is not None
    
    @pytest.mark.asyncio
    async def test_identify_lego_items_success(self):
        """Test successful identification with database matches"""
        # Mock the image matcher to return matches
        mock_matches = [
            MatchResult(
                minifigure_id=1,
                item_number="cty001",
                name="Police Officer",
                theme="City",
                confidence=0.8,
                match_type="exact",
                image_path="/path/to/image.png",
                year_released=2020
            )
        ]
        
        with patch.object(self.identifier.image_matcher, 'find_matches', return_value=mock_matches):
            with patch.object(self.identifier.ai_identifier, 'identify_lego_items') as mock_ai:
                # Mock AI response
                mock_ai.return_value = IdentificationResult(
                    confidence_score=0.7,
                    identified_items=[],
                    description="Test description",
                    condition_assessment="Good condition"
                )
                
                result = await self.identifier.identify_lego_items("/test/image.jpg")
                
                assert result.confidence_score > 0.0
                assert len(result.identified_items) > 0
                assert result.description is not None
    
    @pytest.mark.asyncio
    async def test_identify_lego_items_no_database_matches(self):
        """Test identification when no database matches found"""
        with patch.object(self.identifier.image_matcher, 'find_matches', return_value=[]):
            with patch.object(self.identifier.ai_identifier, 'identify_lego_items') as mock_ai:
                # Mock AI response
                mock_ai.return_value = IdentificationResult(
                    confidence_score=0.6,
                    identified_items=[
                        LegoItem(
                            item_number=None,
                            name="Generic Figure",
                            item_type=ItemType.MINIFIGURE,
                            condition=ItemCondition.USED_COMPLETE,
                            year_released=None,
                            theme="Generic",
                            category=None,
                            pieces=None
                        )
                    ],
                    description="Generic minifigure",
                    condition_assessment="Good condition"
                )
                
                result = await self.identifier.identify_lego_items("/test/image.jpg")
                
                assert result.confidence_score > 0.0
                assert len(result.identified_items) > 0
    
    @pytest.mark.asyncio
    async def test_identify_lego_items_error_fallback(self):
        """Test fallback to AI when database matching fails"""
        with patch.object(self.identifier.image_matcher, 'find_matches', side_effect=Exception("Database error")):
            with patch.object(self.identifier.ai_identifier, 'identify_lego_items') as mock_ai:
                mock_ai.return_value = IdentificationResult(
                    confidence_score=0.5,
                    identified_items=[],
                    description="Fallback identification",
                    condition_assessment="Unknown condition"
                )
                
                result = await self.identifier.identify_lego_items("/test/image.jpg")
                
                assert result.confidence_score == 0.5
                assert result.description == "Fallback identification"
    
    def test_get_database_stats(self):
        """Test database statistics retrieval"""
        stats = self.identifier.get_database_stats()
        
        assert 'total_minifigures' in stats
        assert 'database_path' in stats
        assert 'images_directory' in stats
        assert stats['total_minifigures'] >= 0
    
    def test_search_database(self):
        """Test database search functionality"""
        results = self.identifier.search_database("police", limit=5)
        
        assert isinstance(results, list)
        # Should find police-related minifigures
        police_results = [r for r in results if "police" in r['name'].lower()]
        assert len(police_results) > 0
    
    def test_search_database_no_results(self):
        """Test database search with no results"""
        results = self.identifier.search_database("nonexistent", limit=5)
        
        assert isinstance(results, list)
        assert len(results) == 0


class TestImageMatcher:
    """Test the image matching functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.matcher = ImageMatcher()
        self.mock_builder = MockDatabaseBuilder()
        self.mock_builder.initialize_database()
        self.mock_builder.populate_sample_data()
    
    def test_init(self):
        """Test image matcher initialization"""
        assert self.matcher.sift is not None
        assert self.matcher.orb is not None
        assert self.matcher.match_threshold > 0
    
    def test_extract_features_nonexistent_file(self):
        """Test feature extraction with nonexistent file"""
        features = self.matcher.extract_features("/nonexistent/file.jpg")
        assert features == {}
    
    def test_match_features_empty(self):
        """Test feature matching with empty features"""
        result = self.matcher.match_features({}, {})
        assert result == 0.0
    
    def test_determine_match_type(self):
        """Test match type determination"""
        assert self.matcher._determine_match_type(0.9) == "exact"
        assert self.matcher._determine_match_type(0.7) == "similar"
        assert self.matcher._determine_match_type(0.4) == "partial"
    
    def test_get_all_minifigures(self):
        """Test getting all minifigures from database"""
        # Set up the database first
        self.mock_builder.initialize_database()
        self.mock_builder.populate_sample_data()
        
        minifigures = self.matcher._get_all_minifigures()
        assert isinstance(minifigures, list)
        assert len(minifigures) > 0
    
    def test_get_minifigure_by_id(self):
        """Test getting minifigure by ID"""
        # First get all minifigures to get a valid ID
        minifigures = self.matcher._get_all_minifigures()
        if minifigures:
            first_id = minifigures[0]['id']
            result = self.matcher.get_minifigure_by_id(first_id)
            assert result is not None
            assert 'item_number' in result
            assert 'name' in result


class TestMockDatabaseBuilder:
    """Test the mock database builder"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_minifigure_database.db"
        self.builder = MockDatabaseBuilder(str(self.db_path))
    
    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialize_database(self):
        """Test database initialization"""
        self.builder.initialize_database()
        
        # Check if database file was created
        assert self.db_path.exists()
        
        # Check if tables were created
        count = self.builder.get_minifigure_count()
        assert count == 0  # Should be empty initially
    
    def test_populate_sample_data(self):
        """Test populating sample data"""
        self.builder.initialize_database()
        self.builder.populate_sample_data()
        
        count = self.builder.get_minifigure_count()
        assert count > 0
    
    def test_search_minifigures(self):
        """Test searching minifigures"""
        self.builder.initialize_database()
        self.builder.populate_sample_data()
        
        results = self.builder.search_minifigures("police")
        assert isinstance(results, list)
        
        # Should find police-related minifigures
        police_results = [r for r in results if "police" in r['name'].lower()]
        assert len(police_results) > 0
    
    def test_search_minifigures_no_results(self):
        """Test searching with no results"""
        self.builder.initialize_database()
        self.builder.populate_sample_data()
        
        results = self.builder.search_minifigures("nonexistent")
        assert isinstance(results, list)
        assert len(results) == 0


class TestProductionDatabaseBuilder:
    """Test the production database builder"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_production_database.db"
        self.builder = MockDatabaseBuilder(str(self.db_path))
    
    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_initialize_database(self):
        """Test production database initialization"""
        self.builder.initialize_database()
        assert self.db_path.exists()
    
    def test_get_comprehensive_minifigure_data(self):
        """Test getting comprehensive minifigure data"""
        from src.core.production_database_builder import ProductionDatabaseBuilder
        builder = ProductionDatabaseBuilder(str(self.db_path))
        
        data = builder._get_comprehensive_minifigure_data()
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
        from src.core.production_database_builder import ProductionDatabaseBuilder
        builder = ProductionDatabaseBuilder(str(self.db_path))
        
        base_minifig = {
            'item_number': 'test001',
            'name': 'Test Figure',
            'theme': 'Test',
            'year_released': 2020,
            'description': 'Test description',
            'rarity': 'common',
            'image_url': 'https://example.com/test.png'
        }
        
        variations = builder._create_minifigure_variations(base_minifig)
        assert isinstance(variations, list)
        assert len(variations) == 10  # Should create 10 variations
        
        # Check that variations have different item numbers
        item_numbers = [v['item_number'] for v in variations]
        assert len(set(item_numbers)) == 10  # All should be unique
    
    def test_generate_additional_minifigures(self):
        """Test generating additional minifigures"""
        from src.core.production_database_builder import ProductionDatabaseBuilder
        builder = ProductionDatabaseBuilder(str(self.db_path))
        
        additional = builder._generate_additional_minifigures(10)
        assert isinstance(additional, list)
        assert len(additional) == 10
        
        # Check that all have required fields
        for minifig in additional:
            assert 'item_number' in minifig
            assert 'name' in minifig
            assert 'theme' in minifig
            assert 'year_released' in minifig


class TestEnhancedMainCLI:
    """Test the enhanced main CLI functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        from src.core.database_identifier import DatabaseDrivenIdentifier
        self.cli = DatabaseDrivenIdentifier()
    
    def test_init(self):
        """Test CLI initialization"""
        assert self.cli.image_matcher is not None
        assert self.cli.ai_identifier is not None
        assert self.cli.db_builder is not None
    
    def test_get_database_stats(self):
        """Test getting database statistics"""
        stats = self.cli.get_database_stats()
        assert isinstance(stats, dict)
        assert 'total_minifigures' in stats
    
    def test_search_database(self):
        """Test database search"""
        results = self.cli.search_database("test", limit=5)
        assert isinstance(results, list)


@pytest.mark.integration
class TestDatabaseIdentifierIntegration:
    """Integration tests for database-driven identification"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = Path(self.temp_dir) / "test_integration_database.db"
        self.builder = MockDatabaseBuilder(str(self.db_path))
        self.builder.initialize_database()
        self.builder.populate_sample_data()
        
        # Create a test image file
        self.test_image_path = Path(self.temp_dir) / "test_image.jpg"
        self.test_image_path.write_bytes(b"fake image data")
    
    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    @pytest.mark.asyncio
    async def test_full_identification_workflow(self):
        """Test the complete identification workflow"""
        identifier = DatabaseDrivenIdentifier()
        
        # Mock the image matcher to return some matches
        with patch.object(identifier.image_matcher, 'find_matches') as mock_find:
            mock_find.return_value = [
                MatchResult(
                    minifigure_id=1,
                    item_number="cty001",
                    name="Police Officer",
                    theme="City",
                    confidence=0.8,
                    match_type="exact",
                    image_path=str(self.test_image_path),
                    year_released=2020
                )
            ]
            
            with patch.object(identifier.ai_identifier, 'identify_lego_items') as mock_ai:
                mock_ai.return_value = IdentificationResult(
                    confidence_score=0.7,
                    identified_items=[],
                    description="Test description",
                    condition_assessment="Good condition"
                )
                
                result = await identifier.identify_lego_items(str(self.test_image_path))
                
                assert result.confidence_score > 0.0
                assert result.description is not None
                assert result.condition_assessment is not None
