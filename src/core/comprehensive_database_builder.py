"""
Comprehensive Database Builder
Builds large minifigure database using multiple data sources and improved image handling
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
import json

from src.core.curated_minifigure_data import get_curated_minifigures_dict
from src.external.bricklink_client import BrickLinkClient

logger = logging.getLogger(__name__)

class ComprehensiveDatabaseBuilder:
    """Comprehensive database builder with multiple data sources"""
    
    def __init__(self, db_path: str = "data/minifigure_database.db", images_dir: str = "data/minifigure_images"):
        self.db_path = db_path
        self.images_dir = Path(images_dir)
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.bricklink_client = BrickLinkClient()
        
        # Comprehensive minifigure data from multiple sources
        self.comprehensive_minifigures = self._get_comprehensive_minifigure_data()
        
        self.download_stats = {
            'total_attempted': 0,
            'successful_downloads': 0,
            'failed_downloads': 0,
            'skipped_existing': 0,
            'api_errors': 0,
            'image_errors': 0
        }
    
    def _get_comprehensive_minifigure_data(self) -> List[Dict[str, Any]]:
        """Get comprehensive minifigure data from multiple sources"""
        minifigures = []
        
        # Star Wars minifigures (high priority)
        star_wars_minifigures = [
            {"item_number": "sw001", "name": "Luke Skywalker", "theme": "Star Wars", "year_released": 1999, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw001.png", "description": "Jedi Knight from A New Hope", "rarity": "rare"},
            {"item_number": "sw002", "name": "Princess Leia", "theme": "Star Wars", "year_released": 1999, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw002.png", "description": "Rebel leader and princess", "rarity": "rare"},
            {"item_number": "sw003", "name": "Darth Vader", "theme": "Star Wars", "year_released": 1999, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw003.png", "description": "Sith Lord and father of Luke", "rarity": "rare"},
            {"item_number": "sw004", "name": "Yoda", "theme": "Star Wars", "year_released": 2002, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw004.png", "description": "Jedi Master and wise teacher", "rarity": "rare"},
            {"item_number": "sw005", "name": "Obi-Wan Kenobi", "theme": "Star Wars", "year_released": 1999, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw005.png", "description": "Jedi Master and mentor", "rarity": "rare"},
            {"item_number": "sw006", "name": "Han Solo", "theme": "Star Wars", "year_released": 1999, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw006.png", "description": "Smuggler and pilot of Millennium Falcon", "rarity": "rare"},
            {"item_number": "sw007", "name": "Chewbacca", "theme": "Star Wars", "year_released": 1999, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw007.png", "description": "Wookiee co-pilot and friend", "rarity": "rare"},
            {"item_number": "sw008", "name": "C-3PO", "theme": "Star Wars", "year_released": 1999, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw008.png", "description": "Protocol droid", "rarity": "rare"},
            {"item_number": "sw009", "name": "R2-D2", "theme": "Star Wars", "year_released": 1999, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw009.png", "description": "Astromech droid", "rarity": "rare"},
            {"item_number": "sw010", "name": "Stormtrooper", "theme": "Star Wars", "year_released": 1999, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw010.png", "description": "Imperial soldier", "rarity": "uncommon"},
            {"item_number": "sw011", "name": "Boba Fett", "theme": "Star Wars", "year_released": 2000, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw011.png", "description": "Bounty hunter", "rarity": "rare"},
            {"item_number": "sw012", "name": "Emperor Palpatine", "theme": "Star Wars", "year_released": 2005, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw012.png", "description": "Sith Emperor", "rarity": "rare"},
            {"item_number": "sw013", "name": "Anakin Skywalker", "theme": "Star Wars", "year_released": 2002, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw013.png", "description": "Jedi Knight who becomes Vader", "rarity": "rare"},
            {"item_number": "sw014", "name": "Padmé Amidala", "theme": "Star Wars", "year_released": 2002, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw014.png", "description": "Queen and Senator of Naboo", "rarity": "rare"},
            {"item_number": "sw015", "name": "Mace Windu", "theme": "Star Wars", "year_released": 2002, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw015.png", "description": "Jedi Master with purple lightsaber", "rarity": "rare"},
            {"item_number": "sw016", "name": "Qui-Gon Jinn", "theme": "Star Wars", "year_released": 1999, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw016.png", "description": "Jedi Master and Obi-Wan's teacher", "rarity": "rare"},
            {"item_number": "sw017", "name": "Jar Jar Binks", "theme": "Star Wars", "year_released": 1999, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw017.png", "description": "Gungan from Naboo", "rarity": "uncommon"},
            {"item_number": "sw018", "name": "Darth Maul", "theme": "Star Wars", "year_released": 1999, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw018.png", "description": "Sith apprentice with double-bladed lightsaber", "rarity": "rare"},
            {"item_number": "sw019", "name": "Count Dooku", "theme": "Star Wars", "year_released": 2002, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw019.png", "description": "Sith Lord and former Jedi", "rarity": "rare"},
            {"item_number": "sw020", "name": "General Grievous", "theme": "Star Wars", "year_released": 2005, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw020.png", "description": "Cyborg general", "rarity": "rare"},
        ]
        
        # Super Heroes minifigures
        super_heroes_minifigures = [
            {"item_number": "sh001", "name": "Batman", "theme": "Super Heroes", "year_released": 2012, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh001.png", "description": "Dark Knight of Gotham", "rarity": "uncommon"},
            {"item_number": "sh002", "name": "Superman", "theme": "Super Heroes", "year_released": 2012, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh002.png", "description": "Man of Steel", "rarity": "uncommon"},
            {"item_number": "sh003", "name": "Spider-Man", "theme": "Super Heroes", "year_released": 2012, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh003.png", "description": "Friendly neighborhood Spider-Man", "rarity": "uncommon"},
            {"item_number": "sh004", "name": "Iron Man", "theme": "Super Heroes", "year_released": 2012, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh004.png", "description": "Genius billionaire playboy philanthropist", "rarity": "uncommon"},
            {"item_number": "sh005", "name": "Captain America", "theme": "Super Heroes", "year_released": 2012, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh005.png", "description": "Super soldier and leader", "rarity": "uncommon"},
            {"item_number": "sh006", "name": "Thor", "theme": "Super Heroes", "year_released": 2012, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh006.png", "description": "God of Thunder", "rarity": "uncommon"},
            {"item_number": "sh007", "name": "Hulk", "theme": "Super Heroes", "year_released": 2012, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh007.png", "description": "Incredible Hulk", "rarity": "uncommon"},
            {"item_number": "sh008", "name": "Wonder Woman", "theme": "Super Heroes", "year_released": 2012, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh008.png", "description": "Amazonian warrior princess", "rarity": "uncommon"},
            {"item_number": "sh009", "name": "Green Lantern", "theme": "Super Heroes", "year_released": 2012, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh009.png", "description": "Member of Green Lantern Corps", "rarity": "uncommon"},
            {"item_number": "sh010", "name": "Flash", "theme": "Super Heroes", "year_released": 2012, "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh010.png", "description": "Fastest man alive", "rarity": "uncommon"},
        ]
        
        # Disney minifigures
        disney_minifigures = [
            {"item_number": "dis001", "name": "Mickey Mouse", "theme": "Disney", "year_released": 2016, "image_url": "https://img.bricklink.com/ItemImage/MN/0/dis001.png", "description": "Classic Disney character", "rarity": "uncommon"},
            {"item_number": "dis002", "name": "Minnie Mouse", "theme": "Disney", "year_released": 2016, "image_url": "https://img.bricklink.com/ItemImage/MN/0/dis002.png", "description": "Mickey's girlfriend", "rarity": "uncommon"},
            {"item_number": "dis003", "name": "Elsa", "theme": "Disney", "year_released": 2014, "image_url": "https://img.bricklink.com/ItemImage/MN/0/dis003.png", "description": "Snow Queen from Frozen", "rarity": "uncommon"},
            {"item_number": "dis004", "name": "Anna", "theme": "Disney", "year_released": 2014, "image_url": "https://img.bricklink.com/ItemImage/MN/0/dis004.png", "description": "Princess of Arendelle", "rarity": "uncommon"},
            {"item_number": "dis005", "name": "Belle", "theme": "Disney", "year_released": 2017, "image_url": "https://img.bricklink.com/ItemImage/MN/0/dis005.png", "description": "Beauty and the Beast princess", "rarity": "uncommon"},
            {"item_number": "dis006", "name": "Ariel", "theme": "Disney", "year_released": 2017, "image_url": "https://img.bricklink.com/ItemImage/MN/0/dis006.png", "description": "Little Mermaid princess", "rarity": "uncommon"},
            {"item_number": "dis007", "name": "Cinderella", "theme": "Disney", "year_released": 2017, "image_url": "https://img.bricklink.com/ItemImage/MN/0/dis007.png", "description": "Classic Disney princess", "rarity": "uncommon"},
            {"item_number": "dis008", "name": "Jasmine", "theme": "Disney", "year_released": 2017, "image_url": "https://img.bricklink.com/ItemImage/MN/0/dis008.png", "description": "Aladdin princess", "rarity": "uncommon"},
            {"item_number": "dis009", "name": "Snow White", "theme": "Disney", "year_released": 2017, "image_url": "https://img.bricklink.com/ItemImage/MN/0/dis009.png", "description": "First Disney princess", "rarity": "uncommon"},
            {"item_number": "dis010", "name": "Rapunzel", "theme": "Disney", "year_released": 2017, "image_url": "https://img.bricklink.com/ItemImage/MN/0/dis010.png", "description": "Tangled princess", "rarity": "uncommon"},
        ]
        
        # Add all minifigures
        minifigures.extend(star_wars_minifigures)
        minifigures.extend(super_heroes_minifigures)
        minifigures.extend(disney_minifigures)
        
        # Add curated data
        curated_data = get_curated_minifigures_dict()
        for item in curated_data:
            # Avoid duplicates
            if not any(m['item_number'] == item['item_number'] for m in minifigures):
                minifigures.append(item)
        
        return minifigures
    
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
                source TEXT DEFAULT 'comprehensive',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    async def build_comprehensive_database(self, target_count: int = 500) -> int:
        """Build comprehensive database with multiple data sources"""
        logger.info(f"🚀 Building comprehensive database with target of {target_count} minifigures")
        
        self.initialize_database()
        
        # Add comprehensive minifigure data
        added_count = 0
        for minifig_data in self.comprehensive_minifigures:
            if added_count >= target_count:
                break
            if self._store_minifigure(minifig_data):
                added_count += 1
        
        logger.info(f"📚 Added {added_count} comprehensive minifigures")
        
        # Download images with improved success rate
        await self._download_all_images_enhanced()
        
        total_count = self.get_minifigure_count()
        logger.info(f"✅ Comprehensive database complete: {total_count} minifigures")
        
        return total_count
    
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
                minifig_data.get('year_released'),
                minifig_data.get('image_url', ''),
                minifig_data.get('image_path', ''),
                minifig_data.get('description', ''),
                minifig_data.get('rarity', 'common'),
                minifig_data.get('source', 'comprehensive'),
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
    
    async def _download_all_images_enhanced(self):
        """Download images with enhanced success rate"""
        logger.info("🖼️ Starting enhanced image download...")
        
        # Get all minifigures without local images
        minifigures = self._get_minifigures_without_images()
        logger.info(f"Found {len(minifigures)} minifigures needing images")
        
        if not minifigures:
            logger.info("All minifigures already have local images")
            return
        
        # Download with enhanced retry logic and multiple sources
        async with aiohttp.ClientSession(
            timeout=aiohttp.ClientTimeout(total=45),
            headers={'User-Agent': 'LEGO-Valuation-System/1.0 (Educational Use)'}
        ) as session:
            
            # Process in smaller batches for better success rate
            batch_size = 5
            for i in range(0, len(minifigures), batch_size):
                batch = minifigures[i:i + batch_size]
                await self._download_batch_images_enhanced(session, batch)
                
                # Longer rate limiting between batches
                await asyncio.sleep(3.0)
    
    async def _download_batch_images_enhanced(self, session: aiohttp.ClientSession, minifigures: List[Dict[str, Any]]):
        """Download images for a batch with enhanced success rate"""
        tasks = []
        for minifig in minifigures:
            task = self._download_single_image_enhanced(session, minifig)
            tasks.append(task)
        
        await asyncio.gather(*tasks, return_exceptions=True)
    
    async def _download_single_image_enhanced(self, session: aiohttp.ClientSession, minifig: Dict[str, Any]) -> bool:
        """Download image with enhanced retry logic and multiple sources"""
        item_number = minifig['item_number']
        original_url = minifig.get('image_url', '')
        
        if not original_url:
            return False
        
        # Get comprehensive list of URL variations
        image_urls = self._get_enhanced_image_url_variations(item_number, original_url)
        
        for attempt, url in enumerate(image_urls):
            try:
                self.download_stats['total_attempted'] += 1
                
                async with session.get(url) as response:
                    if response.status == 200:
                        image_data = await response.read()
                        
                        # More lenient size check
                        if len(image_data) < 500:  # Reduced threshold
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
                        logger.debug(f"HTTP {response.status} for {item_number} from {url}")
                        
            except Exception as e:
                logger.debug(f"Error downloading {item_number} from {url}: {e}")
                continue
        
        logger.warning(f"❌ Failed to download image for {item_number}")
        self.download_stats['image_errors'] += 1
        return False
    
    def _get_enhanced_image_url_variations(self, item_number: str, original_url: str) -> List[str]:
        """Get comprehensive list of URL variations"""
        variations = [original_url]
        
        # BrickLink variations
        bricklink_variations = [
            f"https://img.bricklink.com/ItemImage/MN/0/{item_number}.png",
            f"https://img.bricklink.com/ItemImage/MN/1/{item_number}.png", 
            f"https://img.bricklink.com/ItemImage/MN/2/{item_number}.png",
            f"https://img.bricklink.com/ItemImage/MN/0/{item_number}.jpg",
            f"https://img.bricklink.com/ItemImage/MN/1/{item_number}.jpg",
            f"https://img.bricklink.com/ItemImage/MN/2/{item_number}.jpg",
        ]
        
        # LEGO.com variations
        lego_variations = [
            f"https://www.lego.com/cdn/cs/set/assets/blt{item_number}.png",
            f"https://www.lego.com/cdn/cs/set/assets/blt{item_number}.jpg",
        ]
        
        # Alternative sources
        alt_variations = [
            f"https://images.brickset.com/sets/images/{item_number}.jpg",
            f"https://images.brickset.com/sets/images/{item_number}.png",
        ]
        
        variations.extend(bricklink_variations)
        variations.extend(lego_variations)
        variations.extend(alt_variations)
        
        # Remove duplicates while preserving order
        seen = set()
        unique_variations = []
        for url in variations:
            if url not in seen:
                seen.add(url)
                unique_variations.append(url)
        
        return unique_variations[:12]  # Limit to 12 variations
    
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
