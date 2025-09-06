"""
Mock Database Builder for Testing
Creates a sample database with common minifigures for testing
"""

import sqlite3
from pathlib import Path
from typing import List, Dict, Any
from datetime import datetime
import logging

logger = logging.getLogger(__name__)

class MockDatabaseBuilder:
    """Creates a mock database with sample minifigures for testing"""
    
    def __init__(self, db_path: str = "data/minifigure_database.db"):
        self.db_path = db_path
        self.images_dir = Path("data/minifigure_images")
        self.images_dir.mkdir(parents=True, exist_ok=True)
        
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
                source TEXT DEFAULT 'mock',
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
        logger.info("Mock database initialized")
    
    def populate_sample_data(self):
        """Populate database with sample minifigures"""
        sample_minifigures = [
            {
                'item_number': 'cty001',
                'name': 'Police Officer',
                'theme': 'City',
                'year_released': 2020,
                'description': 'City Police Officer with blue uniform and cap',
                'rarity': 'common'
            },
            {
                'item_number': 'cty002', 
                'name': 'Construction Worker',
                'theme': 'City',
                'year_released': 2019,
                'description': 'Construction Worker with orange safety vest and hard hat',
                'rarity': 'common'
            },
            {
                'item_number': 'cty003',
                'name': 'Chef',
                'theme': 'City', 
                'year_released': 2021,
                'description': 'Chef with white uniform and chef hat',
                'rarity': 'common'
            },
            {
                'item_number': 'cty004',
                'name': 'Astronaut',
                'theme': 'City',
                'year_released': 2018,
                'description': 'Space Astronaut with white suit and helmet',
                'rarity': 'uncommon'
            },
            {
                'item_number': 'nin001',
                'name': 'Ninja Warrior',
                'theme': 'Ninjago',
                'year_released': 2020,
                'description': 'Ninja Warrior with katana and ninja outfit',
                'rarity': 'common'
            },
            {
                'item_number': 'sh001',
                'name': 'Spider-Man',
                'theme': 'Super Heroes',
                'year_released': 2019,
                'description': 'Spider-Man with red and blue suit',
                'rarity': 'rare'
            },
            {
                'item_number': 'sh002',
                'name': 'Batman',
                'theme': 'Super Heroes',
                'year_released': 2018,
                'description': 'Batman with black cape and cowl',
                'rarity': 'rare'
            },
            {
                'item_number': 'cas001',
                'name': 'Knight',
                'theme': 'Castle',
                'year_released': 2017,
                'description': 'Medieval Knight with armor and sword',
                'rarity': 'uncommon'
            },
            {
                'item_number': 'cas002',
                'name': 'Wizard',
                'theme': 'Castle',
                'year_released': 2016,
                'description': 'Wizard with robe and staff',
                'rarity': 'uncommon'
            },
            {
                'item_number': 'gen001',
                'name': 'Female Civilian',
                'theme': 'Generic',
                'year_released': 2020,
                'description': 'Generic female figure with casual clothes',
                'rarity': 'common'
            },
            {
                'item_number': 'gen002',
                'name': 'Male Civilian',
                'theme': 'Generic',
                'year_released': 2020,
                'description': 'Generic male figure with casual clothes',
                'rarity': 'common'
            },
            {
                'item_number': 'pir001',
                'name': 'Pirate Captain',
                'theme': 'Pirates',
                'year_released': 2015,
                'description': 'Pirate Captain with hat and sword',
                'rarity': 'uncommon'
            }
        ]
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        for minifig in sample_minifigures:
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
                    f"https://img.bricklink.com/ItemImage/MN/0/{minifig['item_number']}.png",
                    None,  # No local image for now
                    minifig['description'],
                    minifig['rarity'],
                    'mock',
                    datetime.now()
                ))
            except Exception as e:
                logger.error(f"Error inserting {minifig['item_number']}: {e}")
        
        conn.commit()
        conn.close()
        logger.info(f"Populated database with {len(sample_minifigures)} sample minifigures")
    
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

# CLI interface for mock database
def main():
    """Command line interface for mock database"""
    import argparse
    
    parser = argparse.ArgumentParser(description="Mock LEGO Minifigure Database Builder")
    parser.add_argument("command", choices=["init", "populate", "search", "stats"])
    parser.add_argument("--query", type=str, help="Search query")
    
    args = parser.parse_args()
    
    builder = MockDatabaseBuilder()
    
    if args.command == "init":
        builder.initialize_database()
        print("✓ Mock database initialized")
        
    elif args.command == "populate":
        builder.initialize_database()
        builder.populate_sample_data()
        print("✓ Mock database populated with sample data")
        
    elif args.command == "search":
        if not args.query:
            print("Please provide --query")
            return
        results = builder.search_minifigures(args.query)
        for result in results:
            print(f"{result['item_number']}: {result['name']} ({result['theme']})")
            
    elif args.command == "stats":
        count = builder.get_minifigure_count()
        print(f"Mock database contains {count} minifigures")

if __name__ == "__main__":
    main()
