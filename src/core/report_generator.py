import os
import json
import uuid
from typing import List, Optional, Dict, Any
from pathlib import Path
from datetime import datetime
import tempfile

try:
    from reportlab.lib.pagesizes import letter
    from reportlab.lib import colors
    from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
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

    def generate_json(self, report: ValuationReport) -> str:
        """Generate JSON report"""
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
            "estimated_value": report.valuation.estimated_value,
            "confidence_score": report.valuation.confidence_score,
            "recommendation": report.valuation.recommendation.value,
            "reasoning": report.valuation.reasoning,
            "suggested_platforms": [p.value for p in report.valuation.suggested_platforms],
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
            "market_data": report.valuation.market_data.model_dump() if report.valuation.market_data else None
        }

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
        """Generate PDF report"""
        if not REPORTLAB_AVAILABLE:
            raise ImportError("ReportLab is required for PDF generation. Install with: pip install reportlab")

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        unique_id = str(uuid.uuid4())[:8]
        filename = f"valuation_report_{timestamp}_{unique_id}.pdf"
        file_path = self.output_dir / filename

        # Create PDF using canvas (simpler approach)
        c = canvas.Canvas(str(file_path), pagesize=letter)
        width, height = letter

        # Title
        c.setFont("Helvetica-Bold", 20)
        c.drawString(50, height - 50, "LEGO Valuation Report")
        
        # Basic info
        c.setFont("Helvetica", 12)
        y_pos = height - 100
        
        c.drawString(50, y_pos, f"Date: {report.upload_timestamp.strftime('%Y-%m-%d %H:%M') if report.upload_timestamp else datetime.now().strftime('%Y-%m-%d %H:%M')}")
        y_pos -= 20
        
        c.drawString(50, y_pos, f"Estimated Value: {self._format_currency(report.valuation.estimated_value)}")
        y_pos -= 20
        
        c.drawString(50, y_pos, f"Confidence: {self._format_percentage(report.valuation.confidence_score)}")
        y_pos -= 20
        
        c.drawString(50, y_pos, f"Recommendation: {report.valuation.recommendation.value.title()}")
        y_pos -= 40
        
        # Items
        if report.identification.identified_items:
            c.setFont("Helvetica-Bold", 14)
            c.drawString(50, y_pos, "Identified Items:")
            y_pos -= 20
            
            c.setFont("Helvetica", 10)
            for item in report.identification.identified_items:
                item_text = f"• {item.name or 'Unknown'}"
                if item.item_number:
                    item_text += f" ({item.item_number})"
                if item.theme:
                    item_text += f" - {item.theme}"
                
                c.drawString(60, y_pos, item_text)
                y_pos -= 15
                
                if y_pos < 100:  # New page if needed
                    c.showPage()
                    y_pos = height - 50

        # Include image if available and PIL is installed
        # Note: since we only have filename, we'd need full path to include image
        # For now, just skip image inclusion
        pass

        c.save()
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
        """Generate HTML content for report"""
        recommendation_color = self._get_recommendation_color(report.valuation.recommendation)
        
        html = f'''<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>LEGO Valuation Report</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; line-height: 1.6; }}
        .header {{ background-color: #f4f4f4; padding: 20px; border-radius: 5px; }}
        .recommendation {{ background-color: {recommendation_color}; color: #333; padding: 10px; border-radius: 5px; }}
        .item {{ border: 1px solid #ddd; padding: 10px; margin: 10px 0; border-radius: 5px; }}
        .value {{ font-size: 2em; color: #2c5aa0; font-weight: bold; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
    </style>
</head>
<body>
    <div class="header">
        <h1>LEGO Valuation Report</h1>
        <p><strong>Date:</strong> {report.upload_timestamp.strftime('%Y-%m-%d %H:%M') if report.upload_timestamp else datetime.now().strftime('%Y-%m-%d %H:%M')}</p>
    </div>

    <h2>Valuation Summary</h2>
    <div class="value">{self._format_currency(report.valuation.estimated_value)}</div>
    <p><strong>Confidence:</strong> {self._format_percentage(report.valuation.confidence_score)}</p>
    <div class="recommendation">
        <strong>Recommendation:</strong> {report.valuation.recommendation.value.title()}
    </div>
    <p><strong>Reasoning:</strong> {report.valuation.reasoning}</p>

    <h2>Identification Results</h2>
    <p><strong>Confidence:</strong> {self._format_percentage(report.identification.confidence_score)}</p>
    <p><strong>Description:</strong> {report.identification.description}</p>
    <p><strong>Condition Assessment:</strong> {report.identification.condition_assessment}</p>

    <h2>Identified Items ({len(report.identification.identified_items)})</h2>
'''
        
        if report.identification.identified_items:
            html += '<table><tr><th>Name</th><th>Type</th><th>Condition</th><th>Theme</th><th>Year</th><th>Pieces</th></tr>'
            for item in report.identification.identified_items:
                html += f'''<tr>
                    <td>{item.name or 'Unknown'}</td>
                    <td>{item.item_type.value if item.item_type else 'N/A'}</td>
                    <td>{item.condition.value if item.condition else 'N/A'}</td>
                    <td>{item.theme or 'N/A'}</td>
                    <td>{item.year_released or 'N/A'}</td>
                    <td>{item.pieces or 'N/A'}</td>
                </tr>'''
            html += '</table>'
        else:
            html += '<p>No items identified</p>'

        # Market data section
        if report.valuation.market_data:
            market_data = report.valuation.market_data
            html += f'''
    <h2>Market Data</h2>
    <p><strong>Current Market Price:</strong> {self._format_currency(market_data.current_price) if market_data.current_price else 'N/A'}</p>
    <p><strong>Average 6M Price:</strong> {self._format_currency(market_data.avg_price_6m) if market_data.avg_price_6m else 'N/A'}</p>
    <p><strong>Times Sold:</strong> {market_data.times_sold if market_data.times_sold else 'N/A'} times</p>
    <p><strong>Availability:</strong> {market_data.availability or 'N/A'}</p>
'''
        else:
            html += '<h2>Market Data</h2><p>Market data not available</p>'

        # Suggested platforms
        if report.valuation.suggested_platforms:
            html += '<h2>Suggested Selling Platforms</h2><ul>'
            for platform in report.valuation.suggested_platforms:
                html += f'<li>{platform.value.replace("_", " ").title()}</li>'
            html += '</ul>'

        html += '</body></html>'
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