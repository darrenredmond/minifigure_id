#!/usr/bin/env python3
"""
LEGO Valuation System - Main CLI Interface
Redmond's Forge Antique Shop

This is the main entry point for the LEGO valuation system.
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
from src.utils.image_processor import ImageProcessor
from src.core.lego_identifier import LegoIdentifier
from src.core.valuation_engine import ValuationEngine
from src.core.report_generator import ReportGenerator
from src.database.repository import ValuationRepository, InventoryRepository
from src.models.schemas import ValuationReport


class LegoValuationCLI:
    def __init__(self):
        self.db_manager = DatabaseManager()
        self.image_processor = ImageProcessor()
        self.lego_identifier = LegoIdentifier()
        self.valuation_engine = ValuationEngine()
        self.report_generator = ReportGenerator()
        
    def initialize_system(self):
        """Initialize the database and required directories"""
        print("Initializing LEGO Valuation System...")
        
        # Create database tables
        self.db_manager.initialize_database()
        print("✓ Database initialized")
        
        # Create required directories
        Path("data/uploads").mkdir(parents=True, exist_ok=True)
        Path("data/reports").mkdir(parents=True, exist_ok=True)
        print("✓ Directory structure created")
        
        print("System initialization complete!")
        
    async def process_image(self, image_path: str, notes: str = ""):
        """Process a single image and generate valuation report"""
        print(f"Processing image: {image_path}")
        
        try:
            # Validate and optimize image
            with open(image_path, 'rb') as f:
                file_content = f.read()
            
            file_path, image_upload = self.image_processor.save_image(
                file_content, Path(image_path).name
            )
            optimized_path = self.image_processor.optimize_image_for_ai(file_path)
            print("✓ Image processed and optimized")
            
            # Identify LEGO items
            print("🔍 Identifying LEGO items...")
            identification = await self.lego_identifier.identify_lego_items(optimized_path)
            print(f"✓ Identification complete (confidence: {identification.confidence_score:.2%})")
            
            # Perform valuation
            print("💰 Performing valuation...")
            valuation = await self.valuation_engine.evaluate_item(identification)
            print(f"✓ Valuation complete: ${valuation.estimated_value:.2f}")
            
            # Create report
            report = ValuationReport(
                image_filename=image_upload.filename,
                upload_timestamp=datetime.now(),
                identification=identification,
                valuation=valuation,
                notes=notes
            )
            
            # Save to database
            with self.db_manager.get_session() as db:
                repo = ValuationRepository(db)
                record = repo.create_valuation_record(report)
                print(f"✓ Saved to database (ID: {record.id})")
            
            # Generate reports
            pdf_path = self.report_generator.generate_pdf_report(report)
            html_path = self.report_generator.generate_html_report(report)
            
            print("\n" + "="*50)
            print("VALUATION RESULTS")
            print("="*50)
            print(f"Image: {image_path}")
            print(f"Estimated Value: ${valuation.estimated_value:.2f}")
            print(f"Confidence: {valuation.confidence_score:.2%}")
            print(f"Recommendation: {valuation.recommendation.value.title()}")
            print(f"Description: {identification.description}")
            print(f"Reasoning: {valuation.reasoning}")
            print("\nSuggested Platforms:")
            for platform in valuation.suggested_platforms:
                print(f"  - {platform.value.replace('_', ' ').title()}")
            print(f"\nReports generated:")
            print(f"  - PDF: {pdf_path}")
            print(f"  - HTML: {html_path}")
            print("="*50)
            
            return record.id
            
        except Exception as e:
            print(f"❌ Error processing image: {e}")
            return None
    
    def list_valuations(self, limit: int = 10):
        """List recent valuations"""
        with self.db_manager.get_session() as db:
            repo = ValuationRepository(db)
            records = repo.list_valuation_records(limit=limit)
            
            if not records:
                print("No valuations found.")
                return
            
            print(f"\nRecent Valuations (showing {len(records)}):")
            print("-" * 80)
            for record in records:
                created = record.created_at.strftime("%Y-%m-%d %H:%M")
                print(f"ID: {record.id:3d} | ${record.estimated_value:8.2f} | "
                      f"{record.recommendation_category:10s} | "
                      f"{created} | {record.image_filename}")
    
    def show_inventory_summary(self):
        """Show inventory summary"""
        with self.db_manager.get_session() as db:
            repo = InventoryRepository(db)
            summary = repo.get_inventory_summary()
            items = repo.list_inventory()[:10]  # Top 10
            
            print("\nInventory Summary:")
            print("-" * 40)
            print(f"Total Items: {summary['total_items']}")
            print(f"Total Value: ${summary['total_estimated_value']:.2f}")
            
            if summary['items_by_status']:
                print("\nBy Status:")
                for status, count in summary['items_by_status'].items():
                    print(f"  {status}: {count}")
            
            if items:
                print(f"\nTop Items by Value:")
                print("-" * 60)
                for item in items:
                    print(f"${item.estimated_value:8.2f} | {item.item_name[:40]}")
    
    def run_web_server(self):
        """Start the web server"""
        import uvicorn
        print("Starting LEGO Valuation System Web Server...")
        print("Access the system at: http://localhost:8000")
        print("API documentation at: http://localhost:8000/docs")
        
        uvicorn.run(
            "src.api.main:app",
            host="0.0.0.0",
            port=8000,
            reload=settings.debug
        )


def main():
    """Main CLI interface"""
    parser = argparse.ArgumentParser(
        description="LEGO Valuation System for Redmond's Forge",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  python main.py init                           # Initialize system
  python main.py process image.jpg              # Process single image
  python main.py process image.jpg --notes "Found in estate sale"
  python main.py list                           # List recent valuations
  python main.py inventory                      # Show inventory summary
  python main.py server                         # Start web server
        """
    )
    
    parser.add_argument(
        'command',
        choices=['init', 'process', 'list', 'inventory', 'server'],
        help='Command to execute'
    )
    
    parser.add_argument(
        'image_path',
        nargs='?',
        help='Path to image file (for process command)'
    )
    
    parser.add_argument(
        '--notes',
        default="",
        help='Additional notes about the item'
    )
    
    parser.add_argument(
        '--limit',
        type=int,
        default=10,
        help='Limit for list commands'
    )
    
    args = parser.parse_args()
    
    cli = LegoValuationCLI()
    
    if args.command == 'init':
        cli.initialize_system()
    
    elif args.command == 'process':
        if not args.image_path:
            print("Error: Image path required for process command")
            sys.exit(1)
        
        if not Path(args.image_path).exists():
            print(f"Error: Image file not found: {args.image_path}")
            sys.exit(1)
        
        asyncio.run(cli.process_image(args.image_path, args.notes))
    
    elif args.command == 'list':
        cli.list_valuations(args.limit)
    
    elif args.command == 'inventory':
        cli.show_inventory_summary()
    
    elif args.command == 'server':
        cli.run_web_server()


if __name__ == "__main__":
    main()