"""
Real Data Database Builder for LEGO Minifigure Identification
Downloads only real minifigure data from BrickLink API - no mock data
"""

import asyncio
import json
import sqlite3
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
import requests
import hashlib
from dataclasses import dataclass
import logging

from config.settings import settings
from src.external.bricklink_client import BrickLinkClient
from src.core.curated_minifigure_data import get_curated_minifigures_dict

logger = logging.getLogger(__name__)

@dataclass
class MinifigureData:
    """Structured data for a minifigure"""
    item_number: str
    name: str
    theme: str
    year_released: Optional[int]
    image_url: str
    image_path: Optional[str] = None
    description: Optional[str] = None
    parts: List[Dict[str, Any]] = None
    rarity: Optional[str] = None
    source: str = "bricklink"
    last_updated: datetime = None

class RealDataDatabaseBuilder:
    """Builds a minifigure database using only real BrickLink data"""
    
    def __init__(self, db_path: str = "data/minifigure_database.db"):
        self.db_path = db_path
        self.images_dir = Path("data/minifigure_images")
        self.images_dir.mkdir(parents=True, exist_ok=True)
        self.bricklink_client = BrickLinkClient()
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'LEGO-Valuation-System/1.0'
        })
        
    def initialize_database(self):
        """Initialize the minifigure database with proper schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create minifigures table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS minifigures (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                item_number TEXT UNIQUE NOT NULL,
                name TEXT NOT NULL,
                theme TEXT NOT NULL,
                year_released INTEGER,
                image_url TEXT,
                image_path TEXT,
                description TEXT,
                rarity TEXT,
                source TEXT DEFAULT 'bricklink',
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Create indexes for better performance
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_number ON minifigures(item_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON minifigures(name)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_theme ON minifigures(theme)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_year ON minifigures(year_released)")
        
        conn.commit()
        conn.close()
        logger.info("Database initialized successfully")
    
    def get_minifigure_count(self) -> int:
        """Get the current count of minifigures in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM minifigures")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def search_minifigures(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search minifigures by name or theme"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT item_number, name, theme, year_released, image_url, description, rarity
            FROM minifigures 
            WHERE name LIKE ? OR theme LIKE ? OR item_number LIKE ?
            ORDER BY 
                CASE 
                    WHEN name LIKE ? THEN 1
                    WHEN item_number LIKE ? THEN 2
                    ELSE 3
                END,
                year_released DESC
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", f"%{query}%", f"{query}%", f"{query}%", limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'item_number': row[0],
                'name': row[1],
                'theme': row[2],
                'year_released': row[3],
                'image_url': row[4],
                'description': row[5],
                'rarity': row[6]
            })
        
        conn.close()
        return results
    
    def _get_all_minifigures(self) -> List[Dict[str, Any]]:
        """Get all minifigures from the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT id, item_number, name, theme, year_released, image_url, image_path, description, rarity
            FROM minifigures
            ORDER BY name
        """)
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'id': row[0],
                'item_number': row[1],
                'name': row[2],
                'theme': row[3],
                'year_released': row[4],
                'image_url': row[5],
                'image_path': row[6],
                'description': row[7],
                'rarity': row[8]
            })
        
        conn.close()
        return results
    
    def _store_minifigure(self, minifig: MinifigureData):
        """Store a minifigure in the database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute("""
                INSERT OR REPLACE INTO minifigures 
                (item_number, name, theme, year_released, image_url, image_path, 
                 description, rarity, source, last_updated)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                minifig.item_number,
                minifig.name,
                minifig.theme,
                minifig.year_released,
                minifig.image_url,
                minifig.image_path,
                minifig.description,
                minifig.rarity,
                minifig.source,
                minifig.last_updated or datetime.now()
            ))
            conn.commit()
        except Exception as e:
            logger.error(f"Error storing minifigure {minifig.item_number}: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    async def _try_bricklink_download(self, target_count: int) -> int:
        """Try to download minifigures from BrickLink API"""
        logger.info(f"🔄 Attempting to download {target_count} minifigures from BrickLink API...")
        
        if not (self.bricklink_client.consumer_key and self.bricklink_client.consumer_secret and 
                self.bricklink_client.token_value and self.bricklink_client.token_secret):
            logger.warning("⚠️  No BrickLink API credentials found - skipping real data download")
            return 0
        
        downloaded_count = 0
        
        try:
            # Search terms for different minifigure types
            search_terms = [
                "minifig", "figure", "character", "hero", "villain",
                "police", "fire", "construction", "space", "castle",
                "pirates", "ninja", "superhero", "batman", "spider",
                "harry", "potter", "star", "wars", "disney",
                "friends", "city", "creator", "classic", "basic"
            ]
            
            for term in search_terms:
                if downloaded_count >= target_count:
                    break
                
                logger.info(f"🔍 Searching for '{term}' minifigures...")
                
                try:
                    # Search for minifigures
                    search_results = self.bricklink_client.search_items("minifig", term)
                    
                    if not search_results:
                        logger.info(f"No results for '{term}'")
                        continue
                    
                    # Process each result
                    for item in search_results[:20]:  # Limit per search term
                        if downloaded_count >= target_count:
                            break
                        
                        try:
                            minifig_data = self._process_minifigure(item)
                            if minifig_data:
                                self._store_minifigure(minifig_data)
                                downloaded_count += 1
                                
                                if downloaded_count % 50 == 0:
                                    logger.info(f"📦 Downloaded {downloaded_count} minifigures...")
                                
                        except Exception as e:
                            logger.warning(f"Error processing item {item.get('no', 'unknown')}: {e}")
                            continue
                    
                    # Small delay to respect rate limits
                    await asyncio.sleep(0.5)
                    
                except Exception as e:
                    logger.warning(f"Error searching for '{term}': {e}")
                    continue
            
            logger.info(f"✅ Successfully downloaded {downloaded_count} minifigures from BrickLink")
            return downloaded_count
            
        except Exception as e:
            logger.error(f"❌ Error during BrickLink download: {e}")
            return downloaded_count
    
    def _process_minifigure(self, item: Dict[str, Any]) -> Optional[MinifigureData]:
        """Process a minifigure item from BrickLink API"""
        try:
            item_number = item.get('no', '')
            name = item.get('name', '')
            year_released = item.get('year_released')
            
            if not item_number or not name:
                return None
            
            # Get detailed information
            try:
                details = self.bricklink_client.get_item_details("minifig", item_number)
                if details:
                    theme = details.get('category_name', 'Unknown')
                    description = details.get('description', '')
                    image_url = details.get('image_url', '')
                else:
                    theme = 'Unknown'
                    description = ''
                    image_url = ''
            except Exception as e:
                logger.warning(f"Could not get details for {item_number}: {e}")
                theme = 'Unknown'
                description = ''
                image_url = ''
            
            # Determine rarity based on year and theme
            rarity = self._determine_rarity(year_released, theme)
            
            return MinifigureData(
                item_number=item_number,
                name=name,
                theme=theme,
                year_released=year_released,
                image_url=image_url,
                description=description,
                rarity=rarity,
                source="bricklink",
                last_updated=datetime.now()
            )
            
        except Exception as e:
            logger.error(f"Error processing minifigure {item.get('no', 'unknown')}: {e}")
            return None
    
    def _determine_rarity(self, year_released: Optional[int], theme: str) -> str:
        """Determine rarity based on year and theme"""
        if not year_released:
            return "unknown"
        
        current_year = datetime.now().year
        age = current_year - year_released
        
        # Special themes that are typically rarer
        rare_themes = ["Star Wars", "Super Heroes", "Disney", "Harry Potter", "Marvel", "DC Comics"]
        
        if theme in rare_themes:
            if age > 15:
                return "rare"
            elif age > 10:
                return "uncommon"
            else:
                return "common"
        else:
            if age > 20:
                return "rare"
            elif age > 10:
                return "uncommon"
            else:
                return "common"
    
    def _update_image_path(self, item_number: str, image_path: str):
        """Update the local image path for a minifigure"""
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
            conn.rollback()
        finally:
            conn.close()
    
    def _add_curated_data(self, target_count: int) -> int:
        """Add curated real minifigure data as fallback"""
        logger.info(f"📚 Adding curated real minifigure data...")
        
        curated_data = get_curated_minifigures_dict()
        added_count = 0
        
        # Add all curated minifigures (they're all real)
        for minifig_data in curated_data:
            if added_count >= target_count:
                break
                
            minifig = MinifigureData(
                item_number=minifig_data['item_number'],
                name=minifig_data['name'],
                theme=minifig_data['theme'],
                year_released=minifig_data['year_released'],
                image_url=minifig_data['image_url'],
                description=minifig_data['description'],
                rarity=minifig_data['rarity'],
                source="curated",
                last_updated=minifig_data['last_updated']
            )
            
            self._store_minifigure(minifig)
            added_count += 1
        
        logger.info(f"✅ Added {added_count} curated real minifigures")
        return added_count
    
    async def build_real_data_database(self, target_count: int = 1000) -> int:
        """Build database using only real BrickLink data"""
        logger.info(f"🚀 Building real data database with target of {target_count} minifigures...")
        
        # Initialize database
        self.initialize_database()
        
        # Try to download from BrickLink
        downloaded_count = await self._try_bricklink_download(target_count)
        
        if downloaded_count == 0:
            logger.warning("⚠️  No minifigures could be downloaded from BrickLink API")
            logger.info("🔄 Falling back to curated real minifigure data...")
            downloaded_count = self._add_curated_data(target_count)
        
        final_count = self.get_minifigure_count()
        logger.info(f"✅ Real data database complete: {final_count} minifigures")
        
        if final_count < target_count:
            logger.warning(f"⚠️  Only downloaded {final_count} minifigures (target was {target_count})")
            logger.warning("This may be due to API rate limits or network issues")
        
        return final_count

# Convenience function for easy access
async def build_real_database(target_count: int = 1000) -> int:
    """Build a real data database with the specified number of minifigures"""
    builder = RealDataDatabaseBuilder()
    return await builder.build_real_data_database(target_count)
