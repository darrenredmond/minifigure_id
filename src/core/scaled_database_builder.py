"""
Scaled Database Builder for LEGO Minifigures
Systematically downloads minifigures from BrickLink API with improved image handling
"""

import asyncio
import aiohttp
import aiofiles
import sqlite3
import logging
from pathlib import Path
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime
import time
import hashlib
from urllib.parse import urlparse

from src.core.curated_minifigure_data import get_curated_minifigures_dict
from src.external.bricklink_client import BrickLinkClient

logger = logging.getLogger(__name__)

class ScaledDatabaseBuilder:
    """Enhanced database builder for systematic minifigure collection"""
    
    def __init__(self, db_path: str = "data/minifigure_database.db", images_dir: str = "data/minifigure_images"):
        self.db_path = db_path
        self.images_dir = Path(images_dir)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.bricklink_client = BrickLinkClient()
        
        # Popular themes in order of priority
        self.popular_themes = [
            "Star Wars",
            "Super Heroes", 
            "Disney",
            "Harry Potter",
            "Ninjago",
            "City",
            "Friends",
            "Creator",
            "Castle",
            "Pirates",
            "Space",
            "Classic"
        ]
        
        # Search terms for each theme
        self.theme_search_terms = {
            "Star Wars": ["star wars", "luke", "leia", "vader", "yoda", "obi-wan", "anakin", "darth", "jedi", "sith"],
            "Super Heroes": ["batman", "superman", "spider-man", "iron man", "captain america", "thor", "hulk", "wonder woman"],
            "Disney": ["mickey", "minnie", "elsa", "anna", "belle", "ariel", "cinderella", "disney"],
            "Harry Potter": ["harry potter", "hermione", "ron", "dumbledore", "voldemort", "hogwarts"],
            "Ninjago": ["ninjago", "kai", "jay", "zane", "cole", "lloyd", "nya"],
            "City": ["police", "fire", "construction", "chef", "doctor", "city"],
            "Friends": ["friends", "olivia", "stephanie", "emma", "andrea", "mia"],
            "Creator": ["creator", "minifigure", "figure"],
            "Castle": ["knight", "wizard", "king", "queen", "castle"],
            "Pirates": ["pirate", "captain", "sailor", "treasure"],
            "Space": ["astronaut", "space", "alien", "robot"],
            "Classic": ["classic", "basic", "minifigure"]
        }
        
        self.download_stats = {
            'total_attempted': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'skipped_existing': 0,
            'api_errors': 0,
            'image_errors': 0
        }
    
    def initialize_database(self):
        """Initialize the minifigures database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS minifigures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_number TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                theme TEXT,
                year_released INTEGER,
                image_url TEXT,
                image_path TEXT,
                description TEXT,
                rarity TEXT,
                source TEXT DEFAULT 'bricklink',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    async def build_scaled_database(self, target_count: int = 500, focus_theme: str = None) -> int:
        """Build database with systematic BrickLink API downloads"""
        logger.info(f"🚀 Building scaled database with target of {target_count} minifigures")
        if focus_theme:
            logger.info(f"🎯 Focusing on theme: {focus_theme}")
        
        self.initialize_database()
        
        # First, add curated data as base
        curated_count = self._add_curated_data()
        logger.info(f"📚 Added {curated_count} curated minifigures")
        
        # Then try BrickLink API
        api_count = await self._systematic_bricklink_download(target_count - curated_count, focus_theme)
        logger.info(f"🌐 Downloaded {api_count} minifigures from BrickLink API")
        
        # Download images for all minifigures
        await self._download_all_images()
        
        total_count = self.get_minifigure_count()
        logger.info(f"✅ Scaled database complete: {total_count} minifigures")
        
        return total_count
    
    def _add_curated_data(self) -> int:
        """Add curated minifigure data"""
        curated_data = get_curated_minifigures_dict()
        added_count = 0
        
        for minifig_data in curated_data:
            if self._store_minifigure(minifig_data):
                added_count += 1
        
        return added_count
    
    async def _systematic_bricklink_download(self, target_count: int, focus_theme: str = None) -> int:
        """Systematically download from BrickLink API"""
        if not self.bricklink_client.consumer_key:
            logger.warning("No BrickLink API credentials found, skipping API download")
            return 0
        
        downloaded_count = 0
        themes_to_search = [focus_theme] if focus_theme else self.popular_themes
        
        for theme in themes_to_search:
            if downloaded_count >= target_count:
                break
                
            logger.info(f"🔍 Searching theme: {theme}")
            search_terms = self.theme_search_terms.get(theme, [theme.lower()])
            
            for search_term in search_terms:
                if downloaded_count >= target_count:
                    break
                    
                try:
                    # Search for minifigures
                    search_results = self.bricklink_client.search_items("minifig", search_term)
                    
                    if not search_results:
                        continue
                    
                    # Process each result
                    for item in search_results[:20]:  # Limit per search term
                        if downloaded_count >= target_count:
                            break
                            
                        try:
                            # Get detailed information
                            details = self.bricklink_client.get_item_details("minifig", item['no'])
                            
                            if details and self._store_minifigure_from_api(details, theme):
                                downloaded_count += 1
                                self.download_stats['successful_downloads'] += 1
                                
                                if downloaded_count % 10 == 0:
                                    logger.info(f"📈 Downloaded {downloaded_count} minifigures so far...")
                            
                            # Rate limiting
                            await asyncio.sleep(0.5)
                            
                        except Exception as e:
                            logger.warning(f"Error processing item {item.get('no', 'unknown')}: {e}")
                            self.download_stats['api_errors'] += 1
                            continue
                    
                    # Rate limiting between search terms
                    await asyncio.sleep(1.0)
                    
                except Exception as e:
                    logger.error(f"Error searching for '{search_term}': {e}")
                    self.download_stats['api_errors'] += 1
                    continue
        
        return downloaded_count
    
    def _store_minifigure_from_api(self, details: Dict[str, Any], theme: str) -> bool:
        """Store minifigure data from BrickLink API"""
        try:
            minifig_data = {
                'item_number': details.get('no', ''),
                'name': details.get('name', ''),
                'theme': theme,
                'year_released': details.get('year_released', None),
                'image_url': details.get('image_url', ''),
                'description': details.get('description', ''),
                'rarity': self._determine_rarity(details.get('year_released', 2024)),
                'source': 'bricklink'
            }
            
            return self._store_minifigure(minifig_data)
            
        except Exception as e:
            logger.error(f"Error storing minifigure from API: {e}")
            return False
    
    def _store_minifigure(self, minifig_data: Dict[str, Any]) -> bool:
        """Store minifigure in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO minifigures 
                (item_number, name, theme, year_released, image_url, image_path, 
                 description, rarity, source, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                minifig_data['item_number'],
                minifig_data['name'],
                minifig_data['theme'],
                minifig_data['year_released'],
                minifig_data.get('image_url', ''),
                minifig_data.get('image_path', ''),
                minifig_data.get('description', ''),
                minifig_data.get('rarity', 'common'),
                minifig_data.get('source', 'bricklink'),
                datetime.now()
            ))
            conn.commit()
            return True
            
        except Exception as e:
            logger.error(f"Error storing minifigure {minifig_data.get('item_number', 'unknown')}: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    async def _download_all_images(self):
        """Download images for all minifigures with improved success rate"""
        logger.info("🖼️ Starting comprehensive image download...")
        
        # Get all minifigures without local images
        minifigures = self._get_minifigures_without_images()
        logger.info(f"Found {len(minifigures)} minifigures needing images")
        
        if not minifigures:
            logger.info("All minifigures already have local images")
            return
        
        # Download with improved retry logic
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=30),
            headers={'User-Agent': 'LEGO-Valuation-System/1.0 (Educational Use)'}
        ) as session:
            
            # Process in batches with concurrency control
            batch_size = 10
            for i in range(0, len(minifigures), batch_size):
                batch = minifigures[i:i + batch_size]
                await self._download_batch_images(session, batch)
                
                # Rate limiting between batches
                await asyncio.sleep(2.0)
    
    async def _download_batch_images(self, session: aiohttp.ClientSession, minifigures: List[Dict[str, Any]]):
        """Download images for a batch of minifigures"""
        tasks = []
        for minifig in minifigures:
            task = self._download_single_image(session, minifig)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _download_single_image(self, session: aiohttp.ClientSession, minifig: Dict[str, Any]) -> bool:
        """Download image for a single minifigure with retry logic"""
        item_number = minifig['item_number']
        image_url = minifig.get('image_url', '')
        
        if not image_url or not image_url.startswith('http'):
            return False
        
        # Try multiple image URL variations
        image_urls = self._get_image_url_variations(item_number, image_url)
        
        for attempt, url in enumerate(image_urls):
            try:
                self.download_stats['total_attempted'] += 1
                
                async with session.get(url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        
                        if len(image_data) < 1000:  # Too small to be a real image
                            continue
                        
                        # Save image
                        image_path = self._get_image_path(item_number, url)
                        async with aiofiles.open(image_path, 'wb') as f:
                            await f.write(image_data)
                        
                        # Update database with local path
                        self._update_image_path(item_number, str(image_path))
                        
                        logger.info(f"✅ Downloaded image for {item_number} (attempt {attempt + 1})")
                        self.download_stats['successful_downloads'] += 1
                        return True
                    
                    elif response.status == 404:
                        # Try next URL variation
                        continue
                    else:
                        logger.warning(f"HTTP {response.status} for {item_number}")
                        
            except Exception as e:
                logger.debug(f"Error downloading {item_number} from {url}: {e}")
                continue
        
        logger.warning(f"❌ Failed to download image for {item_number}")
        self.download_stats['image_errors'] += 1
        return False
    
    def _get_image_url_variations(self, item_number: str, original_url: str) -> List[str]:
        """Get multiple URL variations to try for image download"""
        variations = [original_url]
        
        # BrickLink image variations
        base_variations = [
            f"https://img.bricklink.com/ItemImage/MN/0/{item_number}.png",
            f"https://img.bricklink.com/ItemImage/MN/1/{item_number}.png", 
            f"https://img.bricklink.com/ItemImage/MN/2/{item_number}.png",
            f"https://img.bricklink.com/ItemImage/MN/0/{item_number}.jpg",
            f"https://img.bricklink.com/ItemImage/MN/1/{item_number}.jpg",
            f"https://img.bricklink.com/ItemImage/MN/2/{item_number}.jpg",
        ]
        
        variations.extend(base_variations)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for url in variations:
            if url not in seen:
                seen.add(url)
                unique_variations.append(url)
        
        return unique_variations[:8]  # Limit to 8 variations
    
    def _get_image_path(self, item_number: str, image_url: str) -> Path:
        """Get local path for storing image"""
        parsed_url = urlparse(image_url)
        path = parsed_url.path
        ext = 'png'  # Default
        
        if '.' in path:
            file_ext = path.split('.')[-1].lower()
            if file_ext in ['jpg', 'jpeg', 'png', 'gif', 'webp']:
                ext = file_ext
        
        filename = f"{item_number}.{ext}"
        return self.images_dir / filename
    
    def _update_image_path(self, item_number: str, image_path: str):
        """Update database with local image path"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                UPDATE minifigures 
                SET image_path = ? 
                WHERE item_number = ?
            """, (image_path, item_number))
            conn.commit()
        except Exception as e:
            logger.error(f"Error updating image path for {item_number}: {e}")
        finally:
            conn.close()
    
    def _get_minifigures_without_images(self) -> List[Dict[str, Any]]:
        """Get minifigures that don't have local images"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT item_number, name, theme, image_url 
            FROM minifigures 
            WHERE (image_path IS NULL OR image_path = '') 
            AND image_url IS NOT NULL 
            AND image_url != ''
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'item_number': row[0],
                'name': row[1], 
                'theme': row[2],
                'image_url': row[3]
            })
        
        conn.close()
        return results
    
    def _determine_rarity(self, year_released: int) -> str:
        """Determine rarity based on release year"""
        if not year_released:
            return "common"
        
        current_year = datetime.now().year
        age = current_year - year_released
        
        if age > 20:
            return "rare"
        elif age > 10:
            return "uncommon"
        else:
            return "common"
    
    def get_minifigure_count(self) -> int:
        """Get total number of minifigures in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM minifigures")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def get_download_stats(self) -> Dict[str, Any]:
        """Get download statistics"""
        return self.download_stats.copy()
    
    def search_minifigures(self, query: str, limit: int = 20) -> List[Dict[str, Any]]:
        """Search minifigures in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT item_number, name, theme, year_released, image_path, rarity
            FROM minifigures 
            WHERE name LIKE ? OR theme LIKE ? OR item_number LIKE ?
            ORDER BY name
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'item_number': row[0],
                'name': row[1],
                'theme': row[2],
                'year_released': row[3],
                'image_path': row[4],
                'rarity': row[5]
            })
        
        conn.close()
        return results
