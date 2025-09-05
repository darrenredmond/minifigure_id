from fastapi import FastAPI, File, UploadFile, Depends, HTTPException, BackgroundTasks
from fastapi.responses import HTMLResponse, FileResponse
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from sqlalchemy.orm import Session
from typing import List, Optional
from pathlib import Path
import asyncio
from datetime import datetime

from config.settings import settings
from src.database.database import get_db, create_tables
from src.database.repository import ValuationRepository, InventoryRepository
from src.utils.image_processor import ImageProcessor
from src.core.lego_identifier import LegoIdentifier
from src.core.valuation_engine import ValuationEngine
from src.core.report_generator import ReportGenerator
from src.models.schemas import ValuationReport, IdentificationResult, ValuationResult

# Initialize FastAPI app
app = FastAPI(
    title="LEGO Valuation System",
    description="AI-powered LEGO minifigure and set valuation system for Redmond's Forge",
    version="1.0.0",
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Configure appropriately for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize components
image_processor = ImageProcessor()
lego_identifier = LegoIdentifier()
valuation_engine = ValuationEngine()
report_generator = ReportGenerator()


# Create database tables on startup
@app.on_event("startup")
async def startup_event():
    create_tables()


# Serve static files
app.mount("/static", StaticFiles(directory="src/web/static"), name="static")


@app.get("/", response_class=HTMLResponse)
async def root():
    """Main page with upload form"""
    return """
    <!DOCTYPE html>
    <html>
    <head>
        <title>LEGO Valuation System</title>
        <style>
            body { 
                font-family: Arial, sans-serif; 
                max-width: 800px; 
                margin: 0 auto; 
                padding: 20px; 
                background-color: #f8f9fa;
            }
            .header { 
                text-align: center; 
                color: #2c3e50; 
                margin-bottom: 30px;
            }
            .upload-form { 
                background: white; 
                padding: 30px; 
                border-radius: 10px; 
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
                margin-bottom: 20px;
            }
            .form-group { 
                margin-bottom: 20px; 
            }
            label { 
                display: block; 
                margin-bottom: 5px; 
                font-weight: bold;
            }
            input[type="file"] { 
                width: 100%; 
                padding: 10px; 
                border: 2px dashed #3498db; 
                border-radius: 5px;
                background-color: #ecf0f1;
            }
            textarea {
                width: 100%;
                padding: 10px;
                border: 1px solid #bdc3c7;
                border-radius: 5px;
                resize: vertical;
                min-height: 80px;
            }
            button { 
                background-color: #3498db; 
                color: white; 
                padding: 12px 25px; 
                border: none; 
                border-radius: 5px; 
                cursor: pointer; 
                font-size: 16px;
            }
            button:hover { 
                background-color: #2980b9; 
            }
            .features {
                background: white;
                padding: 20px;
                border-radius: 10px;
                box-shadow: 0 2px 10px rgba(0,0,0,0.1);
            }
            .feature-grid {
                display: grid;
                grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
                gap: 15px;
                margin-top: 15px;
            }
            .feature {
                padding: 15px;
                background-color: #ecf0f1;
                border-radius: 5px;
                text-align: center;
            }
            .api-links {
                margin-top: 30px;
                text-align: center;
            }
            .api-links a {
                display: inline-block;
                margin: 5px 10px;
                padding: 8px 16px;
                background-color: #27ae60;
                color: white;
                text-decoration: none;
                border-radius: 5px;
            }
        </style>
    </head>
    <body>
        <div class="header">
            <h1>🧱 LEGO Valuation System</h1>
            <h2>Redmond's Forge Antique Shop</h2>
            <p>AI-powered identification and valuation of LEGO minifigures and sets</p>
        </div>
        
        <div class="upload-form">
            <h3>Upload LEGO Item Image</h3>
            <form action="/upload" method="post" enctype="multipart/form-data">
                <div class="form-group">
                    <label for="file">Select Image:</label>
                    <input type="file" name="file" id="file" accept="image/*" required>
                    <small>Supported formats: JPG, PNG, WebP (max 10MB)</small>
                </div>
                <div class="form-group">
                    <label for="notes">Additional Notes (optional):</label>
                    <textarea name="notes" id="notes" placeholder="Any additional information about the item..."></textarea>
                </div>
                <button type="submit">Analyze & Value Item</button>
            </form>
        </div>
        
        <div class="features">
            <h3>System Features</h3>
            <div class="feature-grid">
                <div class="feature">
                    <h4>🔍 AI Identification</h4>
                    <p>Uses Claude Vision to identify LEGO items</p>
                </div>
                <div class="feature">
                    <h4>💰 Market Valuation</h4>
                    <p>Cross-references with BrickLink for current prices</p>
                </div>
                <div class="feature">
                    <h4>🏛️ Museum vs Resale</h4>
                    <p>Recommends whether items should be preserved or sold</p>
                </div>
                <div class="feature">
                    <h4>📊 Detailed Reports</h4>
                    <p>Generates professional PDF and HTML reports</p>
                </div>
                <div class="feature">
                    <h4>📦 Inventory Tracking</h4>
                    <p>Maintains database of all valued items</p>
                </div>
                <div class="feature">
                    <h4>🛒 Platform Recommendations</h4>
                    <p>Suggests best resale platforms for each item</p>
                </div>
            </div>
        </div>
        
        <div class="api-links">
            <h3>Quick Links</h3>
            <a href="/valuations">View All Valuations</a>
            <a href="/inventory">Inventory Summary</a>
            <a href="/docs">API Documentation</a>
        </div>
    </body>
    </html>
    """


@app.post("/upload")
async def upload_image(
    background_tasks: BackgroundTasks,
    file: UploadFile = File(...),
    notes: Optional[str] = None,
    db: Session = Depends(get_db),
):
    """Upload and process an image for valuation"""
    try:
        # Read file content
        file_content = await file.read()

        # Process image
        file_path, image_upload = image_processor.save_image(
            file_content, file.filename
        )
        optimized_path = image_processor.optimize_image_for_ai(file_path)

        # Start processing in background
        background_tasks.add_task(
            process_image_valuation, optimized_path, image_upload.filename, notes, db
        )

        return {
            "message": "Image uploaded successfully. Processing valuation...",
            "filename": image_upload.filename,
            "status": "processing",
        }

    except ValueError as e:
        raise HTTPException(status_code=400, detail=str(e))
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Upload failed: {str(e)}")


async def process_image_valuation(
    image_path: str, filename: str, notes: Optional[str], db: Session
):
    """Background task to process image valuation"""
    try:
        # Identify LEGO items
        identification = await lego_identifier.identify_lego_items(image_path)

        # Perform valuation
        valuation = await valuation_engine.evaluate_item(identification)

        # Create report
        report = ValuationReport(
            image_filename=filename,
            upload_timestamp=datetime.now(),
            identification=identification,
            valuation=valuation,
            notes=notes,
        )

        # Save to database
        repo = ValuationRepository(db)
        repo.create_valuation_record(report)

        # Generate PDF report
        report_generator.generate_pdf_report(report)

        print(f"Valuation completed for {filename}: ${valuation.estimated_value:.2f}")

    except Exception as e:
        print(f"Error processing valuation for {filename}: {e}")


@app.get("/valuations")
async def list_valuations(
    skip: int = 0, limit: int = 20, db: Session = Depends(get_db)
):
    """List all valuation records"""
    repo = ValuationRepository(db)
    records = repo.list_valuation_records(skip=skip, limit=limit)

    # Convert to JSON-serializable format
    results = []
    for record in records:
        results.append(
            {
                "id": record.id,
                "image_filename": record.image_filename,
                "estimated_value": record.estimated_value,
                "recommendation": record.recommendation_category,
                "confidence_score": record.confidence_score,
                "created_at": record.created_at,
            }
        )

    return {"valuations": results, "total": len(results)}


@app.get("/valuations/{valuation_id}")
async def get_valuation_detail(valuation_id: int, db: Session = Depends(get_db)):
    """Get detailed valuation information"""
    repo = ValuationRepository(db)
    record = repo.get_valuation_record(valuation_id)

    if not record:
        raise HTTPException(status_code=404, detail="Valuation not found")

    return {
        "id": record.id,
        "image_filename": record.image_filename,
        "upload_timestamp": record.upload_timestamp,
        "identification": record.identification_data,
        "estimated_value": record.estimated_value,
        "confidence_score": record.valuation_confidence,
        "recommendation": record.recommendation_category,
        "reasoning": record.reasoning,
        "suggested_platforms": record.suggested_platforms,
        "market_data": record.market_data,
        "notes": record.notes,
        "created_at": record.created_at,
    }


@app.get("/inventory")
async def inventory_summary(db: Session = Depends(get_db)):
    """Get inventory summary"""
    repo = InventoryRepository(db)
    items = repo.list_inventory()
    summary = repo.get_inventory_summary()

    return {
        "summary": summary,
        "recent_items": [
            {
                "id": item.id,
                "item_name": item.item_name,
                "item_type": item.item_type,
                "estimated_value": item.estimated_value,
                "status": item.status,
                "location": item.location,
            }
            for item in items[:10]  # Show first 10 items
        ],
    }


@app.post("/inventory/add/{valuation_id}")
async def add_to_inventory(
    valuation_id: int, location: str = "", db: Session = Depends(get_db)
):
    """Add a valuation to inventory"""
    val_repo = ValuationRepository(db)
    inv_repo = InventoryRepository(db)

    valuation_record = val_repo.get_valuation_record(valuation_id)
    if not valuation_record:
        raise HTTPException(status_code=404, detail="Valuation not found")

    inventory_item = inv_repo.create_from_valuation(valuation_record, location)

    return {
        "message": "Item added to inventory",
        "inventory_id": inventory_item.id,
        "item_name": inventory_item.item_name,
    }


@app.get("/reports/generate/{valuation_id}")
async def generate_report(
    valuation_id: int, format: str = "pdf", db: Session = Depends(get_db)
):
    """Generate a report for a specific valuation"""
    repo = ValuationRepository(db)
    record = repo.get_valuation_record(valuation_id)

    if not record:
        raise HTTPException(status_code=404, detail="Valuation not found")

    # Reconstruct ValuationReport from database record
    # This is a simplified reconstruction - in practice you'd want more robust serialization
    try:
        if format.lower() == "pdf":
            # For now, return a simple response - full implementation would reconstruct the report
            return {
                "message": "PDF generation requires full report reconstruction",
                "status": "not_implemented",
            }
        else:
            return {
                "message": "HTML generation requires full report reconstruction",
                "status": "not_implemented",
            }
    except Exception as e:
        raise HTTPException(
            status_code=500, detail=f"Report generation failed: {str(e)}"
        )


@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {"status": "healthy", "timestamp": datetime.now(), "version": "1.0.0"}


if __name__ == "__main__":
    import uvicorn

    uvicorn.run("src.api.main:app", host="0.0.0.0", port=8000, reload=settings.debug)
