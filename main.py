#!/usr/bin/env python3
"""
Enhanced LEGO Valuation System - Main CLI Interface
Redmond's Forge Antique Shop

This is the enhanced main entry point for the LEGO valuation system with database-driven identification.
Use this script to run the web interface or perform command-line operations.
"""

import argparse
import asyncio
import sys
from pathlib import Path
from datetime import datetime

# Add src to path
sys.path.insert(0, str(Path(__file__).parent / "src"))

from config.settings import settings
from src.database.database import DatabaseManager
from src.database.models import ValuationRecord
from src.utils.image_processor import ImageProcessor
from src.core.lego_identifier import LegoIdentifier
from src.core.database_identifier import DatabaseDrivenIdentifier
from src.core.valuation_engine import ValuationEngine
from src.core.report_generator import ReportGenerator
from src.database.repository import ValuationRepository, InventoryRepository
from src.models.schemas import ValuationReport
from sqlalchemy import desc


class EnhancedLegoValuationCLI:
    """Enhanced CLI with database-driven identification and comprehensive features"""
    
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.repository = ValuationRepository(self.db_manager)
        self.image_processor = ImageProcessor()
        self.lego_identifier = LegoIdentifier()
        self.enhanced_identifier = DatabaseDrivenIdentifier()
        self.valuation_engine = ValuationEngine()
        self.report_generator = ReportGenerator()
        
    def initialize_system(self):
        """Initialize the enhanced system with database-driven identification"""
        print("🚀 Initializing Enhanced LEGO Valuation System...")
        
        # Create database tables
        self.db_manager.initialize_database()
        print("✓ Database initialized")
        
        # Check minifigure database
        stats = self.enhanced_identifier.get_database_stats()
        if stats['total_minifigures'] == 0:
            print("⚠️  Minifigure database is empty!")
            print("   Run: python setup_production_database.py build --count 1000")
            print("   to download minifigure data for improved accuracy")
        else:
            print(f"✓ Minifigure database ready ({stats['total_minifigures']} minifigures)")
        
        # Create required directories
        Path("data/uploads").mkdir(parents=True, exist_ok=True)
        Path("data/reports").mkdir(parents=True, exist_ok=True)
        print("✓ Directory structure created")
        
        print("🎉 Enhanced system initialization complete!")
    
    async def process_image(self, image_path: str, notes: str = "", use_enhanced: bool = True):
        """Process an image with enhanced database-driven identification"""
        print(f"Processing image: {image_path}")
        
        try:
            # Process and optimize image
            file_path, image_upload = self.image_processor.save_image(
                open(image_path, "rb").read(), Path(image_path).name
            )
            optimized_path = self.image_processor.optimize_image_for_ai(file_path)
            print("✓ Image processed and optimized")
            
            # Choose identification method
            if use_enhanced:
                print("🔍 Identifying LEGO items with enhanced database matching...")
                identification = await self.enhanced_identifier.identify_lego_items(optimized_path)
                print(f"✓ Enhanced identification complete (confidence: {identification.confidence_score:.2f})")
            else:
                print("🔍 Identifying LEGO items with standard AI...")
                identification = await self.lego_identifier.identify_lego_items(optimized_path)
                print(f"✓ Standard identification complete (confidence: {identification.confidence_score:.2f})")
            
            # Perform valuation
            print("💰 Performing valuation...")
            valuation = await self.valuation_engine.evaluate_item(identification)
            print(f"✓ Valuation complete: ${valuation.estimated_value:.2f}")
            
            # Create report
            report = ValuationReport(
                image_filename=Path(image_path).name,
                image_path=optimized_path,
                upload_timestamp=datetime.now(),
                identification=identification,
                valuation=valuation,
                notes=notes
            )
            
            # Save to database
            valuation_id = self.repository.save_valuation(report)
            print(f"✓ Saved to database (ID: {valuation_id})")
            
            # Generate reports
            pdf_path = self.report_generator.generate_pdf(report)
            html_path = self.report_generator.generate_html(report)
            
            # Display results
            self._display_results(report, pdf_path, html_path, use_enhanced)
            
        except Exception as e:
            print(f"❌ Error processing image: {e}")
            import traceback
            traceback.print_exc()
    
    def _display_results(self, report: ValuationReport, pdf_path: str, html_path: str, enhanced: bool = True):
        """Display valuation results"""
        method = "ENHANCED DATABASE-DRIVEN" if enhanced else "STANDARD AI"
        
        print("\n" + "=" * 60)
        print(f"{method} VALUATION RESULTS")
        print("=" * 60)
        print(f"Image: {report.image_filename}")
        print(f"Estimated Value: ${report.valuation.estimated_value:.2f}")
        print(f"Confidence: {report.valuation.confidence_score:.2f}")
        print(f"Recommendation: {report.valuation.recommendation.value}")
        print(f"Description: {report.identification.description}")
        print(f"Reasoning: {report.valuation.reasoning}")
        print()
        
        if report.identification.identified_items:
            print("Identified Items:")
            for i, item in enumerate(report.identification.identified_items, 1):
                print(f"  {i}. {item.name}")
                if item.item_number:
                    print(f"     Item Number: {item.item_number}")
                print(f"     Theme: {item.theme}")
                print(f"     Condition: {item.condition.value}")
                if item.year_released:
                    print(f"     Year: {item.year_released}")
                print()
        else:
            print("❌ No items identified")
        
        print("Suggested Platforms:")
        for platform in report.valuation.suggested_platforms:
            print(f"  - {platform.value}")
        
        print(f"\nReports generated:")
        print(f"  - PDF: {pdf_path}")
        print(f"  - HTML: {html_path}")
        print("=" * 60)
    
    def list_valuations(self, limit: int = 10):
        """List recent valuations"""
        valuations = self.repository.get_recent_valuations(limit)
        
        if not valuations:
            print("No valuations found")
            return
        
        print(f"Recent Valuations (showing {len(valuations)}):")
        print("-" * 80)
        
        for val in valuations:
            print(f"ID: {val.id:3d} | ${val.estimated_value:8.2f} | {val.recommendation_category:12s} | "
                  f"{val.upload_timestamp.strftime('%Y-%m-%d %H:%M')} | {val.image_filename}")
    
    def show_inventory_summary(self):
        """Show inventory summary"""
        summary = self.repository.get_inventory_summary()
        
        print("Inventory Summary:")
        print("-" * 40)
        print(f"Total Items: {summary['total_items']}")
        print(f"Total Value: ${summary['total_value']:.2f}")
        print(f"Average Value: ${summary['average_value']:.2f}")
        print(f"Highest Value: ${summary['highest_value']:.2f}")
        print(f"Recommendations:")
        print(f"  Museum: {summary['museum_count']}")
        print(f"  Resale: {summary['resale_count']}")
        print(f"  Collection: {summary['collection_count']}")
    
    def search_database(self, query: str, limit: int = 10):
        """Search the minifigure database"""
        results = self.enhanced_identifier.search_database(query, limit)
        
        if not results:
            print(f"No minifigures found matching '{query}'")
            return
        
        print(f"Minifigure Database Search Results for '{query}':")
        print("-" * 60)
        
        for result in results:
            print(f"{result['item_number']}: {result['name']}")
            print(f"  Theme: {result['theme']}")
            if result['year_released']:
                print(f"  Year: {result['year_released']}")
            print()
    
    def show_database_stats(self):
        """Show database statistics"""
        stats = self.enhanced_identifier.get_database_stats()
        
        print("Enhanced Database Statistics:")
        print("-" * 40)
        print(f"Total Minifigures: {stats['total_minifigures']}")
        if 'real_database_count' in stats:
            print(f"Real BrickLink Data: {stats.get('real_database_count', 0)}")
            print(f"Mock Data: {stats.get('mock_database_count', 0)}")
        print(f"Database Path: {stats['database_path']}")
        print(f"Images Directory: {stats['images_directory']}")
        
        # Check if images exist
        images_dir = Path(stats['images_directory'])
        if images_dir.exists():
            image_files = list(images_dir.glob("*.jpg")) + list(images_dir.glob("*.png"))
            print(f"Image Files: {len(image_files)}")
        else:
            print("Image Files: 0 (directory not found)")
    
    def setup_database(self, count: int = 1000):
        """Setup the minifigure database"""
        print(f"🚀 Setting up minifigure database with {count} minifigures...")
        print("This may take several minutes...")
        
        try:
            from src.core.production_database_builder import ProductionDatabaseBuilder
            builder = ProductionDatabaseBuilder()
            total_count = asyncio.run(builder.build_production_database(count))
            print(f"✅ Database setup complete: {total_count} minifigures")
        except Exception as e:
            print(f"❌ Error setting up database: {e}")
            print("Please run: python setup_production_database.py build --count 1000")


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(description="Enhanced LEGO Valuation System")
    subparsers = parser.add_subparsers(dest='command', help='Available commands')
    
    # Initialize command
    subparsers.add_parser('init', help='Initialize the enhanced system')
    
    # Process command
    process_parser = subparsers.add_parser('process', help='Process an image')
    process_parser.add_argument('image', help='Path to image file')
    process_parser.add_argument('--notes', default='', help='Notes about the image')
    process_parser.add_argument('--standard', action='store_true', help='Use standard AI instead of enhanced database')
    
    # List command
    list_parser = subparsers.add_parser('list', help='List recent valuations')
    list_parser.add_argument('--limit', type=int, default=10, help='Number of valuations to show')
    
    # Inventory command
    subparsers.add_parser('inventory', help='Show inventory summary')
    
    # Search command
    search_parser = subparsers.add_parser('search', help='Search minifigure database')
    search_parser.add_argument('query', help='Search query')
    search_parser.add_argument('--limit', type=int, default=10, help='Number of results to show')
    
    # Stats command
    subparsers.add_parser('stats', help='Show database statistics')
    
    # Setup command
    setup_parser = subparsers.add_parser('setup', help='Setup minifigure database')
    setup_parser.add_argument('--count', type=int, default=1000, help='Number of minifigures to download')
    
    # Web server command
    subparsers.add_parser('web', help='Start web server')
    
    args = parser.parse_args()
    
    if not args.command:
        parser.print_help()
        return
    
    cli = EnhancedLegoValuationCLI()
    
    if args.command == 'init':
        cli.initialize_system()
    elif args.command == 'process':
        use_enhanced = not args.standard
        asyncio.run(cli.process_image(args.image, args.notes, use_enhanced))
    elif args.command == 'list':
        cli.list_valuations(args.limit)
    elif args.command == 'inventory':
        cli.show_inventory_summary()
    elif args.command == 'search':
        cli.search_database(args.query, args.limit)
    elif args.command == 'stats':
        cli.show_database_stats()
    elif args.command == 'setup':
        cli.setup_database(args.count)
    elif args.command == 'web':
        print("Starting web server...")
        import uvicorn
        from src.api.main import app
        uvicorn.run(app, host="0.0.0.0", port=8000)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()