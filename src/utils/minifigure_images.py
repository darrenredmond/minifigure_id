import os
import requests
from pathlib import Path
from typing import Optional, Dict, Any
import logging

logger = logging.getLogger(__name__)


class MinifigureImageService:
    """Service to fetch and cache individual minifigure images"""
    
    def __init__(self):
        self.cache_dir = Path("data/minifigure_images")
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # BrickLink image URL patterns
        self.bricklink_img_base = "https://img.bricklink.com/ItemImage/MN/0/"
        
    def get_minifigure_image_url(self, item_number: str) -> Optional[str]:
        """Get the BrickLink image URL for a minifigure"""
        if not item_number:
            return None
            
        # Clean item number (remove any suffixes like -1)
        clean_item_number = item_number.split('-')[0]
        
        # BrickLink uses different URL formats for different themes
        image_url = f"{self.bricklink_img_base}{clean_item_number}.png"
        
        return image_url
    
    def download_minifigure_image(self, item_number: str, item_name: str) -> Optional[str]:
        """Download and cache a minifigure image"""
        if not item_number:
            return None
            
        # Create safe filename
        safe_filename = f"{item_number.replace(':', '_')}.png"
        cache_path = self.cache_dir / safe_filename
        
        # Return cached image if it exists
        if cache_path.exists():
            return str(cache_path)
        
        # Try to download from BrickLink
        image_url = self.get_minifigure_image_url(item_number)
        if not image_url:
            return None
            
        try:
            response = requests.get(image_url, timeout=10, headers={
                'User-Agent': 'LEGO Valuation System'
            })
            
            if response.status_code == 200:
                with open(cache_path, 'wb') as f:
                    f.write(response.content)
                logger.info(f"Downloaded image for {item_name} ({item_number})")
                return str(cache_path)
            else:
                logger.debug(f"Could not download image for {item_number}: HTTP {response.status_code}")
                
        except Exception as e:
            logger.debug(f"Error downloading image for {item_number}: {e}")
            
        return None
    
    def create_placeholder_image(self, item_name: str, theme: str = "Unknown") -> str:
        """Create a simple placeholder image for minifigures without official images"""
        try:
            from PIL import Image, ImageDraw, ImageFont
            
            # Create a simple placeholder
            img = Image.new('RGB', (200, 200), color='#f0f0f0')
            draw = ImageDraw.Draw(img)
            
            # Draw a simple LEGO head shape
            draw.ellipse([50, 50, 150, 150], fill='#ffeb3b', outline='#333')  # Yellow head
            draw.ellipse([70, 70, 80, 80], fill='#333')  # Left eye
            draw.ellipse([120, 70, 130, 80], fill='#333')  # Right eye
            draw.arc([85, 90, 115, 110], start=0, end=180, fill='#333', width=2)  # Smile
            
            # Add text
            try:
                # Try to use a system font
                font = ImageFont.truetype("arial.ttf", 14)
            except:
                font = ImageFont.load_default()
                
            # Wrap text
            lines = []
            words = item_name.split()
            current_line = []
            
            for word in words:
                test_line = ' '.join(current_line + [word])
                bbox = draw.textbbox((0, 0), test_line, font=font)
                if bbox[2] - bbox[0] <= 180:  # Width fits
                    current_line.append(word)
                else:
                    if current_line:
                        lines.append(' '.join(current_line))
                        current_line = [word]
                    else:
                        lines.append(word)
            
            if current_line:
                lines.append(' '.join(current_line))
            
            # Draw text lines
            y_offset = 160
            for line in lines[:2]:  # Max 2 lines
                bbox = draw.textbbox((0, 0), line, font=font)
                text_width = bbox[2] - bbox[0]
                x = (200 - text_width) // 2
                draw.text((x, y_offset), line, fill='#333', font=font)
                y_offset += 20
            
            # Save placeholder
            safe_filename = f"placeholder_{item_name.replace(' ', '_').replace('/', '_')}.png"
            placeholder_path = self.cache_dir / safe_filename
            img.save(placeholder_path, 'PNG')
            
            return str(placeholder_path)
            
        except ImportError:
            logger.debug("PIL not available for placeholder generation")
            return None
        except Exception as e:
            logger.debug(f"Error creating placeholder for {item_name}: {e}")
            return None
    
    def get_minifigure_image(self, item_number: str, item_name: str, theme: str = "Unknown") -> Optional[str]:
        """Get image path for a minifigure (download, cache, or create placeholder)"""
        
        # Try to get official image first
        if item_number:
            image_path = self.download_minifigure_image(item_number, item_name)
            if image_path:
                return image_path
        
        # Create placeholder if no official image available
        placeholder_path = self.create_placeholder_image(item_name, theme)
        return placeholder_path
    
    def clear_cache(self):
        """Clear the image cache"""
        try:
            for file in self.cache_dir.glob("*"):
                file.unlink()
            logger.info("Cleared minifigure image cache")
        except Exception as e:
            logger.error(f"Error clearing cache: {e}")