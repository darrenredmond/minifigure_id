"""
Image Downloader for LEGO Minifigures
Downloads and stores minifigure images locally
"""

import asyncio
import aiohttp
import aiofiles
from pathlib import Path
from typing import List, Dict, Any, Optional
import logging
from urllib.parse import urlparse
import hashlib
import time

logger = logging.getLogger(__name__)

class ImageDownloader:
    """Downloads and manages minifigure images"""
    
    def __init__(self, images_dir: str = "data/minifigure_images"):
        self.images_dir = Path(images_dir)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.session = None
        self.download_stats = {
            'total_attempted': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'skipped_existing': 0
        }
    
    async def __aenter__(self):
        """Async context manager entry"""
        self.session = aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={
                'User-Agent': 'LEGO-Valuation-System/1.0 (Educational Use)'
            }
        )
        return self
    
    async def __aexit__(self, exc_type, exc_val, exc_tb):
        """Async context manager exit"""
        if self.session:
            await self.session.close()
    
    def _get_image_filename(self, item_number: str, image_url: str) -> str:
        """Generate a consistent filename for the image"""
        # Extract extension from URL or default to .png
        parsed_url = urlparse(image_url)
        path = parsed_url.path
        if '.' in path:
            ext = path.split('.')[-1].lower()
            if ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                return f"{item_number}.{ext}"
        
        # Default to .png for LEGO images
        return f"{item_number}.png"
    
    def _get_image_path(self, item_number: str, image_url: str) -> Path:
        """Get the full path for storing the image"""
        filename = self._get_image_filename(item_number, image_url)
        return self.images_dir / filename
    
    async def download_image(self, item_number: str, image_url: str) -> Optional[Path]:
        """Download a single minifigure image"""
        if not image_url or not image_url.startswith('http'):
            logger.warning(f"No valid image URL for {item_number}")
            return None
        
        image_path = self._get_image_path(item_number, image_url)
        
        # Skip if already exists
        if image_path.exists():
            logger.debug(f"Image already exists for {item_number}")
            self.download_stats['skipped_existing'] += 1
            return image_path
        
        self.download_stats['total_attempted'] += 1
        
        try:
            logger.info(f"Downloading image for {item_number}...")
            
            async with self.session.get(image_url) as response:
                if response.status == 200:
                    # Read image data
                    image_data = await response.read()
                    
                    # Validate it's actually an image
                    if len(image_data) < 100:  # Too small to be a real image
                        logger.warning(f"Image too small for {item_number}")
                        self.download_stats['failed_downloads'] += 1
                        return None
                    
                    # Save image
                    async with aiofiles.open(image_path, 'wb') as f:
                        await f.write(image_data)
                    
                    logger.info(f"✅ Downloaded image for {item_number}")
                    self.download_stats['successful_downloads'] += 1
                    return image_path
                else:
                    logger.warning(f"Failed to download {item_number}: HTTP {response.status}")
                    self.download_stats['failed_downloads'] += 1
                    return None
                    
        except Exception as e:
            logger.error(f"Error downloading image for {item_number}: {e}")
            self.download_stats['failed_downloads'] += 1
            return None
    
    async def download_all_images(self, minifigures: List[Dict[str, Any]], 
                                max_concurrent: int = 5) -> Dict[str, Any]:
        """Download images for all minifigures with rate limiting"""
        logger.info(f"🖼️  Starting download of {len(minifigures)} minifigure images...")
        
        # Create semaphore for rate limiting
        semaphore = asyncio.Semaphore(max_concurrent)
        
        async def download_with_semaphore(minifig):
            async with semaphore:
                item_number = minifig['item_number']
                image_url = minifig.get('image_url', '')
                
                if image_url:
                    image_path = await self.download_image(item_number, image_url)
                    return {
                        'item_number': item_number,
                        'image_path': str(image_path) if image_path else None,
                        'success': image_path is not None
                    }
                else:
                    logger.warning(f"No image URL for {item_number}")
                    return {
                        'item_number': item_number,
                        'image_path': None,
                        'success': False
                    }
        
        # Download all images concurrently
        tasks = [download_with_semaphore(mf) for mf in minifigures]
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_downloads = []
        failed_downloads = []
        
        for result in results:
            if isinstance(result, Exception):
                logger.error(f"Task failed with exception: {result}")
                failed_downloads.append({'error': str(result)})
            elif result['success']:
                successful_downloads.append(result)
            else:
                failed_downloads.append(result)
        
        # Update database with local image paths
        await self._update_database_with_local_paths(successful_downloads)
        
        logger.info(f"📊 Download complete:")
        logger.info(f"  ✅ Successful: {len(successful_downloads)}")
        logger.info(f"  ❌ Failed: {len(failed_downloads)}")
        logger.info(f"  ⏭️  Skipped existing: {self.download_stats['skipped_existing']}")
        
        return {
            'successful_downloads': len(successful_downloads),
            'failed_downloads': len(failed_downloads),
            'skipped_existing': self.download_stats['skipped_existing'],
            'total_attempted': self.download_stats['total_attempted']
        }
    
    async def _update_database_with_local_paths(self, successful_downloads: List[Dict[str, Any]]):
        """Update database with local image paths"""
        try:
            from src.core.real_data_database_builder import RealDataDatabaseBuilder
            builder = RealDataDatabaseBuilder()
            
            for download in successful_downloads:
                if download['image_path']:
                    # Update the database with local image path
                    builder._update_image_path(download['item_number'], download['image_path'])
            
            logger.info(f"Updated database with {len(successful_downloads)} local image paths")
            
        except Exception as e:
            logger.error(f"Error updating database with local paths: {e}")

# Convenience function
async def download_all_minifigure_images(minifigures: List[Dict[str, Any]], 
                                      images_dir: str = "data/minifigure_images",
                                      max_concurrent: int = 5) -> Dict[str, Any]:
    """Download all minifigure images"""
    async with ImageDownloader(images_dir) as downloader:
        return await downloader.download_all_images(minifigures, max_concurrent)
