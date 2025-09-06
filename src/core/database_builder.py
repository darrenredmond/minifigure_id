"""
Database Builder for LEGO Minifigure Identification
Downloads and indexes minifigure data from BrickLink and Brickset APIs
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
    source: str = "bricklink"  # or "brickset"
    last_updated: datetime = None

class MinifigureDatabaseBuilder:
    """Builds and maintains a local database of LEGO minifigures"""
    
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
        """Create the minifigure database schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Minifigures table
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
                last_updated TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)
        
        # Parts table for minifigure components
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS minifigure_parts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                minifigure_id INTEGER,
                part_number TEXT,
                part_name TEXT,
                color TEXT,
                quantity INTEGER,
                FOREIGN KEY (minifigure_id) REFERENCES minifigures (id)
            )
        """)
        
        # Image features table for fast matching
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS image_features (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                minifigure_id INTEGER,
                feature_vector BLOB,
                feature_type TEXT,
                FOREIGN KEY (minifigure_id) REFERENCES minifigures (id)
            )
        """)
        
        # Indexes for fast searching
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_item_number ON minifigures(item_number)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_theme ON minifigures(theme)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_year ON minifigures(year_released)")
        cursor.execute("CREATE INDEX IF NOT EXISTS idx_name ON minifigures(name)")
        
        conn.commit()
        conn.close()
        logger.info("Minifigure database initialized")
    
    async def download_minifigure_data(self, limit: Optional[int] = None):
        """Download minifigure data from BrickLink API"""
        logger.info("Starting minifigure data download from BrickLink...")
        
        # Get all minifigure categories
        categories = await self._get_minifigure_categories()
        
        total_downloaded = 0
        for category in categories:
            if limit and total_downloaded >= limit:
                break
                
            logger.info(f"Downloading category: {category}")
            minifigures = await self._download_category_minifigures(category)
            
            for minifig in minifigures:
                if limit and total_downloaded >= limit:
                    break
                    
                await self._process_minifigure(minifig)
                total_downloaded += 1
                
                if total_downloaded % 100 == 0:
                    logger.info(f"Downloaded {total_downloaded} minifigures...")
        
        logger.info(f"Download complete: {total_downloaded} minifigures")
        return total_downloaded
    
    async def _get_minifigure_categories(self) -> List[str]:
        """Get list of minifigure categories from BrickLink"""
        # BrickLink minifigure categories - use correct API format
        return [
            "minifig",  # General minifigures
        ]
    
    async def _download_category_minifigures(self, category: str) -> List[Dict[str, Any]]:
        """Download minifigures from a specific category"""
        try:
            # Use BrickLink search to get minifigures - search for common minifigure terms
            search_terms = ["minifigure", "minifig", "figure", "character"]
            all_results = []
            
            for term in search_terms:
                results = self.bricklink_client.search_items("minifig", term)
                all_results.extend(results)
            
            # Remove duplicates and filter
            seen = set()
            minifigures = []
            for item in all_results:
                item_id = item.get('no', '')
                if item_id and item_id not in seen:
                    seen.add(item_id)
                    minifigures.append(item)
            
            return minifigures[:50]  # Limit for now
            
        except Exception as e:
            logger.error(f"Error downloading category {category}: {e}")
            return []
    
    async def _process_minifigure(self, minifig_data: Dict[str, Any]):
        """Process and store a single minifigure"""
        try:
            # Extract basic info
            item_number = minifig_data.get('no', '')
            name = minifig_data.get('name', '')
            year_released = minifig_data.get('year_released')
            
            # Get detailed info
            details = await self._get_minifigure_details(item_number)
            
            # Download image
            image_path = await self._download_minifigure_image(details.get('image_url'), item_number)
            
            # Create MinifigureData object
            minifig = MinifigureData(
                item_number=item_number,
                name=name,
                theme=details.get('theme', 'Unknown'),
                year_released=year_released,
                image_url=details.get('image_url', ''),
                image_path=str(image_path) if image_path else None,
                description=details.get('description', ''),
                parts=details.get('parts', []),
                rarity=details.get('rarity', 'common'),
                source='bricklink',
                last_updated=datetime.now()
            )
            
            # Store in database
            self._store_minifigure(minifig)
            
        except Exception as e:
            logger.error(f"Error processing minifigure {minifig_data.get('no', 'unknown')}: {e}")
    
    async def _get_minifigure_details(self, item_number: str) -> Dict[str, Any]:
        """Get detailed information about a minifigure"""
        try:
            # Use BrickLink API to get item details
            url = f"{self.bricklink_client.BASE_URL}/items/minifig/{item_number}"
            headers = self.bricklink_client._get_oauth_headers("GET", url)
            
            response = self.session.get(url, headers=headers, timeout=10)
            if response.status_code == 200:
                data = response.json()
                return data.get('data', {})
            else:
                logger.warning(f"API returned {response.status_code} for {item_number}")
                # Return basic info from search result
                return {
                    'image_url': f"https://img.bricklink.com/ItemImage/MN/0/{item_number}.png",
                    'description': f"LEGO Minifigure {item_number}",
                    'theme': 'Unknown',
                    'rarity': 'common'
                }
            
        except Exception as e:
            logger.error(f"Error getting details for {item_number}: {e}")
            # Return basic info
            return {
                'image_url': f"https://img.bricklink.com/ItemImage/MN/0/{item_number}.png",
                'description': f"LEGO Minifigure {item_number}",
                'theme': 'Unknown',
                'rarity': 'common'
            }
    
    async def _download_minifigure_image(self, image_url: str, item_number: str) -> Optional[Path]:
        """Download and save minifigure image"""
        if not image_url:
            return None
            
        try:
            # Create filename
            filename = f"{item_number}_{hashlib.md5(image_url.encode()).hexdigest()[:8]}.jpg"
            image_path = self.images_dir / filename
            
            # Skip if already downloaded
            if image_path.exists():
                return image_path
            
            # Download image
            response = self.session.get(image_url, timeout=30)
            if response.status_code == 200:
                with open(image_path, 'wb') as f:
                    f.write(response.content)
                return image_path
                
        except Exception as e:
            logger.error(f"Error downloading image for {item_number}: {e}")
        
        return None
    
    def _store_minifigure(self, minifig: MinifigureData):
        """Store minifigure data in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        try:
            # Insert or update minifigure
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
                minifig.last_updated
            ))
            
            # Get the minifigure ID
            minifig_id = cursor.lastrowid
            
            # Store parts if available
            if minifig.parts:
                for part in minifig.parts:
                    cursor.execute("""
                        INSERT INTO minifigure_parts 
                        (minifigure_id, part_number, part_name, color, quantity)
                        VALUES (?, ?, ?, ?, ?)
                    """, (
                        minifig_id,
                        part.get('part_number', ''),
                        part.get('part_name', ''),
                        part.get('color', ''),
                        part.get('quantity', 1)
                    ))
            
            conn.commit()
            
        except Exception as e:
            logger.error(f"Error storing minifigure {minifig.item_number}: {e}")
            conn.rollback()
        finally:
            conn.close()
    
    def get_minifigure_count(self) -> int:
        """Get total number of minifigures in database"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute("SELECT COUNT(*) FROM minifigures")
        count = cursor.fetchone()[0]
        conn.close()
        return count
    
    def search_minifigures(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """Search minifigures by name or item number"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT item_number, name, theme, year_released, image_path, description
            FROM minifigures 
            WHERE name LIKE ? OR item_number LIKE ?
            ORDER BY name
            LIMIT ?
        """, (f"%{query}%", f"%{query}%", limit))
        
        results = []
        for row in cursor.fetchall():
            results.append({
                'item_number': row[0],
                'name': row[1],
                'theme': row[2],
                'year_released': row[3],
                'image_path': row[4],
                'description': row[5]
            })
        
        conn.close()
        return results

# CLI interface for database management
async def main():
    """Command line interface for database management"""
    import argparse
    
    parser = argparse.ArgumentParser(description="LEGO Minifigure Database Builder")
    parser.add_argument("command", choices=["init", "download", "search", "stats"])
    parser.add_argument("--limit", type=int, help="Limit number of minifigures to download")
    parser.add_argument("--query", type=str, help="Search query")
    
    args = parser.parse_args()
    
    builder = MinifigureDatabaseBuilder()
    
    if args.command == "init":
        builder.initialize_database()
        print("✓ Database initialized")
        
    elif args.command == "download":
        builder.initialize_database()
        count = await builder.download_minifigure_data(args.limit)
        print(f"✓ Downloaded {count} minifigures")
        
    elif args.command == "search":
        if not args.query:
            print("Please provide --query")
            return
        results = builder.search_minifigures(args.query)
        for result in results:
            print(f"{result['item_number']}: {result['name']} ({result['theme']})")
            
    elif args.command == "stats":
        count = builder.get_minifigure_count()
        print(f"Database contains {count} minifigures")

if __name__ == "__main__":
    asyncio.run(main())
