import pytest
import tempfile
import shutil
from pathlib import Path
from PIL import Image
import io
import magic

from src.utils.image_processor import ImageProcessor
from src.models.schemas import ImageUpload


class TestImageProcessor:
    @pytest.fixture
    def temp_upload_dir(self):
        """Create temporary upload directory for testing"""
        temp_dir = tempfile.mkdtemp()
        yield temp_dir
        shutil.rmtree(temp_dir)
    
    @pytest.fixture
    def image_processor(self, temp_upload_dir):
        """Create ImageProcessor with temporary directory"""
        return ImageProcessor(upload_dir=temp_upload_dir)
    
    @pytest.fixture
    def sample_image_bytes(self):
        """Create a small test image as bytes"""
        # Create a small RGB image
        img = Image.new('RGB', (100, 100), color='red')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        return img_bytes.getvalue()
    
    @pytest.fixture
    def large_image_bytes(self):
        """Create a large test image that exceeds size limits"""
        # Create a very large image that definitely exceeds 10MB limit
        img = Image.new('RGB', (8000, 8000), color='blue')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG', quality=100)
        
        # If still not large enough, pad it
        data = img_bytes.getvalue()
        if len(data) < 10485760:  # 10MB
            padding = b'0' * (10485760 - len(data) + 1000)  # Exceed by 1000 bytes
            data = data + padding
        
        return data
    
    def test_init_creates_upload_directory(self, temp_upload_dir):
        """Test that ImageProcessor creates upload directory"""
        upload_path = Path(temp_upload_dir) / "uploads"
        processor = ImageProcessor(upload_dir=str(upload_path))
        
        assert upload_path.exists()
        assert upload_path.is_dir()
    
    def test_validate_image_success(self, image_processor, sample_image_bytes):
        """Test successful image validation"""
        result = image_processor.validate_image(sample_image_bytes, "test.jpg")
        assert result is True
    
    def test_validate_image_file_too_large(self, image_processor, large_image_bytes):
        """Test validation fails for oversized files"""
        with pytest.raises(ValueError, match="File size exceeds maximum"):
            image_processor.validate_image(large_image_bytes, "large.jpg")
    
    def test_validate_image_invalid_type(self, image_processor):
        """Test validation fails for non-image files"""
        text_content = b"This is not an image file"
        
        with pytest.raises(ValueError, match="File type .* is not supported"):
            image_processor.validate_image(text_content, "test.txt")
    
    def test_validate_image_invalid_extension(self, image_processor, sample_image_bytes):
        """Test validation fails for invalid file extensions"""
        with pytest.raises(ValueError, match="File extension 'exe' is not allowed"):
            image_processor.validate_image(sample_image_bytes, "test.exe")
    
    def test_save_image_success(self, image_processor, sample_image_bytes):
        """Test successful image saving"""
        file_path, image_upload = image_processor.save_image(
            sample_image_bytes, "test_image.jpg"
        )
        
        # Check file was saved
        assert Path(file_path).exists()
        assert Path(file_path).is_file()
        
        # Check metadata
        assert isinstance(image_upload, ImageUpload)
        assert image_upload.filename.startswith("test-image_")
        assert image_upload.filename.endswith(".jpg")
        assert image_upload.content_type == "image/jpeg"
        assert image_upload.size == len(sample_image_bytes)
    
    def test_save_image_generates_unique_filename(self, image_processor, sample_image_bytes):
        """Test that saving same filename twice generates unique names"""
        file_path1, upload1 = image_processor.save_image(
            sample_image_bytes, "duplicate.jpg"
        )
        file_path2, upload2 = image_processor.save_image(
            sample_image_bytes, "duplicate.jpg"
        )
        
        # Both files should exist and have different names
        assert Path(file_path1).exists()
        assert Path(file_path2).exists()
        assert upload1.filename != upload2.filename
        assert file_path1 != file_path2
    
    def test_optimize_image_for_ai(self, image_processor, temp_upload_dir):
        """Test image optimization for AI processing"""
        # Create a large image to test resizing
        large_img = Image.new('RGB', (2000, 2000), color='green')
        large_img_path = Path(temp_upload_dir) / "large_image.jpg"
        large_img.save(large_img_path, 'JPEG')
        
        # Optimize the image
        optimized_path = image_processor.optimize_image_for_ai(str(large_img_path))
        
        # Check optimized file exists
        assert Path(optimized_path).exists()
        
        # Check that image was resized
        with Image.open(optimized_path) as optimized_img:
            assert optimized_img.size[0] <= 1024
            assert optimized_img.size[1] <= 1024
            assert optimized_img.format == 'JPEG'
    
    def test_optimize_image_handles_rgba(self, image_processor, temp_upload_dir):
        """Test that RGBA images are converted to RGB during optimization"""
        # Create RGBA image
        rgba_img = Image.new('RGBA', (500, 500), color=(255, 0, 0, 128))
        rgba_img_path = Path(temp_upload_dir) / "rgba_image.png"
        rgba_img.save(rgba_img_path, 'PNG')
        
        # Optimize the image
        optimized_path = image_processor.optimize_image_for_ai(str(rgba_img_path))
        
        # Check that result is RGB JPEG
        with Image.open(optimized_path) as optimized_img:
            assert optimized_img.mode == 'RGB'
            assert optimized_img.format == 'JPEG'
    
    def test_get_image_info(self, image_processor, temp_upload_dir):
        """Test extracting image information"""
        # Create test image
        test_img = Image.new('RGB', (300, 200), color='purple')
        test_img_path = Path(temp_upload_dir) / "info_test.jpg"
        test_img.save(test_img_path, 'JPEG')
        
        # Get image info
        info = image_processor.get_image_info(str(test_img_path))
        
        assert info['format'] == 'JPEG'
        assert info['mode'] == 'RGB'
        assert info['size'] == (300, 200)
        assert info['width'] == 300
        assert info['height'] == 200
    
    def test_cleanup_old_files(self, image_processor, temp_upload_dir):
        """Test cleanup of old files"""
        import time
        import os
        
        # Create some test files
        old_file = Path(temp_upload_dir) / "old_file.jpg"
        new_file = Path(temp_upload_dir) / "new_file.jpg"
        
        old_file.touch()
        new_file.touch()
        
        # Make old file appear old by changing its modification time
        old_time = time.time() - (40 * 24 * 60 * 60)  # 40 days ago
        os.utime(old_file, (old_time, old_time))
        
        # Cleanup files older than 30 days
        deleted_count = image_processor.cleanup_old_files(days_old=30)
        
        # Old file should be deleted, new file should remain
        assert not old_file.exists()
        assert new_file.exists()
        assert deleted_count == 1


class TestImageProcessorEdgeCases:
    """Test edge cases and error conditions"""
    
    @pytest.fixture
    def image_processor(self):
        return ImageProcessor()
    
    def test_save_image_with_no_extension(self, image_processor):
        """Test saving image with no file extension"""
        # Create small test image
        img = Image.new('RGB', (50, 50), color='orange')
        img_bytes = io.BytesIO()
        img.save(img_bytes, format='JPEG')
        
        file_path, image_upload = image_processor.save_image(
            img_bytes.getvalue(), "no_extension"
        )
        
        # Should default to .jpg extension
        assert image_upload.filename.endswith('.jpg')
        assert Path(file_path).exists()
    
    def test_optimize_nonexistent_file(self, image_processor):
        """Test optimizing a file that doesn't exist"""
        with pytest.raises(FileNotFoundError):
            image_processor.optimize_image_for_ai("/nonexistent/file.jpg")
    
    def test_get_info_nonexistent_file(self, image_processor):
        """Test getting info for nonexistent file"""
        with pytest.raises(FileNotFoundError):
            image_processor.get_image_info("/nonexistent/file.jpg")


@pytest.mark.integration
class TestImageProcessorIntegration:
    """Integration tests that require more setup"""
    
    def test_full_upload_pipeline(self):
        """Test the complete upload and processing pipeline"""
        with tempfile.TemporaryDirectory() as temp_dir:
            processor = ImageProcessor(upload_dir=temp_dir)
            
            # Create a realistic test image
            img = Image.new('RGB', (1500, 1200), color='blue')
            # Add some complexity to the image
            for i in range(0, 1500, 100):
                for j in range(0, 1200, 100):
                    color = (i % 255, j % 255, (i+j) % 255)
                    for x in range(i, min(i+50, 1500)):
                        for y in range(j, min(j+50, 1200)):
                            img.putpixel((x, y), color)
            
            img_bytes = io.BytesIO()
            img.save(img_bytes, format='JPEG', quality=90)
            img_data = img_bytes.getvalue()
            
            # Test full pipeline
            file_path, upload_info = processor.save_image(img_data, "complex_image.jpg")
            optimized_path = processor.optimize_image_for_ai(file_path)
            image_info = processor.get_image_info(optimized_path)
            
            # Verify results
            assert Path(file_path).exists()
            assert Path(optimized_path).exists()
            assert upload_info.size == len(img_data)
            assert image_info['width'] <= 1024
            assert image_info['height'] <= 1024
            assert image_info['format'] == 'JPEG'


if __name__ == "__main__":
    pytest.main([__file__, "-v"])