"""
Tests for Enhanced Main CLI Functionality
"""

import pytest
import asyncio
from unittest.mock import Mock, patch, AsyncMock
from pathlib import Path
import tempfile
import shutil
import sys
from io import StringIO

# Add src to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent / "src"))

from src.core.enhanced_main import EnhancedLegoValuationCLI
from src.models.schemas import ValuationReport, IdentificationResult, ValuationResult, LegoItem, ItemType, ItemCondition


class TestEnhancedLegoValuationCLI:
    """Test the enhanced LEGO valuation CLI"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.cli = EnhancedLegoValuationCLI()
        self.temp_dir = tempfile.mkdtemp()
        self.test_image_path = Path(self.temp_dir) / "test_image.jpg"
        self.test_image_path.write_bytes(b"fake image data")
    
    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_init(self):
        """Test CLI initialization"""
        assert self.cli.db_manager is not None
        assert self.cli.repository is not None
        assert self.cli.image_processor is not None
        assert self.cli.lego_identifier is not None
        assert self.cli.enhanced_identifier is not None
        assert self.cli.valuation_engine is not None
        assert self.cli.report_generator is not None
    
    def test_initialize_system(self):
        """Test system initialization"""
        with patch.object(self.cli.db_manager, 'initialize_database'):
            with patch.object(Path, 'mkdir'):
                with patch.object(self.cli.enhanced_identifier, 'get_database_stats', return_value={'total_minifigures': 100}):
                    # This should not raise an exception
                    self.cli.initialize_system()
    
    @pytest.mark.asyncio
    async def test_process_image_enhanced_mode(self):
        """Test processing image in enhanced mode"""
        with patch.object(self.cli.image_processor, 'save_image', return_value=("test_path", Mock())):
            with patch.object(self.cli.image_processor, 'optimize_image_for_ai', return_value="optimized_path"):
                with patch.object(self.cli.enhanced_identifier, 'identify_lego_items') as mock_identify:
                    with patch.object(self.cli.valuation_engine, 'evaluate_item') as mock_evaluate:
                        with patch.object(self.cli.repository, 'save_valuation', return_value=1):
                            with patch.object(self.cli.report_generator, 'generate_pdf', return_value="pdf_path"):
                                with patch.object(self.cli.report_generator, 'generate_html', return_value="html_path"):
                                    # Mock the identification result
                                    mock_identify.return_value = IdentificationResult(
                                        confidence_score=0.8,
                                        identified_items=[
                                            LegoItem(
                                                item_number="test001",
                                                name="Test Figure",
                                                item_type=ItemType.MINIFIGURE,
                                                condition=ItemCondition.USED_COMPLETE,
                                                year_released=2020,
                                                theme="Test",
                                                category="Test",
                                                pieces=None
                                            )
                                        ],
                                        description="Test description",
                                        condition_assessment="Good condition"
                                    )
                                    
                                    # Mock the valuation result
                                    mock_evaluate.return_value = ValuationResult(
                                        estimated_value=100.0,
                                        estimated_value_eur=85.0,
                                        confidence_score=0.8,
                                        recommendation="collection",
                                        reasoning="Test reasoning",
                                        suggested_platforms=["bricklink"],
                                        market_data=None,
                                        individual_valuations=[],
                                        exchange_rate_usd_eur=0.85
                                    )
                                    
                                    await self.cli.process_image(str(self.test_image_path), "Test notes", use_enhanced=True)
                                    
                                    # Verify enhanced identifier was called
                                    mock_identify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_image_standard_mode(self):
        """Test processing image in standard mode"""
        with patch.object(self.cli.image_processor, 'save_image', return_value=("test_path", Mock())):
            with patch.object(self.cli.image_processor, 'optimize_image_for_ai', return_value="optimized_path"):
                with patch.object(self.cli.lego_identifier, 'identify_lego_items') as mock_identify:
                    with patch.object(self.cli.valuation_engine, 'evaluate_item') as mock_evaluate:
                        with patch.object(self.cli.repository, 'save_valuation', return_value=1):
                            with patch.object(self.cli.report_generator, 'generate_pdf', return_value="pdf_path"):
                                with patch.object(self.cli.report_generator, 'generate_html', return_value="html_path"):
                                    # Mock the identification result
                                    mock_identify.return_value = IdentificationResult(
                                        confidence_score=0.7,
                                        identified_items=[],
                                        description="Standard AI description",
                                        condition_assessment="Standard condition"
                                    )
                                    
                                    # Mock the valuation result
                                    mock_evaluate.return_value = ValuationResult(
                                        estimated_value=50.0,
                                        estimated_value_eur=42.5,
                                        confidence_score=0.7,
                                        recommendation="collection",
                                        reasoning="Standard reasoning",
                                        suggested_platforms=["bricklink"],
                                        market_data=None,
                                        individual_valuations=[],
                                        exchange_rate_usd_eur=0.85
                                    )
                                    
                                    await self.cli.process_image(str(self.test_image_path), "Test notes", use_enhanced=False)
                                    
                                    # Verify standard identifier was called
                                    mock_identify.assert_called_once()
    
    @pytest.mark.asyncio
    async def test_process_image_error_handling(self):
        """Test error handling in image processing"""
        with patch.object(self.cli.image_processor, 'save_image', side_effect=Exception("Image processing error")):
            # This should not raise an exception, but should handle the error gracefully
            await self.cli.process_image(str(self.test_image_path), "Test notes")
    
    def test_list_valuations(self):
        """Test listing valuations"""
        with patch.object(self.cli.repository, 'get_recent_valuations', return_value=[]):
            # This should not raise an exception
            self.cli.list_valuations(limit=10)
    
    def test_show_inventory_summary(self):
        """Test showing inventory summary"""
        with patch.object(self.cli.repository, 'get_inventory_summary', return_value={
            'total_items': 0,
            'total_value': 0.0,
            'average_value': 0.0,
            'highest_value': 0.0,
            'museum_count': 0,
            'resale_count': 0,
            'collection_count': 0
        }):
            # This should not raise an exception
            self.cli.show_inventory_summary()
    
    def test_search_database(self):
        """Test database search"""
        with patch.object(self.cli.enhanced_identifier, 'search_database', return_value=[]):
            # This should not raise an exception
            self.cli.search_database("test query", limit=10)
    
    def test_show_database_stats(self):
        """Test showing database statistics"""
        with patch.object(self.cli.enhanced_identifier, 'get_database_stats', return_value={
            'total_minifigures': 100,
            'database_path': '/test/path',
            'images_directory': '/test/images'
        }):
            # This should not raise an exception
            self.cli.show_database_stats()
    
    def test_setup_database(self):
        """Test database setup"""
        with patch('src.core.enhanced_main.ProductionDatabaseBuilder') as mock_builder_class:
            mock_builder = Mock()
            mock_builder.build_production_database = AsyncMock(return_value=1000)
            mock_builder_class.return_value = mock_builder
            
            # This should not raise an exception
            self.cli.setup_database(count=1000)
            
            # Verify the builder was called
            mock_builder_class.assert_called_once()
            mock_builder.build_production_database.assert_called_once_with(1000)


class TestEnhancedMainCLIArguments:
    """Test the enhanced main CLI argument parsing"""
    
    def test_process_command_enhanced_mode(self):
        """Test process command with enhanced mode (default)"""
        from src.core.enhanced_main import main
        
        # Mock the CLI class
        with patch('src.core.enhanced_main.EnhancedLegoValuationCLI') as mock_cli_class:
            mock_cli = Mock()
            mock_cli_class.return_value = mock_cli
            
            # Test with enhanced mode (default)
            sys.argv = ['main.py', 'process', 'test_image.jpg', '--notes', 'Test notes']
            
            with patch('asyncio.run'):
                main()
            
            # Verify process_image was called with enhanced=True (default)
            mock_cli.process_image.assert_called_once()
            args, kwargs = mock_cli.process_image.call_args
            assert kwargs.get('use_enhanced', True) == True
    
    def test_process_command_standard_mode(self):
        """Test process command with standard mode"""
        from src.core.enhanced_main import main
        
        # Mock the CLI class
        with patch('src.core.enhanced_main.EnhancedLegoValuationCLI') as mock_cli_class:
            mock_cli = Mock()
            mock_cli_class.return_value = mock_cli
            
            # Test with standard mode
            sys.argv = ['main.py', 'process', 'test_image.jpg', '--standard']
            
            with patch('asyncio.run'):
                main()
            
            # Verify process_image was called with enhanced=False
            mock_cli.process_image.assert_called_once()
            args, kwargs = mock_cli.process_image.call_args
            assert kwargs.get('use_enhanced', True) == False
    
    def test_search_command(self):
        """Test search command"""
        from src.core.enhanced_main import main
        
        # Mock the CLI class
        with patch('src.core.enhanced_main.EnhancedLegoValuationCLI') as mock_cli_class:
            mock_cli = Mock()
            mock_cli_class.return_value = mock_cli
            
            sys.argv = ['main.py', 'search', 'spider', '--limit', '5']
            main()
            
            mock_cli.search_database.assert_called_once_with('spider', 5)
    
    def test_stats_command(self):
        """Test stats command"""
        from src.core.enhanced_main import main
        
        # Mock the CLI class
        with patch('src.core.enhanced_main.EnhancedLegoValuationCLI') as mock_cli_class:
            mock_cli = Mock()
            mock_cli_class.return_value = mock_cli
            
            sys.argv = ['main.py', 'stats']
            main()
            
            mock_cli.show_database_stats.assert_called_once()
    
    def test_setup_command(self):
        """Test setup command"""
        from src.core.enhanced_main import main
        
        # Mock the CLI class
        with patch('src.core.enhanced_main.EnhancedLegoValuationCLI') as mock_cli_class:
            mock_cli = Mock()
            mock_cli_class.return_value = mock_cli
            
            sys.argv = ['main.py', 'setup', '--count', '500']
            main()
            
            mock_cli.setup_database.assert_called_once_with(500)
    
    def test_help_command(self):
        """Test help command"""
        from src.core.enhanced_main import main
        
        # Capture stdout
        old_stdout = sys.stdout
        sys.stdout = captured_output = StringIO()
        
        try:
            sys.argv = ['main.py', '--help']
            main()
            
            output = captured_output.getvalue()
            assert 'Enhanced LEGO Valuation System' in output
            assert 'process' in output
            assert 'search' in output
            assert 'stats' in output
        finally:
            sys.stdout = old_stdout


class TestEnhancedMainIntegration:
    """Integration tests for enhanced main functionality"""
    
    def setup_method(self):
        """Set up test fixtures"""
        self.temp_dir = tempfile.mkdtemp()
        self.test_image_path = Path(self.temp_dir) / "test_image.jpg"
        self.test_image_path.write_bytes(b"fake image data")
    
    def teardown_method(self):
        """Clean up test fixtures"""
        shutil.rmtree(self.temp_dir, ignore_errors=True)
    
    def test_cli_initialization_integration(self):
        """Test CLI initialization with real components"""
        cli = EnhancedLegoValuationCLI()
        
        # All components should be properly initialized
        assert cli.db_manager is not None
        assert cli.repository is not None
        assert cli.image_processor is not None
        assert cli.lego_identifier is not None
        assert cli.enhanced_identifier is not None
        assert cli.valuation_engine is not None
        assert cli.report_generator is not None
    
    def test_database_stats_integration(self):
        """Test database statistics with real database"""
        cli = EnhancedLegoValuationCLI()
        stats = cli.show_database_stats()
        
        # Should not raise an exception and should return some stats
        assert isinstance(stats, type(None))  # show_database_stats prints, doesn't return
    
    def test_search_database_integration(self):
        """Test database search with real database"""
        cli = EnhancedLegoValuationCLI()
        results = cli.search_database("test", limit=5)
        
        # Should return a list (may be empty)
        assert isinstance(results, list)
