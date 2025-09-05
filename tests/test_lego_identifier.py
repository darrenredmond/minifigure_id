import pytest
import json
import tempfile
import base64
from pathlib import Path
from PIL import Image
from unittest.mock import Mock, AsyncMock, patch
import asyncio

from src.core.lego_identifier import LegoIdentifier
from src.models.schemas import IdentificationResult, LegoItem, ItemType, ItemCondition


class TestLegoIdentifier:
    @pytest.fixture
    def mock_anthropic_client(self):
        """Mock Anthropic client for testing"""
        mock_client = Mock()
        mock_message = Mock()
        mock_message.content = [Mock()]
        mock_client.messages = Mock()
        mock_client.messages.create = Mock(return_value=mock_message)  # Changed to sync Mock
        return mock_client
    
    @pytest.fixture
    def lego_identifier(self, mock_anthropic_client):
        """Create LegoIdentifier with mocked client"""
        identifier = LegoIdentifier()
        identifier.client = mock_anthropic_client
        return identifier
    
    @pytest.fixture
    def sample_image_path(self):
        """Create a temporary test image file"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            # Create a small test image
            img = Image.new('RGB', (100, 100), color='red')
            img.save(temp_file.name, 'JPEG')
            yield temp_file.name
        
        # Cleanup
        Path(temp_file.name).unlink(missing_ok=True)
    
    def test_encode_image(self, lego_identifier, sample_image_path):
        """Test image encoding to base64"""
        encoded = lego_identifier._encode_image(sample_image_path)
        
        assert isinstance(encoded, str)
        assert len(encoded) > 0
        
        # Verify it's valid base64
        try:
            decoded = base64.b64decode(encoded)
            assert len(decoded) > 0
        except Exception:
            pytest.fail("Encoded string is not valid base64")
    
    def test_get_identification_prompt(self, lego_identifier):
        """Test that identification prompt is generated"""
        prompt = lego_identifier._get_identification_prompt()
        
        assert isinstance(prompt, str)
        assert len(prompt) > 0
        assert "LEGO" in prompt
        assert "confidence_score" in prompt
        assert "identified_items" in prompt
    
    @pytest.mark.asyncio
    async def test_identify_lego_items_success(self, lego_identifier, sample_image_path, mock_anthropic_client):
        """Test successful LEGO identification with valid JSON response"""
        # Mock response with valid JSON
        mock_json_response = {
            "confidence_score": 0.85,
            "identified_items": [
                {
                    "item_number": "sw0001a",
                    "name": "Luke Skywalker (Tatooine)",
                    "item_type": "minifigure",
                    "condition": "used_complete",
                    "year_released": 1999,
                    "theme": "Star Wars",
                    "category": "Episode IV",
                    "pieces": None
                }
            ],
            "description": "Single LEGO Star Wars minifigure of Luke Skywalker from 1999",
            "condition_assessment": "Figure appears to be in good used condition"
        }
        
        mock_response_text = f"Here is my analysis:\n\n{json.dumps(mock_json_response)}\n\nThat completes my assessment."
        mock_anthropic_client.messages.create.return_value.content[0].text = mock_response_text
        
        # Test identification
        result = await lego_identifier.identify_lego_items(sample_image_path)
        
        # Verify result
        assert isinstance(result, IdentificationResult)
        assert result.confidence_score == 0.85
        assert len(result.identified_items) == 1
        
        item = result.identified_items[0]
        assert item.item_number == "sw0001a"
        assert item.name == "Luke Skywalker (Tatooine)"
        assert item.item_type == ItemType.MINIFIGURE
        assert item.condition == ItemCondition.USED_COMPLETE
        assert item.year_released == 1999
        assert item.theme == "Star Wars"
        
        assert result.description == "Single LEGO Star Wars minifigure of Luke Skywalker from 1999"
        assert result.condition_assessment == "Figure appears to be in good used condition"
    
    @pytest.mark.asyncio
    async def test_identify_lego_items_multiple_items(self, lego_identifier, sample_image_path, mock_anthropic_client):
        """Test identification with multiple LEGO items"""
        mock_json_response = {
            "confidence_score": 0.75,
            "identified_items": [
                {
                    "item_number": "sw0001a",
                    "name": "Luke Skywalker",
                    "item_type": "minifigure",
                    "condition": "used_complete",
                    "year_released": 1999,
                    "theme": "Star Wars"
                },
                {
                    "item_number": "sw0002",
                    "name": "Princess Leia",
                    "item_type": "minifigure", 
                    "condition": "new",
                    "year_released": 1999,
                    "theme": "Star Wars"
                }
            ],
            "description": "Two Star Wars minifigures from the original 1999 set",
            "condition_assessment": "Mixed condition - Luke shows wear, Leia appears new"
        }
        
        mock_response_text = json.dumps(mock_json_response)
        mock_anthropic_client.messages.create.return_value.content[0].text = mock_response_text
        
        result = await lego_identifier.identify_lego_items(sample_image_path)
        
        assert len(result.identified_items) == 2
        assert result.identified_items[0].name == "Luke Skywalker"
        assert result.identified_items[1].name == "Princess Leia"
        assert result.identified_items[1].condition == ItemCondition.NEW
    
    @pytest.mark.asyncio
    async def test_identify_lego_items_invalid_json(self, lego_identifier, sample_image_path, mock_anthropic_client):
        """Test handling of invalid JSON response"""
        mock_response_text = "This is not valid JSON response about LEGO items"
        mock_anthropic_client.messages.create.return_value.content[0].text = mock_response_text
        
        result = await lego_identifier.identify_lego_items(sample_image_path)
        
        # Should return fallback result
        assert isinstance(result, IdentificationResult)
        assert result.confidence_score == 0.3
        assert len(result.identified_items) == 0
        assert result.description == mock_response_text[:500]
        assert result.condition_assessment == "Could not parse detailed assessment"
    
    @pytest.mark.asyncio
    async def test_identify_lego_items_partial_json(self, lego_identifier, sample_image_path, mock_anthropic_client):
        """Test handling of partial/malformed JSON"""
        mock_response_text = 'Looking at this image, I can see {"confidence_score": 0.6, "identified_items": [{"name": "Unknown LEGO piece"'
        mock_anthropic_client.messages.create.return_value.content[0].text = mock_response_text
        
        result = await lego_identifier.identify_lego_items(sample_image_path)
        
        # Should fall back to description
        assert result.confidence_score == 0.3
        assert len(result.identified_items) == 0
    
    @pytest.mark.asyncio
    async def test_identify_lego_items_api_error(self, lego_identifier, sample_image_path, mock_anthropic_client):
        """Test handling of API errors"""
        mock_anthropic_client.messages.create.side_effect = Exception("API Error")
        
        result = await lego_identifier.identify_lego_items(sample_image_path)
        
        # Should return error result
        assert isinstance(result, IdentificationResult)
        assert result.confidence_score == 0.0
        assert len(result.identified_items) == 0
        assert "Error during identification" in result.description
        assert result.condition_assessment == "Could not assess condition due to error"
    
    @pytest.mark.asyncio
    async def test_api_call_parameters(self, lego_identifier, sample_image_path, mock_anthropic_client):
        """Test that API is called with correct parameters"""
        mock_json_response = {
            "confidence_score": 0.5,
            "identified_items": [],
            "description": "No items found",
            "condition_assessment": "N/A"
        }
        
        mock_response_text = json.dumps(mock_json_response)
        mock_anthropic_client.messages.create.return_value.content[0].text = mock_response_text
        
        await lego_identifier.identify_lego_items(sample_image_path)
        
        # Verify API call parameters
        call_args = mock_anthropic_client.messages.create.call_args
        assert call_args is not None
        
        # Check keyword arguments  
        kwargs = call_args.kwargs
        assert kwargs['model'] == "claude-3-haiku-20240307"
        assert kwargs['max_tokens'] == 2000
        assert 'messages' in kwargs
        assert 'system' in kwargs
        
        # Check message structure
        messages = kwargs['messages']
        assert len(messages) == 1
        assert messages[0]['role'] == 'user'
        assert 'content' in messages[0]
        
        content = messages[0]['content']
        assert len(content) == 2  # Image and text
        assert content[0]['type'] == 'image'
        assert content[1]['type'] == 'text'
        
        # Check image content
        image_content = content[0]
        assert image_content['source']['type'] == 'base64'
        assert image_content['source']['media_type'] == 'image/jpeg'
        assert 'data' in image_content['source']
    
    def test_extract_keywords(self, lego_identifier):
        """Test keyword extraction from descriptions"""
        description = "This is a rare limited edition LEGO set with a prototype piece"
        keywords = lego_identifier._extract_keywords(description)
        
        assert "rare" in keywords
        assert "limited" in keywords
        assert "prototype" in keywords
    
    def test_extract_keywords_no_matches(self, lego_identifier):
        """Test keyword extraction with no special terms"""
        description = "This is a regular LEGO set in good condition"
        keywords = lego_identifier._extract_keywords(description)
        
        assert len(keywords) == 0
    
    def test_nonexistent_image_file(self, lego_identifier):
        """Test handling of nonexistent image file"""
        with pytest.raises(FileNotFoundError):
            lego_identifier._encode_image("/nonexistent/file.jpg")


@pytest.mark.integration 
class TestLegoIdentifierIntegration:
    """Integration tests that may require actual API calls"""
    
    @pytest.mark.skipif(
        False,  # Now we have a real API key!
        reason="Requires valid Anthropic API key"
    )
    @pytest.mark.asyncio
    async def test_real_api_call(self):
        """Test with real API call (only run manually with valid API key)"""
        identifier = LegoIdentifier()
        
        # Create a simple test image
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            img = Image.new('RGB', (200, 200), color='blue')
            img.save(temp_file.name, 'JPEG')
            
            try:
                result = await identifier.identify_lego_items(temp_file.name)
                
                # Basic validation - should not crash
                assert isinstance(result, IdentificationResult)
                assert 0.0 <= result.confidence_score <= 1.0
                assert isinstance(result.identified_items, list)
                assert isinstance(result.description, str)
                assert isinstance(result.condition_assessment, str)
                
            finally:
                Path(temp_file.name).unlink(missing_ok=True)


class TestLegoIdentifierErrorHandling:
    """Test various error conditions and edge cases"""
    
    @pytest.fixture
    def lego_identifier(self):
        return LegoIdentifier()
    
    @pytest.mark.asyncio
    async def test_corrupted_image_file(self, lego_identifier):
        """Test handling of corrupted image file"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            # Write invalid image data
            temp_file.write(b"This is not a valid image file")
            temp_file.flush()
            
            try:
                # Should not crash - might get encoding error but should handle gracefully
                result = await lego_identifier.identify_lego_items(temp_file.name)
                assert isinstance(result, IdentificationResult)
                
            except Exception as e:
                # If it does raise an exception, it should be a specific one
                assert not isinstance(e, AttributeError)  # Avoid None attribute errors
                
            finally:
                Path(temp_file.name).unlink(missing_ok=True)
    
    @pytest.mark.asyncio 
    async def test_empty_image_file(self, lego_identifier):
        """Test handling of empty image file"""
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            # File is empty
            temp_file.flush()
            
            try:
                result = await lego_identifier.identify_lego_items(temp_file.name)
                assert isinstance(result, IdentificationResult)
                
            except Exception as e:
                assert not isinstance(e, AttributeError)
                
            finally:
                Path(temp_file.name).unlink(missing_ok=True)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])