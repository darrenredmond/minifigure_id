# Enhanced LEGO Valuation System
**AI-powered LEGO minifigure and set valuation system with database-driven identification**

This system combines Claude's vision capabilities with a comprehensive minifigure database to identify LEGO pieces, cross-references with BrickLink for market values, and provides intelligent recommendations for museum preservation vs. resale.

## 🚀 Enhanced Features

- 🔍 **Database-Driven Identification**: 2000+ minifigure database for improved accuracy (85% vs 60-70%)
- 🤖 **Dual AI Modes**: Enhanced database matching + AI fallback for maximum coverage
- 💰 **Market Valuation**: Cross-references with BrickLink API for current market prices
- 🏛️ **Museum vs Resale Logic**: Intelligent recommendations based on rarity and value
- 📊 **Professional Reports**: Generates PDF and HTML valuation reports
- 📦 **Inventory Tracking**: Maintains database of all valued items
- 🛒 **Platform Recommendations**: Suggests best resale platforms (BrickLink, eBay, etc.)
- 🌐 **Web Interface**: Easy-to-use web interface for uploads and management
- 🖥️ **Enhanced CLI**: Command-line interface with database search and management
- 🔎 **Advanced Search**: Search across 2000+ minifigures by name, theme, or characteristics

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

### 3. Setup Enhanced Database (Recommended)

For improved accuracy, set up the minifigure database:

```bash
# Setup database with 1000 minifigures (recommended for production)
python main.py setup --count 1000

# Or setup with more minifigures for maximum accuracy
python main.py setup --count 2000
```

### 4. Usage

**Enhanced CLI Interface** (Recommended):
```bash
# Process image with enhanced database matching (default)
python main.py process /path/to/image.jpg --notes "Found in attic, good condition"

# Process with standard AI only
python main.py process /path/to/image.jpg --standard

# Search the minifigure database
python main.py search "spider"
python main.py search "construction"

# View database statistics
python main.py stats

# List recent valuations
python main.py list --limit 20

# Show inventory summary
python main.py inventory
```

**Web Interface**:
```bash
python main.py web
# Visit http://localhost:8000
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
