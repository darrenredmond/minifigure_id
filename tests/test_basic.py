import pytest
import tempfile
import os
from pathlib import Path

from src.models.schemas import ItemType, ItemCondition, LegoItem
from src.utils.image_processor import ImageProcessor
from config.settings import settings


def test_lego_item_creation():
    """Test basic LegoItem model creation"""
    item = LegoItem(
        item_number="sw0001",
        name="Luke Skywalker",
        item_type=ItemType.MINIFIGURE,
        condition=ItemCondition.USED_COMPLETE,
        year_released=1999,
        theme="Star Wars"
    )
    
    assert item.item_number == "sw0001"
    assert item.name == "Luke Skywalker"
    assert item.item_type == ItemType.MINIFIGURE
    assert item.condition == ItemCondition.USED_COMPLETE
    assert item.year_released == 1999
    assert item.theme == "Star Wars"


def test_image_processor_validation():
    """Test image validation"""
    processor = ImageProcessor()
    
    # Test file size validation
    large_content = b'x' * (settings.max_upload_size + 1)
    with pytest.raises(ValueError, match="File size exceeds maximum"):
        processor.validate_image(large_content, "test.jpg")
    
    # Test valid small content (this will fail on MIME type but shows size validation works)
    small_content = b'small content'
    with pytest.raises(ValueError, match="File type"):
        processor.validate_image(small_content, "test.jpg")


def test_settings_loading():
    """Test that settings can be loaded"""
    # This will use default values since no .env file exists yet
    assert settings.max_upload_size == 10485760  # 10MB
    assert settings.museum_threshold == 500.0
    assert settings.rare_threshold == 100.0
    assert "jpg" in settings.allowed_image_types


def test_directory_structure():
    """Test that required directories can be created"""
    with tempfile.TemporaryDirectory() as temp_dir:
        test_processor = ImageProcessor(upload_dir=temp_dir + "/uploads")
        
        # Directory should be created automatically
        assert Path(temp_dir + "/uploads").exists()


if __name__ == "__main__":
    pytest.main([__file__])