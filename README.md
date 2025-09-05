# LEGO Valuation System
**AI-powered LEGO minifigure and set valuation system for Redmond's Forge antique shop**

This system uses Claude's vision capabilities to identify LEGO minifigures and sets, cross-references with BrickLink for market values, and provides intelligent recommendations for museum preservation vs. resale.

## Features

- 🔍 **AI-Powered Identification**: Uses Claude Vision to identify specific LEGO pieces
- 💰 **Market Valuation**: Cross-references with BrickLink API for current market prices
- 🏛️ **Museum vs Resale Logic**: Intelligent recommendations based on rarity and value
- 📊 **Professional Reports**: Generates PDF and HTML valuation reports
- 📦 **Inventory Tracking**: Maintains database of all valued items
- 🛒 **Platform Recommendations**: Suggests best resale platforms (BrickLink, eBay, etc.)
- 🌐 **Web Interface**: Easy-to-use web interface for uploads and management
- 🖥️ **CLI Interface**: Command-line interface for batch processing

## Quick Start

### 1. Installation

```bash
# Clone the repository
git clone <repository-url>
cd minifigure_id

# Install dependencies
pip install -r requirements.txt

# Initialize the system
python main.py init
```

### 2. Configuration

Copy the example environment file and configure your API keys:

```bash
cp .env.example .env
```

Edit `.env` with your API keys:
- **ANTHROPIC_API_KEY**: Get from https://console.anthropic.com/
- **BRICKLINK_***: Get from https://www.bricklink.com/v3/api/register_consumer.page

### 3. Usage

**Web Interface** (Recommended):
```bash
python main.py server
# Visit http://localhost:8000
```

**Command Line**:
```bash
# Process a single image
python main.py process path/to/lego_image.jpg

# Add notes
python main.py process image.jpg --notes "Found in estate sale"

# List recent valuations
python main.py list

# Show inventory summary
python main.py inventory
```

## System Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Web/CLI UI    │    │   Image Upload   │    │  Claude Vision  │
│                 │───▶│   & Processing   │───▶│  Identification │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                                         │
┌─────────────────┐    ┌──────────────────┐             ▼
│  PDF/HTML       │    │   Valuation      │    ┌─────────────────┐
│  Reports        │◀───│   Engine         │◀───│  BrickLink API  │
└─────────────────┘    └──────────────────┘    │  Market Data    │
                                │               └─────────────────┘
                                ▼
                       ┌──────────────────┐
                       │  SQLite Database │
                       │  Inventory       │
                       └──────────────────┘
```

## API Endpoints

- `POST /upload` - Upload and process image
- `GET /valuations` - List all valuations
- `GET /valuations/{id}` - Get specific valuation
- `GET /inventory` - Inventory summary
- `POST /inventory/add/{valuation_id}` - Add to inventory
- `GET /reports/generate/{id}` - Generate report

## Project Structure

```
minifigure_id/
├── config/
│   └── settings.py          # Configuration management
├── src/
│   ├── api/                 # FastAPI web interface
│   ├── core/                # Core business logic
│   │   ├── lego_identifier.py      # Claude Vision integration
│   │   ├── valuation_engine.py     # Valuation logic
│   │   └── report_generator.py     # PDF/HTML reports
│   ├── database/            # Database models and operations
│   ├── external/            # External API integrations
│   │   └── bricklink_client.py     # BrickLink API client
│   ├── models/              # Data schemas
│   └── utils/               # Utility functions
├── data/
│   ├── uploads/             # Uploaded images
│   └── reports/             # Generated reports
├── tests/                   # Test files
├── main.py                  # CLI interface
└── requirements.txt         # Dependencies
```

## Configuration

Key settings in `.env`:

```env
# AI & APIs
ANTHROPIC_API_KEY=your_key_here
BRICKLINK_CONSUMER_KEY=your_key
BRICKLINK_CONSUMER_SECRET=your_secret
BRICKLINK_TOKEN_VALUE=your_token
BRICKLINK_TOKEN_SECRET=your_token_secret

# Valuation Thresholds (USD)
MUSEUM_THRESHOLD=500         # Items above this go to museum
RARE_THRESHOLD=100          # Items above this recommended for resale

# File Limits
MAX_UPLOAD_SIZE=10485760    # 10MB
ALLOWED_IMAGE_TYPES=jpg,jpeg,png,webp
```

## Development

```bash
# Install development dependencies
pip install -r requirements.txt

# Run tests
pytest

# Code formatting
black src/ tests/

# Linting
pylint src/

# Type checking
mypy src/
```

## Example Workflow

1. **Upload Image**: Take photo of LEGO items
2. **AI Identification**: Claude Vision identifies specific pieces
3. **Market Research**: System queries BrickLink for current values
4. **Valuation**: Engine combines AI confidence, condition, rarity
5. **Recommendation**: Museum (rare/valuable) vs Resale decision
6. **Report Generation**: Professional PDF/HTML reports
7. **Inventory Tracking**: Add to database for ongoing management

## License

MIT License - see LICENSE file for details.

---

**Redmond's Forge Antique Shop**  
*Preserving LEGO history, one minifigure at a time*
