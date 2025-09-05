"""
Integration tests for the complete LEGO valuation system.
These tests require real API keys and network access.
"""

import pytest
import asyncio
import tempfile
import base64
from pathlib import Path
from PIL import Image, ImageDraw, ImageFont
import io

from src.core.lego_identifier import LegoIdentifier
from src.core.valuation_engine import ValuationEngine
from src.external.bricklink_client import BrickLinkClient
from src.utils.image_processor import ImageProcessor
from src.models.schemas import ItemType, ItemCondition, MarketData
from config.settings import settings


def create_lego_test_image():
    """Create a test image that looks somewhat like LEGO bricks"""
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw some brick-like rectangles with studs
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
    
    for i in range(4):
        y_offset = i * 150
        color = colors[i]
        
        # Draw brick body
        draw.rectangle([50, 50 + y_offset, 350, 150 + y_offset], fill=color, outline='black', width=2)
        
        # Draw studs (circles on top of brick)
        for j in range(4):
            x = 80 + j * 70
            y = 70 + y_offset
            draw.ellipse([x-15, y-15, x+15, y+15], fill=color, outline='black', width=1)
            # Add "LEGO" text inside one stud
            if j == 1:
                try:
                    draw.text((x-10, y-5), "LEGO", fill='white')
                except:
                    pass  # Font might not be available
    
    # Add text that says it's a LEGO test
    draw.text((400, 50), "LEGO BRICKS TEST IMAGE", fill='black')
    draw.text((400, 100), "Classic 2x4 Bricks", fill='black')
    draw.text((400, 150), "Red, Green, Blue, Yellow", fill='black')
    
    return img


@pytest.mark.integration
class TestRealAPIIntegration:
    """Tests that use real API keys"""
    
    @pytest.fixture
    def has_anthropic_key(self):
        """Check if Anthropic API key is configured"""
        return settings.anthropic_api_key and not settings.anthropic_api_key.startswith("test_")
    
    @pytest.fixture
    def has_bricklink_keys(self):
        """Check if BrickLink API keys are configured"""
        return all([
            settings.bricklink_consumer_key,
            settings.bricklink_consumer_secret,
            settings.bricklink_token_value,
            settings.bricklink_token_secret
        ])
    
    @pytest.mark.asyncio
    async def test_claude_vision_with_lego_image(self, has_anthropic_key):
        """Test Claude Vision API with a LEGO-like test image"""
        if not has_anthropic_key:
            pytest.skip("No valid Anthropic API key")
        
        identifier = LegoIdentifier()
        
        # Create and save test image
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            img = create_lego_test_image()
            img.save(temp_file.name, 'JPEG')
            
            try:
                # Test identification
                result = await identifier.identify_lego_items(temp_file.name)
                
                # Assertions
                assert result is not None
                assert hasattr(result, 'confidence_score')
                assert 0.0 <= result.confidence_score <= 1.0
                assert hasattr(result, 'description')
                assert len(result.description) > 0
                assert hasattr(result, 'identified_items')
                assert isinstance(result.identified_items, list)
                
                # Since this is a synthetic image, confidence might be low
                print(f"Claude Vision Result:")
                print(f"  Confidence: {result.confidence_score}")
                print(f"  Description: {result.description[:200]}...")
                print(f"  Items found: {len(result.identified_items)}")
                
                for item in result.identified_items:
                    print(f"    - {item.name}: {item.item_type.value}")
                
            finally:
                Path(temp_file.name).unlink(missing_ok=True)
    
    def test_bricklink_search_real(self, has_bricklink_keys):
        """Test BrickLink API search functionality"""
        if not has_bricklink_keys:
            pytest.skip("No valid BrickLink API keys")
        
        client = BrickLinkClient()
        
        # Search for a well-known LEGO item
        results = client.search_items("MINIFIG", "Luke Skywalker")
        
        # Should return a list (empty list if IP not whitelisted)
        assert isinstance(results, list)
        
        if len(results) > 0:
            print(f"Found {len(results)} Luke Skywalker minifigures")
            for result in results[:3]:  # Show first 3
                print(f"  - {result.get('name', 'Unknown')}")
        else:
            print("No search results - likely IP not whitelisted for BrickLink API")
    
    def test_bricklink_price_guide_real(self, has_bricklink_keys):
        """Test BrickLink price guide API"""
        if not has_bricklink_keys:
            pytest.skip("No valid BrickLink API keys")
        
        client = BrickLinkClient()
        
        # Get price guide for a specific item (Luke Skywalker from 1999)
        market_data = client.get_price_guide("MINIFIG", "sw0001a", "U")
        
        # The API call should not crash, but may return None due to IP restrictions
        assert market_data is None or isinstance(market_data, MarketData)
        
        if market_data:
            print(f"Market Data for sw0001a:")
            print(f"  Current Price: ${market_data.current_price or 'N/A'}")
            print(f"  Times Sold: {market_data.times_sold or 'N/A'}")
            print(f"  Availability: {market_data.availability or 'N/A'}")
        else:
            print("No market data returned - likely IP not whitelisted for BrickLink API")
    
    @pytest.mark.asyncio
    async def test_full_valuation_pipeline(self, has_anthropic_key, has_bricklink_keys):
        """Test the complete valuation pipeline from image to valuation"""
        if not has_anthropic_key:
            pytest.skip("No valid Anthropic API key")
        
        # Create test image
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            img = create_lego_test_image()
            img.save(temp_file.name, 'JPEG')
            
            try:
                # Step 1: Image Processing
                processor = ImageProcessor()
                optimized_path = processor.optimize_image_for_ai(temp_file.name)
                assert Path(optimized_path).exists()
                
                # Step 2: Identification
                identifier = LegoIdentifier()
                identification = await identifier.identify_lego_items(optimized_path)
                assert identification is not None
                
                print(f"\n=== Identification Results ===")
                print(f"Confidence: {identification.confidence_score:.2%}")
                print(f"Description: {identification.description[:200]}...")
                print(f"Items identified: {len(identification.identified_items)}")
                
                # Step 3: Valuation (even if no items identified)
                valuation_engine = ValuationEngine()
                valuation = await valuation_engine.evaluate_item(identification)
                assert valuation is not None
                
                print(f"\n=== Valuation Results ===")
                print(f"Estimated Value: ${valuation.estimated_value:.2f}")
                print(f"Confidence: {valuation.confidence_score:.2%}")
                print(f"Recommendation: {valuation.recommendation.value}")
                print(f"Reasoning: {valuation.reasoning}")
                print(f"Suggested Platforms: {[p.value for p in valuation.suggested_platforms]}")
                
                # Basic assertions
                assert valuation.estimated_value >= 0
                assert 0.0 <= valuation.confidence_score <= 1.0
                assert valuation.recommendation is not None
                assert len(valuation.suggested_platforms) > 0
                
            finally:
                Path(temp_file.name).unlink(missing_ok=True)
                if Path(optimized_path).exists():
                    Path(optimized_path).unlink(missing_ok=True)


@pytest.mark.integration
class TestEndToEndWorkflow:
    """Test complete end-to-end workflow"""
    
    @pytest.mark.asyncio
    async def test_process_real_lego_scenario(self):
        """Simulate processing a real LEGO minifigure scenario"""
        
        # Skip if no API keys
        if not settings.anthropic_api_key or settings.anthropic_api_key.startswith("test_"):
            pytest.skip("No valid Anthropic API key")
        
        # Create a more realistic LEGO image with metadata
        img = Image.new('RGB', (1024, 768), color='white')
        draw = ImageDraw.Draw(img)
        
        # Draw a minifigure-like shape
        # Head
        draw.ellipse([450, 100, 550, 200], fill='yellow', outline='black', width=2)
        # Body
        draw.rectangle([425, 200, 575, 400], fill='red', outline='black', width=2)
        # Arms
        draw.rectangle([350, 220, 425, 350], fill='yellow', outline='black', width=2)
        draw.rectangle([575, 220, 650, 350], fill='yellow', outline='black', width=2)
        # Legs
        draw.rectangle([440, 400, 490, 550], fill='blue', outline='black', width=2)
        draw.rectangle([510, 400, 560, 550], fill='blue', outline='black', width=2)
        
        # Add LEGO text
        draw.text((100, 50), "LEGO Minifigure Collection", fill='black')
        draw.text((100, 100), "Star Wars - Luke Skywalker", fill='black')
        draw.text((100, 150), "Episode IV: A New Hope (1999)", fill='black')
        draw.text((100, 200), "Item sw0001a - Complete with Lightsaber", fill='black')
        draw.text((100, 250), "Condition: Used, Complete", fill='black')
        
        with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
            img.save(temp_file.name, 'JPEG', quality=95)
            
            try:
                # Process through the system
                processor = ImageProcessor()
                identifier = LegoIdentifier()
                valuation_engine = ValuationEngine()
                
                # Full pipeline
                file_path, upload_info = processor.save_image(
                    open(temp_file.name, 'rb').read(),
                    "luke_skywalker_minifig.jpg"
                )
                optimized = processor.optimize_image_for_ai(file_path)
                
                identification = await identifier.identify_lego_items(optimized)
                valuation = await valuation_engine.evaluate_item(identification)
                
                # Log results for debugging
                print("\n" + "="*60)
                print("COMPLETE WORKFLOW TEST RESULTS")
                print("="*60)
                print(f"Upload: {upload_info.filename} ({upload_info.size} bytes)")
                print(f"Identification Confidence: {identification.confidence_score:.2%}")
                print(f"Items Found: {len(identification.identified_items)}")
                if identification.identified_items:
                    for item in identification.identified_items:
                        print(f"  - {item.name or 'Unknown'} ({item.item_type.value})")
                print(f"Valuation: ${valuation.estimated_value:.2f}")
                print(f"Recommendation: {valuation.recommendation.value}")
                print("="*60)
                
                # Assertions
                assert upload_info.content_type == "image/jpeg"
                assert Path(file_path).exists()
                assert Path(optimized).exists()
                
                # Cleanup
                Path(file_path).unlink(missing_ok=True)
                Path(optimized).unlink(missing_ok=True)
                
            finally:
                Path(temp_file.name).unlink(missing_ok=True)


if __name__ == "__main__":
    # Run integration tests
    pytest.main([__file__, "-v", "-s"])  # -s to see print statements