"""
Production Database Builder for LEGO Minifigure Identification
Downloads real minifigure data from BrickLink API with fallback to comprehensive mock data
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
    source: str = "bricklink"
    last_updated: datetime = None

class ProductionDatabaseBuilder:
    """Builds a comprehensive minifigure database for production use"""
    
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
        logger.info("Production database initialized")
    
    async def build_production_database(self, target_count: int = 1000):
        """Build a comprehensive production database"""
        print(f"🚀 Building production database with target of {target_count} minifigures...")
        
        # Initialize database
        self.initialize_database()
        
        # Try to get real data from BrickLink first
        real_count = await self._try_bricklink_download(target_count // 2)
        
        # Fill remaining with comprehensive mock data
        remaining = target_count - real_count
        if remaining > 0:
            print(f"📦 Adding {remaining} comprehensive mock minifigures...")
            mock_count = self._add_comprehensive_mock_data(remaining)
            real_count += mock_count
        
        total_count = self.get_minifigure_count()
        print(f"✅ Production database complete: {total_count} minifigures")
        return total_count
    
    async def _try_bricklink_download(self, target_count: int) -> int:
        """Try to download real data from BrickLink API"""
        print("🔗 Attempting to download from BrickLink API...")
        
        try:
            # Test API connection first
            test_results = self.bricklink_client.search_items("minifig", "test")
            if not test_results:
                print("⚠️  BrickLink API not available, using mock data")
                return 0
            
            print("✅ BrickLink API connected, downloading real data...")
            
            # Download real minifigures
            downloaded = 0
            search_terms = [
                "minifigure", "minifig", "figure", "character", "person",
                "police", "construction", "chef", "astronaut", "ninja",
                "spider", "batman", "superman", "knight", "pirate",
                "wizard", "civilian", "worker", "officer", "soldier"
            ]
            
            for term in search_terms:
                if downloaded >= target_count:
                    break
                    
                results = self.bricklink_client.search_items("minifig", term)
                for item in results[:10]:  # Limit per term
                    if downloaded >= target_count:
                        break
                    await self._process_minifigure(item)
                    downloaded += 1
                    
                print(f"📥 Downloaded {downloaded}/{target_count} from BrickLink...")
            
            return downloaded
            
        except Exception as e:
            print(f"⚠️  BrickLink API error: {e}")
            print("📦 Falling back to comprehensive mock data...")
            return 0
    
    def _add_comprehensive_mock_data(self, count: int) -> int:
        """Add comprehensive mock minifigure data"""
        comprehensive_minifigures = self._get_comprehensive_minifigure_data()
        
        # Generate more minifigures by creating variations
        all_minifigures = comprehensive_minifigures.copy()
        
        # Add variations for each theme
        for base_minifig in comprehensive_minifigures:
            if len(all_minifigures) >= count:
                break
                
            # Create variations
            variations = self._create_minifigure_variations(base_minifig)
            all_minifigures.extend(variations)
        
        # If we still need more, generate additional minifigures
        if len(all_minifigures) < count:
            additional = self._generate_additional_minifigures(count - len(all_minifigures))
            all_minifigures.extend(additional)
        
        # Select the requested count
        selected = all_minifigures[:count]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        added = 0
        for minifig in selected:
            try:
                cursor.execute("""
                    INSERT OR REPLACE INTO minifigures 
                    (item_number, name, theme, year_released, image_url, image_path, 
                     description, rarity, source, last_updated)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    minifig['item_number'],
                    minifig['name'],
                    minifig['theme'],
                    minifig['year_released'],
                    minifig['image_url'],
                    None,  # No local image for mock data
                    minifig['description'],
                    minifig['rarity'],
                    'mock',
                    datetime.now()
                ))
                added += 1
            except Exception as e:
                logger.error(f"Error inserting {minifig['item_number']}: {e}")
        
        conn.commit()
        conn.close()
        return added
    
    def _create_minifigure_variations(self, base_minifig: Dict[str, Any]) -> List[Dict[str, Any]]:
        """Create variations of a base minifigure"""
        variations = []
        base_number = base_minifig['item_number']
        base_name = base_minifig['name']
        theme = base_minifig['theme']
        
        # Create 10-15 variations per base minifigure
        for i in range(1, 11):  # Create 10 variations
            variation = base_minifig.copy()
            variation['item_number'] = f"{base_number}v{i:02d}"
            variation['name'] = f"{base_name} (Variant {i})"
            variation['year_released'] = (base_minifig.get('year_released', 2020) + i) % 2024
            variation['description'] = f"{base_minifig['description']} - Variation {i}"
            variation['image_url'] = f"https://img.bricklink.com/ItemImage/MN/0/{variation['item_number']}.png"
            variations.append(variation)
        
        return variations
    
    def _generate_additional_minifigures(self, count: int) -> List[Dict[str, Any]]:
        """Generate additional minifigures to reach target count"""
        additional = []
        themes = ["City", "Space", "Super Heroes", "Ninjago", "Castle", "Pirates", "Friends", "Generic", "Star Wars", "Harry Potter", "Marvel", "DC Comics", "Disney"]
        occupations = ["Worker", "Officer", "Pilot", "Doctor", "Teacher", "Chef", "Engineer", "Scientist", "Artist", "Musician", "Athlete", "Farmer", "Sailor", "Explorer"]
        
        for i in range(count):
            theme = themes[i % len(themes)]
            occupation = occupations[i % len(occupations)]
            item_number = f"gen{i+1000:04d}"
            name = f"{occupation} {i+1}"
            
            minifig = {
                'item_number': item_number,
                'name': name,
                'theme': theme,
                'year_released': 2020 + (i % 5),
                'description': f"Generic {occupation} from {theme} theme",
                'rarity': 'common' if i % 3 == 0 else 'uncommon',
                'image_url': f"https://img.bricklink.com/ItemImage/MN/0/{item_number}.png"
            }
            additional.append(minifig)
        
        return additional
    
    def _get_comprehensive_minifigure_data(self) -> List[Dict[str, Any]]:
        """Get comprehensive mock minifigure data covering all major themes"""
        return [
            # City Theme
            {"item_number": "cty001", "name": "Police Officer", "theme": "City", "year_released": 2020, "description": "City Police Officer with blue uniform and cap", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cty001.png"},
            {"item_number": "cty002", "name": "Construction Worker", "theme": "City", "year_released": 2019, "description": "Construction Worker with orange safety vest and hard hat", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cty002.png"},
            {"item_number": "cty003", "name": "Chef", "theme": "City", "year_released": 2021, "description": "Chef with white uniform and chef hat", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cty003.png"},
            {"item_number": "cty004", "name": "Firefighter", "theme": "City", "year_released": 2020, "description": "Firefighter with red uniform and helmet", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cty004.png"},
            {"item_number": "cty005", "name": "Doctor", "theme": "City", "year_released": 2021, "description": "Doctor with white coat and stethoscope", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cty005.png"},
            {"item_number": "cty006", "name": "Pilot", "theme": "City", "year_released": 2019, "description": "Airline Pilot with uniform and cap", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cty006.png"},
            {"item_number": "cty007", "name": "Teacher", "theme": "City", "year_released": 2020, "description": "School Teacher with casual clothes", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cty007.png"},
            {"item_number": "cty008", "name": "Mail Carrier", "theme": "City", "year_released": 2018, "description": "Mail Carrier with blue uniform and mailbag", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cty008.png"},
            
            # Space Theme
            {"item_number": "spc001", "name": "Astronaut", "theme": "Space", "year_released": 2020, "description": "Space Astronaut with white suit and helmet", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/spc001.png"},
            {"item_number": "spc002", "name": "Space Pilot", "theme": "Space", "year_released": 2019, "description": "Space Pilot with futuristic uniform", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/spc002.png"},
            {"item_number": "spc003", "name": "Alien", "theme": "Space", "year_released": 2021, "description": "Green Alien with large head", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/spc003.png"},
            {"item_number": "spc004", "name": "Robot", "theme": "Space", "year_released": 2018, "description": "Mechanical Robot with metallic parts", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/spc004.png"},
            
            # Super Heroes Theme
            {"item_number": "sh001", "name": "Spider-Man", "theme": "Super Heroes", "year_released": 2019, "description": "Spider-Man with red and blue suit", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh001.png"},
            {"item_number": "sh002", "name": "Batman", "theme": "Super Heroes", "year_released": 2018, "description": "Batman with black cape and cowl", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh002.png"},
            {"item_number": "sh003", "name": "Superman", "theme": "Super Heroes", "year_released": 2017, "description": "Superman with blue suit and red cape", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh003.png"},
            {"item_number": "sh004", "name": "Wonder Woman", "theme": "Super Heroes", "year_released": 2020, "description": "Wonder Woman with golden armor", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh004.png"},
            {"item_number": "sh005", "name": "Iron Man", "theme": "Super Heroes", "year_released": 2019, "description": "Iron Man with red and gold armor", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/sh005.png"},
            
            # Ninjago Theme
            {"item_number": "nin001", "name": "Ninja Warrior", "theme": "Ninjago", "year_released": 2020, "description": "Ninja Warrior with katana and ninja outfit", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/nin001.png"},
            {"item_number": "nin002", "name": "Sensei Wu", "theme": "Ninjago", "year_released": 2019, "description": "Master Wu with beard and staff", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/nin002.png"},
            {"item_number": "nin003", "name": "Kai", "theme": "Ninjago", "year_released": 2021, "description": "Kai with red ninja suit and fire powers", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/nin003.png"},
            {"item_number": "nin004", "name": "Jay", "theme": "Ninjago", "year_released": 2021, "description": "Jay with blue ninja suit and lightning powers", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/nin004.png"},
            {"item_number": "nin005", "name": "Zane", "theme": "Ninjago", "year_released": 2021, "description": "Zane with white ninja suit and ice powers", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/nin005.png"},
            {"item_number": "nin006", "name": "Cole", "theme": "Ninjago", "year_released": 2021, "description": "Cole with black ninja suit and earth powers", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/nin006.png"},
            
            # Castle Theme
            {"item_number": "cas001", "name": "Knight", "theme": "Castle", "year_released": 2017, "description": "Medieval Knight with armor and sword", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cas001.png"},
            {"item_number": "cas002", "name": "Wizard", "theme": "Castle", "year_released": 2016, "description": "Wizard with robe and staff", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cas002.png"},
            {"item_number": "cas003", "name": "King", "theme": "Castle", "year_released": 2015, "description": "Medieval King with crown and royal robes", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cas003.png"},
            {"item_number": "cas004", "name": "Queen", "theme": "Castle", "year_released": 2015, "description": "Medieval Queen with crown and dress", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cas004.png"},
            {"item_number": "cas005", "name": "Archer", "theme": "Castle", "year_released": 2018, "description": "Medieval Archer with bow and quiver", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cas005.png"},
            {"item_number": "cas006", "name": "Blacksmith", "theme": "Castle", "year_released": 2017, "description": "Medieval Blacksmith with apron and hammer", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cas006.png"},
            
            # Pirates Theme
            {"item_number": "pir001", "name": "Pirate Captain", "theme": "Pirates", "year_released": 2015, "description": "Pirate Captain with hat and sword", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/pir001.png"},
            {"item_number": "pir002", "name": "Pirate Crew", "theme": "Pirates", "year_released": 2016, "description": "Pirate Crew Member with bandana", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/pir002.png"},
            {"item_number": "pir003", "name": "Pirate Lady", "theme": "Pirates", "year_released": 2017, "description": "Female Pirate with dress and sword", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/pir003.png"},
            {"item_number": "pir004", "name": "Navy Officer", "theme": "Pirates", "year_released": 2015, "description": "Navy Officer with blue uniform", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/pir004.png"},
            
            # Friends Theme
            {"item_number": "fri001", "name": "Emma", "theme": "Friends", "year_released": 2020, "description": "Emma with pink top and jeans", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/fri001.png"},
            {"item_number": "fri002", "name": "Olivia", "theme": "Friends", "year_released": 2020, "description": "Olivia with purple dress", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/fri002.png"},
            {"item_number": "fri003", "name": "Stephanie", "theme": "Friends", "year_released": 2021, "description": "Stephanie with green top and skirt", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/fri003.png"},
            {"item_number": "fri004", "name": "Mia", "theme": "Friends", "year_released": 2021, "description": "Mia with blue shirt and shorts", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/fri004.png"},
            {"item_number": "fri005", "name": "Andrea", "theme": "Friends", "year_released": 2019, "description": "Andrea with yellow dress", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/fri005.png"},
            
            # Generic/Creator Theme
            {"item_number": "gen001", "name": "Female Civilian", "theme": "Generic", "year_released": 2020, "description": "Generic female figure with casual clothes", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/gen001.png"},
            {"item_number": "gen002", "name": "Male Civilian", "theme": "Generic", "year_released": 2020, "description": "Generic male figure with casual clothes", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/gen002.png"},
            {"item_number": "gen003", "name": "Child Figure", "theme": "Generic", "year_released": 2021, "description": "Generic child figure with colorful clothes", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/gen003.png"},
            {"item_number": "gen004", "name": "Elderly Figure", "theme": "Generic", "year_released": 2019, "description": "Generic elderly figure with glasses", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/gen004.png"},
            
            # Star Wars Theme
            {"item_number": "sw001", "name": "Luke Skywalker", "theme": "Star Wars", "year_released": 2018, "description": "Luke Skywalker with lightsaber", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw001.png"},
            {"item_number": "sw002", "name": "Princess Leia", "theme": "Star Wars", "year_released": 2018, "description": "Princess Leia with white dress", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw002.png"},
            {"item_number": "sw003", "name": "Darth Vader", "theme": "Star Wars", "year_released": 2017, "description": "Darth Vader with black helmet and cape", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw003.png"},
            {"item_number": "sw004", "name": "Stormtrooper", "theme": "Star Wars", "year_released": 2019, "description": "Stormtrooper with white armor", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw004.png"},
            {"item_number": "sw005", "name": "Yoda", "theme": "Star Wars", "year_released": 2016, "description": "Yoda with green skin and lightsaber", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/sw005.png"},
            
            # Harry Potter Theme
            {"item_number": "hp001", "name": "Harry Potter", "theme": "Harry Potter", "year_released": 2019, "description": "Harry Potter with glasses and wand", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/hp001.png"},
            {"item_number": "hp002", "name": "Hermione Granger", "theme": "Harry Potter", "year_released": 2019, "description": "Hermione with brown hair and wand", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/hp002.png"},
            {"item_number": "hp003", "name": "Ron Weasley", "theme": "Harry Potter", "year_released": 2019, "description": "Ron Weasley with red hair and wand", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/hp003.png"},
            {"item_number": "hp004", "name": "Dumbledore", "theme": "Harry Potter", "year_released": 2018, "description": "Dumbledore with long beard and wand", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/hp004.png"},
            
            # Marvel Theme
            {"item_number": "mar001", "name": "Captain America", "theme": "Marvel", "year_released": 2019, "description": "Captain America with shield", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/mar001.png"},
            {"item_number": "mar002", "name": "Thor", "theme": "Marvel", "year_released": 2018, "description": "Thor with hammer and cape", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/mar002.png"},
            {"item_number": "mar003", "name": "Hulk", "theme": "Marvel", "year_released": 2019, "description": "Hulk with green skin and torn clothes", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/mar003.png"},
            {"item_number": "mar004", "name": "Black Widow", "theme": "Marvel", "year_released": 2020, "description": "Black Widow with black suit", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/mar004.png"},
            
            # DC Comics Theme
            {"item_number": "dc001", "name": "Superman", "theme": "DC Comics", "year_released": 2017, "description": "Superman with blue suit and red cape", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/dc001.png"},
            {"item_number": "dc002", "name": "Batman", "theme": "DC Comics", "year_released": 2018, "description": "Batman with black cape and cowl", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/dc002.png"},
            {"item_number": "dc003", "name": "Wonder Woman", "theme": "DC Comics", "year_released": 2020, "description": "Wonder Woman with golden armor", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/dc003.png"},
            {"item_number": "dc004", "name": "Flash", "theme": "DC Comics", "year_released": 2019, "description": "Flash with red suit and lightning bolt", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/dc004.png"},
            
            # Disney Theme
            {"item_number": "dis001", "name": "Mickey Mouse", "theme": "Disney", "year_released": 2018, "description": "Mickey Mouse with red shorts", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/dis001.png"},
            {"item_number": "dis002", "name": "Minnie Mouse", "theme": "Disney", "year_released": 2018, "description": "Minnie Mouse with polka dot dress", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/dis002.png"},
            {"item_number": "dis003", "name": "Donald Duck", "theme": "Disney", "year_released": 2019, "description": "Donald Duck with sailor suit", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/dis003.png"},
            {"item_number": "dis004", "name": "Goofy", "theme": "Disney", "year_released": 2019, "description": "Goofy with green shirt and hat", "rarity": "rare", "image_url": "https://img.bricklink.com/ItemImage/MN/0/dis004.png"},
            
            # Creator Expert Theme
            {"item_number": "ce001", "name": "Architect", "theme": "Creator Expert", "year_released": 2020, "description": "Architect with blueprints and hard hat", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/ce001.png"},
            {"item_number": "ce002", "name": "Engineer", "theme": "Creator Expert", "year_released": 2021, "description": "Engineer with safety vest and tools", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/ce002.png"},
            {"item_number": "ce003", "name": "Scientist", "theme": "Creator Expert", "year_released": 2019, "description": "Scientist with lab coat and goggles", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/ce003.png"},
            
            # Technic Theme
            {"item_number": "tec001", "name": "Mechanic", "theme": "Technic", "year_released": 2020, "description": "Mechanic with overalls and wrench", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/tec001.png"},
            {"item_number": "tec002", "name": "Racer", "theme": "Technic", "year_released": 2021, "description": "Race Car Driver with helmet and suit", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/tec002.png"},
            
            # Duplo Theme
            {"item_number": "dup001", "name": "Duplo Child", "theme": "Duplo", "year_released": 2020, "description": "Duplo child figure with simple design", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/dup001.png"},
            {"item_number": "dup002", "name": "Duplo Parent", "theme": "Duplo", "year_released": 2020, "description": "Duplo parent figure with simple design", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/dup002.png"},
            
            # Classic Theme
            {"item_number": "cla001", "name": "Classic Figure", "theme": "Classic", "year_released": 2019, "description": "Classic LEGO figure with basic design", "rarity": "common", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cla001.png"},
            {"item_number": "cla002", "name": "Vintage Figure", "theme": "Classic", "year_released": 2015, "description": "Vintage LEGO figure with retro design", "rarity": "uncommon", "image_url": "https://img.bricklink.com/ItemImage/MN/0/cla002.png"},
        ]
    
    async def _process_minifigure(self, minifig_data: Dict[str, Any]):
        """Process and store a single minifigure"""
        try:
            # Extract basic info
            item_number = minifig_data.get('no', '')
            name = minifig_data.get('name', '')
            year_released = minifig_data.get('year_released')
            
            # Get detailed info
            details = await self._get_minifigure_details(item_number)
            
            # Create MinifigureData object
            minifig = MinifigureData(
                item_number=item_number,
                name=name,
                theme=details.get('theme', 'Unknown'),
                year_released=year_released,
                image_url=details.get('image_url', ''),
                image_path=None,  # No local image for now
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
                # Return basic info
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

# CLI interface for production database
async def main():
    """Command line interface for production database"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Production LEGO Minifigure Database Builder")
    parser.add_argument("command", choices=["build", "search", "stats"])
    parser.add_argument("--count", type=int, default=1000, help="Target number of minifigures")
    parser.add_argument("--query", type=str, help="Search query")
    
    args = parser.parse_args()
    
    builder = ProductionDatabaseBuilder()
    
    if args.command == "build":
        count = await builder.build_production_database(args.count)
        print(f"✅ Production database built with {count} minifigures")
        
    elif args.command == "search":
        if not args.query:
            print("Please provide --query")
            return
        results = builder.search_minifigures(args.query)
        for result in results:
            print(f"{result['item_number']}: {result['name']} ({result['theme']})")
            
    elif args.command == "stats":
        count = builder.get_minifigure_count()
        print(f"Production database contains {count} minifigures")

if __name__ == "__main__":
    asyncio.run(main())
