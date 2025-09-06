import os
import json
import uuid
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import tempfile

from src.utils.minifigure_images import MinifigureImageService

try:
    from reportlab.lib.pagesizes import letter, A4
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle, Image as RLImage, PageBreak
    from reportlab.lib.units import inch
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False

try:
    from PIL import Image
    PIL_AVAILABLE = True
except ImportError:
    PIL_AVAILABLE = False

from src.models.schemas import ValuationReport, RecommendationCategory, LegoItem


class ReportGenerator:
    """Generate reports in various formats (JSON, HTML, PDF, Markdown)"""
    
    def __init__(self, output_dir: str = None):
        if output_dir:
            self.output_dir = Path(output_dir)
        else:
            self.output_dir = Path("data/reports")
        
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        # Initialize minifigure image service
        self.image_service = MinifigureImageService()

    def generate_json(self, report: ValuationReport) -> str:
        """Generate comprehensive JSON report with detailed pricing"""
        # Create unique filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"valuation_report_{timestamp}_{unique_id}.json"
        file_path = self.output_dir / filename

        # Prepare data
        data = {
            "report_id": unique_id,
            "timestamp": report.upload_timestamp.isoformat() if report.upload_timestamp else datetime.now().isoformat(),
            "image_filename": report.image_filename,
            "image_path": report.image_path,
            "estimated_value_usd": report.valuation.estimated_value,
            "estimated_value_eur": report.valuation.estimated_value_eur,
            "confidence_score": report.valuation.confidence_score,
            "recommendation": report.valuation.recommendation.value,
            "reasoning": report.valuation.reasoning,
            "suggested_platforms": [p.value for p in report.valuation.suggested_platforms],
            "exchange_rate_usd_eur": report.valuation.exchange_rate_usd_eur,
            "identification": {
                "confidence_score": report.identification.confidence_score,
                "description": report.identification.description,
                "condition_assessment": report.identification.condition_assessment
            },
            "identified_items": [
                {
                    "item_number": item.item_number,
                    "name": item.name,
                    "item_type": item.item_type.value if item.item_type else None,
                    "condition": item.condition.value if item.condition else None,
                    "year_released": item.year_released,
                    "theme": item.theme,
                    "category": item.category,
                    "pieces": item.pieces
                }
                for item in report.identification.identified_items
            ],
            "individual_valuations": [
                {
                    "item": {
                        "item_number": val.item.item_number,
                        "name": val.item.name,
                        "item_type": val.item.item_type.value if val.item.item_type else None,
                        "condition": val.item.condition.value if val.item.condition else None,
                        "year_released": val.item.year_released,
                        "theme": val.item.theme,
                        "category": val.item.category,
                        "pieces": val.item.pieces
                    },
                    "detailed_pricing": val.detailed_pricing.model_dump() if val.detailed_pricing else None,
                    "estimated_individual_value_usd": val.estimated_individual_value_usd,
                    "estimated_individual_value_eur": val.estimated_individual_value_eur,
                    "confidence_score": val.confidence_score,
                    "market_data": val.market_data.model_dump() if val.market_data else None,
                    "notes": val.notes
                }
                for val in report.valuation.individual_valuations
            ],
            "market_data": report.valuation.market_data.model_dump() if report.valuation.market_data else None
        }

        # Include base64 encoded image if available
        if report.image_path and os.path.exists(report.image_path):
            try:
                import base64
                with open(report.image_path, 'rb') as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    data["image_base64"] = img_data
                    data["image_mime_type"] = "image/jpeg"  # Assume JPEG for simplicity
            except Exception as e:
                print(f"Could not encode image for JSON: {e}")

        # Write JSON file
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

        return str(file_path)

    def generate_html(self, report: ValuationReport) -> str:
        """Generate HTML report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"valuation_report_{timestamp}_{unique_id}.html"
        file_path = self.output_dir / filename

        # Generate HTML content
        html_content = self._generate_html_content(report)

        # Write HTML file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(html_content)

        return str(file_path)

    def generate_pdf(self, report: ValuationReport) -> str:
        """Generate comprehensive PDF report with detailed pricing and image"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"valuation_report_{timestamp}_{unique_id}.pdf"
        file_path = self.output_dir / filename

        # Create PDF using SimpleDocTemplate for better layout control
        doc = SimpleDocTemplate(str(file_path), pagesize=A4)
        styles = getSampleStyleSheet()
        story = []

        # Title
        title_style = ParagraphStyle(
            'CustomTitle',
            parent=styles['Heading1'],
            fontSize=24,
            spaceAfter=30,
            textColor=colors.HexColor('#2c5aa0'),
            alignment=1  # Center alignment
        )
        story.append(Paragraph("LEGO Valuation Report", title_style))

        # Include original image if available
        if report.image_path and os.path.exists(report.image_path):
            try:
                # Add introduction heading
                intro_style = ParagraphStyle(
                    'IntroStyle',
                    parent=styles['Heading2'],
                    fontSize=16,
                    spaceAfter=10,
                    textColor=colors.HexColor('#2c5aa0'),
                    alignment=1
                )
                story.append(Paragraph("Original Image", intro_style))
                
                # Resize image to fit nicely in report with better proportions
                img = RLImage(report.image_path)
                # Calculate aspect ratio to maintain proportions
                try:
                    from PIL import Image
                    pil_img = Image.open(report.image_path)
                    aspect_ratio = pil_img.width / pil_img.height
                    
                    # Set max dimensions
                    max_width = 5*inch
                    max_height = 3.5*inch
                    
                    if aspect_ratio > 1:  # Landscape
                        img.drawWidth = max_width
                        img.drawHeight = max_width / aspect_ratio
                    else:  # Portrait or square
                        img.drawHeight = max_height
                        img.drawWidth = max_height * aspect_ratio
                        
                except ImportError:
                    # Fallback if PIL not available
                    img.drawHeight = 3*inch
                    img.drawWidth = 4*inch
                
                story.append(img)
                story.append(Spacer(1, 30))
            except Exception as e:
                print(f"Could not include image in PDF: {e}")

        # Report metadata
        metadata_data = [
            ["Date:", report.upload_timestamp.strftime('%Y-%m-%d %H:%M') if report.upload_timestamp else datetime.now().strftime('%Y-%m-%d %H:%M')],
            ["Image File:", report.image_filename],
            ["Identification Confidence:", self._format_percentage(report.identification.confidence_score)],
            ["Valuation Confidence:", self._format_percentage(report.valuation.confidence_score)]
        ]
        
        metadata_table = Table(metadata_data, colWidths=[2*inch, 4*inch])
        metadata_table.setStyle(TableStyle([
            ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
            ('TEXTCOLOR', (0, 0), (-1, -1), colors.black),
            ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
            ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
            ('FONTSIZE', (0, 0), (-1, -1), 10),
            ('BOTTOMPADDING', (0, 0), (-1, -1), 6),
            ('GRID', (0, 0), (-1, -1), 1, colors.black)
        ]))
        story.append(metadata_table)
        story.append(Spacer(1, 20))

        # Valuation Summary
        story.append(Paragraph("Valuation Summary", styles['Heading2']))
        
        # Total valuation in prominent display
        total_usd = self._format_currency(report.valuation.estimated_value)
        total_eur = ""
        if report.valuation.estimated_value_eur:
            total_eur = f" / €{report.valuation.estimated_value_eur:,.2f}"
        
        valuation_style = ParagraphStyle(
            'ValuationStyle',
            parent=styles['Normal'],
            fontSize=18,
            textColor=colors.HexColor('#2c5aa0'),
            alignment=1,
            spaceAfter=10
        )
        story.append(Paragraph(f"<b>{total_usd}{total_eur}</b>", valuation_style))
        
        story.append(Paragraph(f"<b>Recommendation:</b> {report.valuation.recommendation.value.title()}", styles['Normal']))
        story.append(Paragraph(f"<b>Reasoning:</b> {report.valuation.reasoning}", styles['Normal']))
        story.append(Spacer(1, 20))

        # Individual Item Valuations
        if report.valuation.individual_valuations:
            story.append(Paragraph("Individual Item Valuations", styles['Heading2']))
            
            for i, item_val in enumerate(report.valuation.individual_valuations):
                story.append(Paragraph(f"Item {i+1}: {item_val.item.name or 'Unknown'}", styles['Heading3']))
                
                # Item details table
                item_data = [
                    ["Item Number:", item_val.item.item_number or "N/A"],
                    ["Type:", item_val.item.item_type.value if item_val.item.item_type else "N/A"],
                    ["Condition:", item_val.item.condition.value if item_val.item.condition else "N/A"],
                    ["Theme:", item_val.item.theme or "N/A"],
                    ["Year Released:", str(item_val.item.year_released) if item_val.item.year_released else "N/A"],
                    ["Pieces:", str(item_val.item.pieces) if item_val.item.pieces else "N/A"]
                ]
                
                item_table = Table(item_data, colWidths=[1.5*inch, 3*inch])
                item_table.setStyle(TableStyle([
                    ('BACKGROUND', (0, 0), (0, -1), colors.lightgrey),
                    ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
                    ('FONTNAME', (0, 0), (0, -1), 'Helvetica-Bold'),
                    ('FONTSIZE', (0, 0), (-1, -1), 9),
                    ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                    ('GRID', (0, 0), (-1, -1), 1, colors.black)
                ]))
                story.append(item_table)
                story.append(Spacer(1, 10))
                
                # Detailed pricing table if available
                if item_val.detailed_pricing:
                    pricing = item_val.detailed_pricing
                    story.append(Paragraph("Detailed Pricing", styles['Heading4']))
                    
                    pricing_data = [
                        ["Condition", "USD", "EUR"],
                        ["MSRP", self._format_currency(pricing.msrp_usd) if pricing.msrp_usd else "N/A", 
                         f"€{pricing.msrp_eur:,.2f}" if pricing.msrp_eur else "N/A"],
                        ["Sealed/New", self._format_currency(pricing.sealed_new_usd) if pricing.sealed_new_usd else "N/A",
                         f"€{pricing.sealed_new_eur:,.2f}" if pricing.sealed_new_eur else "N/A"],
                        ["Used Complete", self._format_currency(pricing.used_complete_usd) if pricing.used_complete_usd else "N/A",
                         f"€{pricing.used_complete_eur:,.2f}" if pricing.used_complete_eur else "N/A"],
                        ["Used Incomplete", self._format_currency(pricing.used_incomplete_usd) if pricing.used_incomplete_usd else "N/A",
                         f"€{pricing.used_incomplete_eur:,.2f}" if pricing.used_incomplete_eur else "N/A"],
                        ["Missing Instructions", self._format_currency(pricing.missing_instructions_usd) if pricing.missing_instructions_usd else "N/A",
                         f"€{pricing.missing_instructions_eur:,.2f}" if pricing.missing_instructions_eur else "N/A"],
                        ["Missing Box", self._format_currency(pricing.missing_box_usd) if pricing.missing_box_usd else "N/A",
                         f"€{pricing.missing_box_eur:,.2f}" if pricing.missing_box_eur else "N/A"]
                    ]
                    
                    pricing_table = Table(pricing_data, colWidths=[2*inch, 1.5*inch, 1.5*inch])
                    pricing_table.setStyle(TableStyle([
                        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
                        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
                        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
                        ('FONTSIZE', (0, 0), (-1, -1), 9),
                        ('BOTTOMPADDING', (0, 0), (-1, -1), 4),
                        ('GRID', (0, 0), (-1, -1), 1, colors.black)
                    ]))
                    story.append(pricing_table)
                    story.append(Spacer(1, 15))
                
                if i < len(report.valuation.individual_valuations) - 1:
                    story.append(PageBreak())
        
        # Exchange rate info
        if report.valuation.exchange_rate_usd_eur:
            story.append(Paragraph(f"<i>Exchange rate used: 1 USD = {report.valuation.exchange_rate_usd_eur:.4f} EUR</i>", styles['Normal']))

        # Build PDF
        doc.build(story)
        return str(file_path)

    def generate_markdown(self, report: ValuationReport) -> str:
        """Generate Markdown report"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"valuation_report_{timestamp}_{unique_id}.md"
        file_path = self.output_dir / filename

        # Generate Markdown content
        md_content = self._generate_markdown_content(report)

        # Write Markdown file
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(md_content)

        return str(file_path)

    def generate_all_formats(self, report: ValuationReport) -> Dict[str, str]:
        """Generate reports in all available formats"""
        results = {}
        
        results['json'] = self.generate_json(report)
        results['html'] = self.generate_html(report)
        results['markdown'] = self.generate_markdown(report)
        
        try:
            results['pdf'] = self.generate_pdf(report)
        except ImportError as e:
            results['pdf_error'] = str(e)
        
        return results

    def _format_currency(self, amount: float) -> str:
        """Format currency value"""
        return f"${amount:,.2f}"

    def _format_percentage(self, value: float) -> str:
        """Format percentage value"""
        return f"{value * 100:.1f}%"

    def _get_recommendation_color(self, recommendation: RecommendationCategory) -> str:
        """Get color for recommendation category"""
        color_map = {
            RecommendationCategory.MUSEUM: "#FFD700",  # Gold
            RecommendationCategory.RESALE: "#00FF00",   # Green
            RecommendationCategory.COLLECTION: "#87CEEB" # Sky Blue
        }
        return color_map.get(recommendation, "#CCCCCC")

    def _generate_summary_statistics(self, items: List[LegoItem]) -> Dict[str, int]:
        """Generate summary statistics for items"""
        stats = {
            "total_items": len(items),
            "minifigures": 0,
            "sets": 0,
            "parts": 0,
            "new_items": 0,
            "used_items": 0
        }
        
        for item in items:
            # Count by type
            if item.item_type and "minifigure" in item.item_type.value.lower():
                stats["minifigures"] += 1
            elif item.item_type and "set" in item.item_type.value.lower():
                stats["sets"] += 1
            else:
                stats["parts"] += 1
            
            # Count by condition
            if item.condition and "new" in item.condition.value.lower():
                stats["new_items"] += 1
            else:
                stats["used_items"] += 1
        
        return stats

    def _generate_html_content(self, report: ValuationReport) -> str:
        """Generate comprehensive HTML content for report with detailed pricing and image"""
        recommendation_color = self._get_recommendation_color(report.valuation.recommendation)
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LEGO Valuation Report</title>
    <style>
        body {{ font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; margin: 20px; line-height: 1.6; background-color: #f9f9f9; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 30px; border-radius: 10px; box-shadow: 0 4px 6px rgba(0,0,0,0.1); }}
        .header {{ background: linear-gradient(135deg, #2c5aa0, #3a7bd5); color: white; padding: 30px; border-radius: 10px; text-align: center; }}
        .header h1 {{ margin: 0; font-size: 2.5em; }}
        .recommendation {{ background-color: {recommendation_color}; color: #333; padding: 15px; border-radius: 8px; margin: 20px 0; text-align: center; }}
        .value {{ font-size: 3em; color: #2c5aa0; font-weight: bold; text-align: center; margin: 20px 0; }}
        .euro-value {{ font-size: 2em; color: #666; }}
        table {{ border-collapse: collapse; width: 100%; margin: 20px 0; }}
        th, td {{ border: 1px solid #ddd; padding: 12px; text-align: left; }}
        th {{ background-color: #2c5aa0; color: white; font-weight: bold; }}
        tr:nth-child(even) {{ background-color: #f2f2f2; }}
        .pricing-table {{ margin: 20px 0; }}
        .pricing-table th {{ background-color: #34495e; }}
        .item-section {{ background: #f8f9fa; padding: 20px; margin: 20px 0; border-radius: 8px; border-left: 4px solid #2c5aa0; }}
        .introduction-section {{ margin: 30px 0; }}
        .original-image {{ text-align: center; margin: 20px 0; }}
        .original-image h2 {{ color: #2c5aa0; margin-bottom: 20px; }}
        .original-image img {{ max-width: 100%; max-height: 400px; height: auto; border-radius: 8px; box-shadow: 0 4px 8px rgba(0,0,0,0.2); }}
        .minifigure-image {{ text-align: center; margin: 15px 0; }}
        .minifigure-image img {{ max-width: 150px; max-height: 150px; height: auto; border-radius: 6px; box-shadow: 0 2px 4px rgba(0,0,0,0.1); border: 2px solid #e0e0e0; }}
        .metadata {{ background: #ecf0f1; padding: 15px; border-radius: 8px; margin: 20px 0; }}
        .exchange-rate {{ font-style: italic; color: #666; margin-top: 20px; text-align: center; }}
    </style>
</head>
<body>
    <div class="container">
        <div class="header">
            <h1>LEGO Valuation Report</h1>
            <p><strong>Date:</strong> {report.upload_timestamp.strftime('%Y-%m-%d %H:%M') if report.upload_timestamp else datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
            <p><strong>Image:</strong> {report.image_filename}</p>
        </div>

        <!-- Introduction Section with Original Image -->
        <div class="introduction-section">'''

        # Include original image if available
        if report.image_path and os.path.exists(report.image_path):
            try:
                import base64
                with open(report.image_path, 'rb') as img_file:
                    img_data = base64.b64encode(img_file.read()).decode('utf-8')
                    html += f'''
            <div class="original-image">
                <h2>Original Image</h2>
                <img src="data:image/jpeg;base64,{img_data}" alt="Original LEGO Collection Image" />
            </div>'''
            except Exception as e:
                print(f"Could not include image in HTML: {e}")
        
        html += '''
        </div>'''

        # Valuation summary with both currencies
        total_usd = self._format_currency(report.valuation.estimated_value)
        eur_display = ""
        if report.valuation.estimated_value_eur:
            eur_display = f'<div class="euro-value">€{report.valuation.estimated_value_eur:,.2f}</div>'

        html += f'''
        <h2>Valuation Summary</h2>
        <div class="value">{total_usd}</div>
        {eur_display}
        <div class="metadata">
            <p><strong>Identification Confidence:</strong> {self._format_percentage(report.identification.confidence_score)}</p>
            <p><strong>Valuation Confidence:</strong> {self._format_percentage(report.valuation.confidence_score)}</p>
        </div>
        <div class="recommendation">
            <strong>Recommendation:</strong> {report.valuation.recommendation.value.title()}
        </div>
        <p><strong>Reasoning:</strong> {report.valuation.reasoning}</p>

        <h2>Identification Results</h2>
        <p><strong>Description:</strong> {report.identification.description}</p>
        <p><strong>Condition Assessment:</strong> {report.identification.condition_assessment}</p>'''

        # Individual valuations section
        if report.valuation.individual_valuations:
            html += '<h2>Individual Item Valuations</h2>'
            
            for i, item_val in enumerate(report.valuation.individual_valuations):
                # Get individual minifigure image
                minifig_image = None
                if item_val.item.item_number or item_val.item.name:
                    minifig_image = self.image_service.get_minifigure_image(
                        item_val.item.item_number, 
                        item_val.item.name or "Unknown",
                        item_val.item.theme or "Unknown"
                    )
                
                html += f'''
        <div class="item-section">
            <h3>Item {i+1}: {item_val.item.name or 'Unknown'}</h3>'''
            
                # Include individual minifigure image if available
                if minifig_image and os.path.exists(minifig_image):
                    try:
                        import base64
                        with open(minifig_image, 'rb') as img_file:
                            img_data = base64.b64encode(img_file.read()).decode('utf-8')
                            html += f'''
            <div class="minifigure-image">
                <img src="data:image/png;base64,{img_data}" alt="{item_val.item.name or 'Unknown'}" />
            </div>'''
                    except Exception as e:
                        print(f"Could not include minifigure image in HTML: {e}")
                
                html += '''
            <table>
                <tr><th>Property</th><th>Value</th></tr>
                <tr><td>Item Number</td><td>{item_val.item.item_number or 'N/A'}</td></tr>
                <tr><td>Type</td><td>{item_val.item.item_type.value if item_val.item.item_type else 'N/A'}</td></tr>
                <tr><td>Condition</td><td>{item_val.item.condition.value if item_val.item.condition else 'N/A'}</td></tr>
                <tr><td>Theme</td><td>{item_val.item.theme or 'N/A'}</td></tr>
                <tr><td>Year Released</td><td>{item_val.item.year_released or 'N/A'}</td></tr>
                <tr><td>Pieces</td><td>{item_val.item.pieces or 'N/A'}</td></tr>
                <tr><td>Individual Value (USD)</td><td>{self._format_currency(item_val.estimated_individual_value_usd) if item_val.estimated_individual_value_usd else 'N/A'}</td></tr>
                <tr><td>Individual Value (EUR)</td><td>{'€{:,.2f}'.format(item_val.estimated_individual_value_eur) if item_val.estimated_individual_value_eur else 'N/A'}</td></tr>
                <tr><td>Confidence</td><td>{self._format_percentage(item_val.confidence_score)}</td></tr>
            </table>'''

                # Detailed pricing table
                if item_val.detailed_pricing:
                    pricing = item_val.detailed_pricing
                    html += '''
            <h4>Detailed Pricing by Condition</h4>
            <table class="pricing-table">
                <tr><th>Condition</th><th>USD</th><th>EUR</th></tr>'''
                    
                    pricing_rows = [
                        ("MSRP", pricing.msrp_usd, pricing.msrp_eur),
                        ("Sealed/New", pricing.sealed_new_usd, pricing.sealed_new_eur),
                        ("Used Complete", pricing.used_complete_usd, pricing.used_complete_eur),
                        ("Used Incomplete", pricing.used_incomplete_usd, pricing.used_incomplete_eur),
                        ("Missing Instructions", pricing.missing_instructions_usd, pricing.missing_instructions_eur),
                        ("Missing Box", pricing.missing_box_usd, pricing.missing_box_eur)
                    ]
                    
                    for condition, usd_price, eur_price in pricing_rows:
                        usd_display = self._format_currency(usd_price) if usd_price else "N/A"
                        eur_display = f"€{eur_price:,.2f}" if eur_price else "N/A"
                        html += f'<tr><td>{condition}</td><td>{usd_display}</td><td>{eur_display}</td></tr>'
                    
                    html += '</table>'
                
                if item_val.notes:
                    html += f'<p><strong>Notes:</strong> {item_val.notes}</p>'
                
                html += '</div>'

        # Market data section
        if report.valuation.market_data:
            market_data = report.valuation.market_data
            html += f'''
        <h2>Market Data</h2>
        <table>
            <tr><th>Metric</th><th>Value</th></tr>
            <tr><td>Current Market Price</td><td>{self._format_currency(market_data.current_price) if market_data.current_price else 'N/A'}</td></tr>
            <tr><td>Average 6M Price</td><td>{self._format_currency(market_data.avg_price_6m) if market_data.avg_price_6m else 'N/A'}</td></tr>
            <tr><td>Times Sold</td><td>{market_data.times_sold if market_data.times_sold else 'N/A'}</td></tr>
            <tr><td>Availability</td><td>{market_data.availability or 'N/A'}</td></tr>
        </table>'''
        else:
            html += '<h2>Market Data</h2><p>Market data not available</p>'

        # Suggested platforms
        if report.valuation.suggested_platforms:
            html += '<h2>Suggested Selling Platforms</h2><ul>'
            for platform in report.valuation.suggested_platforms:
                html += f'<li>{platform.value.replace("_", " ").title()}</li>'
            html += '</ul>'

        # Exchange rate footer
        if report.valuation.exchange_rate_usd_eur:
            html += f'''
        <div class="exchange-rate">
            Exchange rate used: 1 USD = {report.valuation.exchange_rate_usd_eur:.4f} EUR
        </div>'''

        html += '''
    </div>
</body>
</html>'''
        return html

    def _generate_markdown_content(self, report: ValuationReport) -> str:
        """Generate Markdown content for report"""
        md = f'''# LEGO Valuation Report

**Date:** {report.upload_timestamp.strftime('%Y-%m-%d %H:%M') if report.upload_timestamp else datetime.now().strftime('%Y-%m-%d %H:%M')}

## Valuation Summary

**Estimated Value:** **{self._format_currency(report.valuation.estimated_value)}**

- **Confidence:** {self._format_percentage(report.valuation.confidence_score)}
- **Recommendation:** {report.valuation.recommendation.value.title()}
- **Reasoning:** {report.valuation.reasoning}

## Identification Results

- **Confidence:** {self._format_percentage(report.identification.confidence_score)}
- **Description:** {report.identification.description}
- **Condition Assessment:** {report.identification.condition_assessment}

## Identified Items ({len(report.identification.identified_items)})

'''
        
        if report.identification.identified_items:
            md += '| Name | Type | Condition | Theme | Year | Pieces |\n'
            md += '|------|------|-----------|-------|------|--------|\n'
            
            for item in report.identification.identified_items:
                md += f'| {item.name or "Unknown"} | {item.item_type.value if item.item_type else "N/A"} | {item.condition.value if item.condition else "N/A"} | {item.theme or "N/A"} | {item.year_released or "N/A"} | {item.pieces or "N/A"} |\n'
        else:
            md += 'No items identified.\n'

        # Market data
        if report.valuation.market_data:
            market_data = report.valuation.market_data
            md += f'''
## Market Data

- **Current Market Price:** {self._format_currency(market_data.current_price) if market_data.current_price else 'N/A'}
- **Average 6M Price:** {self._format_currency(market_data.avg_price_6m) if market_data.avg_price_6m else 'N/A'}
- **Times Sold:** {market_data.times_sold if market_data.times_sold else 'N/A'} times
- **Availability:** {market_data.availability or 'N/A'}
'''
        else:
            md += '\n## Market Data\n\nMarket data not available.\n'

        # Suggested platforms
        if report.valuation.suggested_platforms:
            md += '\n## Suggested Selling Platforms\n\n'
            for platform in report.valuation.suggested_platforms:
                md += f'- {platform.value.replace("_", " ").title()}\n'

        return md