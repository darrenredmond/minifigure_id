import os
from typing import List, Optional
from pathlib import Path
from datetime import datetime
from reportlab.lib.pagesizes import letter
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet, ParagraphStyle
from reportlab.platypus import (
    SimpleDocTemplate,
    Paragraph,
    Spacer,
    Table,
    TableStyle,
    Image,
)
from reportlab.lib.units import inch
from jinja2 import Environment, FileSystemLoader
import json

from src.models.schemas import ValuationReport, ValuationResult, IdentificationResult
from config.settings import settings


class ReportGenerator:
    def __init__(self, reports_dir: str = "data/reports"):
        self.reports_dir = Path(reports_dir)
        self.reports_dir.mkdir(parents=True, exist_ok=True)

        # Setup Jinja2 templates
        self.template_env = Environment(
            loader=FileSystemLoader(str(Path(__file__).parent / "templates"))
        )

    def generate_pdf_report(self, report: ValuationReport) -> str:
        """Generate a PDF valuation report"""
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"valuation_report_{timestamp}.pdf"
        pdf_path = self.reports_dir / pdf_filename

        # Create PDF document
        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
        styles = getSampleStyleSheet()

        # Custom styles
        title_style = ParagraphStyle(
            "CustomTitle",
            parent=styles["Heading1"],
            fontSize=18,
            spaceAfter=30,
            textColor=colors.darkblue,
        )

        heading_style = ParagraphStyle(
            "CustomHeading",
            parent=styles["Heading2"],
            fontSize=14,
            spaceBefore=20,
            spaceAfter=10,
            textColor=colors.darkred,
        )

        # Build document content
        content = []

        # Title
        content.append(Paragraph("LEGO Valuation Report", title_style))
        content.append(Paragraph(f"Redmond's Forge Antique Shop", styles["Normal"]))
        content.append(Spacer(1, 20))

        # Report metadata
        content.append(Paragraph("Report Information", heading_style))
        metadata_data = [
            ["Report Date:", report.created_at.strftime("%Y-%m-%d %H:%M")],
            ["Image File:", report.image_filename],
            ["Upload Date:", report.upload_timestamp.strftime("%Y-%m-%d %H:%M")],
        ]
        metadata_table = Table(metadata_data, colWidths=[2 * inch, 4 * inch])
        metadata_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        content.append(metadata_table)
        content.append(Spacer(1, 20))

        # Identification results
        content.append(Paragraph("Item Identification", heading_style))
        content.append(
            Paragraph(
                f"<b>Confidence Score:</b> {report.identification.confidence_score:.2%}",
                styles["Normal"],
            )
        )
        content.append(
            Paragraph(
                f"<b>Description:</b> {report.identification.description}",
                styles["Normal"],
            )
        )
        content.append(
            Paragraph(
                f"<b>Condition Assessment:</b> {report.identification.condition_assessment}",
                styles["Normal"],
            )
        )
        content.append(Spacer(1, 10))

        # Identified items table
        if report.identification.identified_items:
            content.append(
                Paragraph(
                    "Identified Items",
                    ParagraphStyle("SubHeading", parent=styles["Heading3"]),
                )
            )

            items_data = [["Item Number", "Name", "Type", "Condition", "Year", "Theme"]]
            for item in report.identification.identified_items:
                items_data.append(
                    [
                        item.item_number or "N/A",
                        item.name or "Unknown",
                        item.item_type.value,
                        item.condition.value,
                        str(item.year_released) if item.year_released else "N/A",
                        item.theme or "N/A",
                    ]
                )

            items_table = Table(
                items_data,
                colWidths=[
                    1 * inch,
                    2 * inch,
                    0.8 * inch,
                    1 * inch,
                    0.7 * inch,
                    1.5 * inch,
                ],
            )
            items_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 9),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 6),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            content.append(items_table)
            content.append(Spacer(1, 20))

        # Valuation results
        content.append(Paragraph("Valuation Assessment", heading_style))

        valuation_data = [
            ["Estimated Value:", f"${report.valuation.estimated_value:.2f}"],
            ["Confidence Score:", f"{report.valuation.confidence_score:.2%}"],
            ["Recommendation:", report.valuation.recommendation.value.title()],
            [
                "Suggested Platforms:",
                ", ".join(
                    [
                        p.value.replace("_", " ").title()
                        for p in report.valuation.suggested_platforms
                    ]
                ),
            ],
        ]

        valuation_table = Table(valuation_data, colWidths=[2 * inch, 4 * inch])
        valuation_table.setStyle(
            TableStyle(
                [
                    ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 11),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ("GRID", (0, 0), (-1, -1), 1, colors.grey),
                ]
            )
        )
        content.append(valuation_table)
        content.append(Spacer(1, 15))

        # Market data if available
        if report.valuation.market_data and report.valuation.market_data.current_price:
            content.append(Paragraph("Market Data", heading_style))
            market_data = report.valuation.market_data
            market_info = [
                [
                    "Current Market Price:",
                    (
                        f"${market_data.current_price:.2f}"
                        if market_data.current_price
                        else "N/A"
                    ),
                ],
                [
                    "Times Sold:",
                    str(market_data.times_sold) if market_data.times_sold else "N/A",
                ],
                [
                    "Availability:",
                    (
                        market_data.availability.replace("_", " ").title()
                        if market_data.availability
                        else "N/A"
                    ),
                ],
                [
                    "Price Trend:",
                    (
                        market_data.price_trend.title()
                        if market_data.price_trend
                        else "N/A"
                    ),
                ],
            ]

            market_table = Table(market_info, colWidths=[2 * inch, 4 * inch])
            market_table.setStyle(
                TableStyle(
                    [
                        ("ALIGN", (0, 0), (-1, -1), "LEFT"),
                        ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 10),
                        ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                    ]
                )
            )
            content.append(market_table)
            content.append(Spacer(1, 15))

        # Reasoning
        content.append(Paragraph("Valuation Reasoning", heading_style))
        content.append(Paragraph(report.valuation.reasoning, styles["Normal"]))
        content.append(Spacer(1, 15))

        # Notes if any
        if report.notes:
            content.append(Paragraph("Additional Notes", heading_style))
            content.append(Paragraph(report.notes, styles["Normal"]))
            content.append(Spacer(1, 15))

        # Footer
        content.append(Spacer(1, 30))
        footer_style = ParagraphStyle(
            "Footer",
            parent=styles["Normal"],
            fontSize=8,
            textColor=colors.grey,
            alignment=1,  # Center alignment
        )
        content.append(
            Paragraph(
                "This report was generated using AI-assisted valuation. Please verify with additional sources for critical decisions.",
                footer_style,
            )
        )
        content.append(
            Paragraph(
                f"Generated by Redmond's Forge Valuation System on {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}",
                footer_style,
            )
        )

        # Build PDF
        doc.build(content)

        return str(pdf_path)

    def generate_html_report(self, report: ValuationReport) -> str:
        """Generate an HTML valuation report"""
        # Create filename
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_filename = f"valuation_report_{timestamp}.html"
        html_path = self.reports_dir / html_filename

        # Prepare template data
        template_data = {
            "report": report,
            "generated_at": datetime.now(),
            "estimated_value_formatted": f"${report.valuation.estimated_value:.2f}",
            "confidence_percentage": f"{report.valuation.confidence_score:.1%}",
            "identification_confidence": f"{report.identification.confidence_score:.1%}",
        }

        # Load and render template
        try:
            template = self.template_env.get_template("valuation_report.html")
            html_content = template.render(template_data)
        except Exception:
            # Fallback to basic HTML if template not found
            html_content = self._generate_basic_html(report)

        # Write HTML file
        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(html_path)

    def _generate_basic_html(self, report: ValuationReport) -> str:
        """Generate basic HTML report when template is not available"""
        return f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>LEGO Valuation Report</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 40px; }}
                .header {{ color: #2c3e50; border-bottom: 2px solid #3498db; padding-bottom: 10px; }}
                .section {{ margin: 20px 0; }}
                .value {{ color: #27ae60; font-weight: bold; font-size: 1.2em; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .recommendation {{ padding: 10px; border-left: 4px solid #3498db; background-color: #ecf0f1; }}
            </style>
        </head>
        <body>
            <div class="header">
                <h1>LEGO Valuation Report</h1>
                <p>Redmond's Forge Antique Shop</p>
                <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            </div>
            
            <div class="section">
                <h2>Item Information</h2>
                <p><strong>Image:</strong> {report.image_filename}</p>
                <p><strong>Upload Date:</strong> {report.upload_timestamp.strftime('%Y-%m-%d %H:%M')}</p>
            </div>
            
            <div class="section">
                <h2>Identification Results</h2>
                <p><strong>Confidence:</strong> {report.identification.confidence_score:.2%}</p>
                <p><strong>Description:</strong> {report.identification.description}</p>
                <p><strong>Condition:</strong> {report.identification.condition_assessment}</p>
            </div>
            
            <div class="section">
                <h2>Valuation</h2>
                <p class="value">Estimated Value: ${report.valuation.estimated_value:.2f}</p>
                <p><strong>Confidence:</strong> {report.valuation.confidence_score:.2%}</p>
                <div class="recommendation">
                    <strong>Recommendation:</strong> {report.valuation.recommendation.value.title()}
                </div>
                <p><strong>Reasoning:</strong> {report.valuation.reasoning}</p>
            </div>
            
            <div class="section">
                <h2>Suggested Platforms</h2>
                <ul>
                    {''.join([f"<li>{p.value.replace('_', ' ').title()}</li>" for p in report.valuation.suggested_platforms])}
                </ul>
            </div>
        </body>
        </html>
        """

    def generate_json_export(self, reports: List[ValuationReport]) -> str:
        """Generate JSON export of multiple reports"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        json_filename = f"valuation_export_{timestamp}.json"
        json_path = self.reports_dir / json_filename

        # Convert reports to dict format
        export_data = {
            "exported_at": datetime.now().isoformat(),
            "total_reports": len(reports),
            "reports": [report.dict() for report in reports],
        }

        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(export_data, f, indent=2, default=str)

        return str(json_path)

    def create_inventory_summary(
        self, inventory_items: List, output_format: str = "pdf"
    ) -> str:
        """Create inventory summary report"""
        if output_format.lower() == "pdf":
            return self._create_inventory_pdf(inventory_items)
        else:
            return self._create_inventory_html(inventory_items)

    def _create_inventory_pdf(self, inventory_items: List) -> str:
        """Create PDF inventory summary"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        pdf_filename = f"inventory_summary_{timestamp}.pdf"
        pdf_path = self.reports_dir / pdf_filename

        doc = SimpleDocTemplate(str(pdf_path), pagesize=letter)
        styles = getSampleStyleSheet()
        content = []

        # Title
        title_style = ParagraphStyle(
            "CustomTitle", parent=styles["Heading1"], fontSize=16
        )
        content.append(Paragraph("Inventory Summary Report", title_style))
        content.append(
            Paragraph(
                f"Redmond's Forge - {datetime.now().strftime('%Y-%m-%d')}",
                styles["Normal"],
            )
        )
        content.append(Spacer(1, 30))

        # Summary statistics
        total_items = len(inventory_items)
        total_value = sum(item.estimated_value or 0 for item in inventory_items)

        content.append(Paragraph("Summary Statistics", styles["Heading2"]))
        summary_data = [
            ["Total Items:", str(total_items)],
            ["Total Estimated Value:", f"${total_value:.2f}"],
            [
                "Average Value:",
                f"${total_value/total_items:.2f}" if total_items > 0 else "$0.00",
            ],
        ]

        summary_table = Table(summary_data, colWidths=[2 * inch, 2 * inch])
        summary_table.setStyle(
            TableStyle(
                [
                    ("FONTNAME", (0, 0), (0, -1), "Helvetica-Bold"),
                    ("FONTSIZE", (0, 0), (-1, -1), 10),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 8),
                ]
            )
        )
        content.append(summary_table)
        content.append(Spacer(1, 20))

        # Items table (first 20 items)
        if inventory_items:
            content.append(Paragraph("Top Items by Value", styles["Heading2"]))

            items_data = [["Item", "Type", "Condition", "Est. Value", "Location"]]
            for item in sorted(
                inventory_items, key=lambda x: x.estimated_value or 0, reverse=True
            )[:20]:
                items_data.append(
                    [
                        item.item_name[:30] or "Unknown",
                        item.item_type or "N/A",
                        item.condition or "N/A",
                        (
                            f"${item.estimated_value:.2f}"
                            if item.estimated_value
                            else "N/A"
                        ),
                        item.location[:20] if item.location else "N/A",
                    ]
                )

            items_table = Table(
                items_data,
                colWidths=[2 * inch, 1 * inch, 1 * inch, 1 * inch, 1.5 * inch],
            )
            items_table.setStyle(
                TableStyle(
                    [
                        ("BACKGROUND", (0, 0), (-1, 0), colors.grey),
                        ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                        ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                        ("FONTSIZE", (0, 0), (-1, -1), 8),
                        ("GRID", (0, 0), (-1, -1), 1, colors.black),
                    ]
                )
            )
            content.append(items_table)

        doc.build(content)
        return str(pdf_path)

    def _create_inventory_html(self, inventory_items: List) -> str:
        """Create HTML inventory summary"""
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        html_filename = f"inventory_summary_{timestamp}.html"
        html_path = self.reports_dir / html_filename

        total_value = sum(item.estimated_value or 0 for item in inventory_items)

        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <title>Inventory Summary</title>
            <style>
                body {{ font-family: Arial, sans-serif; margin: 20px; }}
                table {{ border-collapse: collapse; width: 100%; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f2f2f2; }}
                .summary {{ background-color: #e8f4fd; padding: 20px; margin: 20px 0; }}
            </style>
        </head>
        <body>
            <h1>Inventory Summary</h1>
            <p>Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
            
            <div class="summary">
                <h2>Summary Statistics</h2>
                <p><strong>Total Items:</strong> {len(inventory_items)}</p>
                <p><strong>Total Estimated Value:</strong> ${total_value:.2f}</p>
                <p><strong>Average Value:</strong> ${total_value/len(inventory_items):.2f if inventory_items else 0}</p>
            </div>
            
            <h2>Inventory Items</h2>
            <table>
                <tr>
                    <th>Item Name</th>
                    <th>Type</th>
                    <th>Condition</th>
                    <th>Estimated Value</th>
                    <th>Location</th>
                    <th>Status</th>
                </tr>
        """

        for item in sorted(
            inventory_items, key=lambda x: x.estimated_value or 0, reverse=True
        ):
            html_content += f"""
                <tr>
                    <td>{item.item_name or 'Unknown'}</td>
                    <td>{item.item_type or 'N/A'}</td>
                    <td>{item.condition or 'N/A'}</td>
                    <td>${item.estimated_value:.2f if item.estimated_value else 0}</td>
                    <td>{item.location or 'N/A'}</td>
                    <td>{item.status or 'N/A'}</td>
                </tr>
            """

        html_content += """
            </table>
        </body>
        </html>
        """

        with open(html_path, "w", encoding="utf-8") as f:
            f.write(html_content)

        return str(html_path)
