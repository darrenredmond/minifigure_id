#!/usr/bin/env python3
"""
Production Database Setup Script
Builds a comprehensive minifigure database with 1000+ minifigures for production use
"""

import asyncio
import argparse
import sys
from pathlib import Path

# Add src to path
sys.path.append(str(Path(__file__).parent / "src"))

from src.core.production_database_builder import ProductionDatabaseBuilder
from src.core.database_identifier import DatabaseDrivenIdentifier

async def setup_production_database(count: int = 1000):
    """Setup the production minifigure database"""
    print("🚀 Setting up Production LEGO Minifigure Database...")
    print("=" * 60)
    
    builder = ProductionDatabaseBuilder()
    
    # Build the comprehensive database
    total_count = await builder.build_production_database(count)
    
    print(f"\n✅ Production database setup complete!")
    print(f"📊 Total minifigures: {total_count}")
    
    # Test the enhanced identifier
    print("\n🧪 Testing enhanced identification...")
    identifier = DatabaseDrivenIdentifier()
    stats = identifier.get_database_stats()
    
    print(f"📈 Database Statistics:")
    print(f"  Total minifigures: {stats['total_minifigures']}")
    print(f"  Real BrickLink data: {stats.get('real_database_count', 0)}")
    print(f"  Mock data: {stats.get('mock_database_count', 0)}")
    print(f"  Database path: {stats['database_path']}")
    
    print(f"\n🎯 Ready for production use!")
    print(f"   - Enhanced accuracy with {total_count} minifigures")
    print(f"   - Comprehensive theme coverage")
    print(f"   - Fast local search and matching")
    print(f"   - Fallback to AI when needed")

def search_database(query: str, limit: int = 10):
    """Search the production database"""
    print(f"🔍 Searching production database for: {query}")
    print("=" * 50)
    
    builder = ProductionDatabaseBuilder()
    results = builder.search_minifigures(query, limit)
    
    if results:
        print(f"Found {len(results)} results:")
        for result in results:
            print(f"  {result['item_number']}: {result['name']} ({result['theme']})")
            if result['year_released']:
                print(f"    Year: {result['year_released']}")
            print()
    else:
        print("❌ No results found")

def show_stats():
    """Show production database statistics"""
    print("📊 Production Database Statistics")
    print("=" * 50)
    
    builder = ProductionDatabaseBuilder()
    count = builder.get_minifigure_count()
    
    print(f"Total minifigures: {count}")
    print(f"Database path: {builder.db_path}")
    print(f"Images directory: {builder.images_dir}")
    
    # Check if images directory exists and count files
    if builder.images_dir.exists():
        image_files = list(builder.images_dir.glob("*.jpg")) + list(builder.images_dir.glob("*.png"))
        print(f"Image files: {len(image_files)}")
    else:
        print("Images directory: Not found")

def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Production LEGO Minifigure Database Setup")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Build command
    build_parser = subparsers.add_parser('build', help='Build production database')
    build_parser.add_argument('--count', type=int, default=1000, help='Target number of minifigures (default: 1000)')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search the database')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Number of results to return')
    
    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')
    
    args = parser.parse_args()
    
    if args.command == 'build':
        asyncio.run(setup_production_database(args.count))
    elif args.command == 'search':
        search_database(args.query, args.limit)
    elif args.command == 'stats':
        show_stats()
    else:
        parser.print_help()

if __name__ == "__main__":
    main()
