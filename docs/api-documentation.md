# API Documentation

This document provides comprehensive technical documentation for the LEGO Valuation System APIs and components.

## Core APIs

### LegoIdentifier API

The `LegoIdentifier` class provides Claude Vision-based LEGO item identification capabilities.

#### Class: `LegoIdentifier`

**Constructor:**
```python
LegoIdentifier(api_key: Optional[str] = None, rate_limiter: Optional[AnthropicRateLimiter] = None)
```

**Parameters:**
- `api_key`: Optional Anthropic API key. Uses environment variable if not provided
- `rate_limiter`: Optional rate limiter instance. Creates default if not provided

**Methods:**

##### `identify_lego_items(image_path: str) -> IdentificationResult`

Identifies LEGO items in an image using Claude Vision.

**Parameters:**
- `image_path`: Path to image file (JPG, PNG, WebP, GIF supported)

**Returns:**
- `IdentificationResult`: Contains confidence score, identified items, description, and condition assessment

**Example:**
```python
identifier = LegoIdentifier()
result = await identifier.identify_lego_items("/path/to/image.jpg")

print(f"Confidence: {result.confidence_score}")
print(f"Items found: {len(result.identified_items)}")
for item in result.identified_items:
    print(f"- {item.name}: {item.item_type.value}")
```

**Rate Limiting:**
- Automatically throttles requests to stay under 30,000 input tokens/minute
- Estimates token usage based on image size and prompt length
- Adds delays when necessary to prevent 429 errors

---

### ValuationEngine API

The `ValuationEngine` class provides comprehensive LEGO item valuation capabilities.

#### Class: `ValuationEngine`

**Constructor:**
```python
ValuationEngine(bricklink_client: Optional[BrickLinkClient] = None)
```

**Methods:**

##### `evaluate_item(identification: IdentificationResult) -> ValuationResult`

Evaluates the market value of identified LEGO items.

**Parameters:**
- `identification`: IdentificationResult from LegoIdentifier

**Returns:**
- `ValuationResult`: Complete valuation including individual item prices, recommendations, and market data

**Example:**
```python
engine = ValuationEngine()
valuation = await engine.evaluate_item(identification)

print(f"Total Value: ${valuation.estimated_value_usd:.2f}")
print(f"Recommendation: {valuation.recommendation.value}")
for individual in valuation.individual_valuations:
    print(f"- {individual.item.name}: ${individual.estimated_individual_value_usd:.2f}")
```

---

### BrickLinkClient API

The `BrickLinkClient` class provides market data integration with BrickLink.

#### Class: `BrickLinkClient`

**Constructor:**
```python
BrickLinkClient()
```
Uses environment variables for authentication.

**Methods:**

##### `search_items(item_type: str, query: str) -> List[Dict]`

Searches for LEGO items on BrickLink.

**Parameters:**
- `item_type`: Type of item ("MINIFIG", "SET", "PART")
- `query`: Search query string

**Returns:**
- List of search results with item details

##### `get_price_guide(item_type: str, item_no: str, condition: str) -> Optional[MarketData]`

Gets current market pricing for a specific item.

**Parameters:**
- `item_type`: Type of item ("MINIFIG", "SET", "PART")
- `item_no`: BrickLink item number
- `condition`: Condition code ("N" = new, "U" = used)

**Returns:**
- `MarketData` object with pricing information or None

##### `get_detailed_pricing(item_type: str, item_no: str) -> Optional[DetailedPricing]`

Gets comprehensive pricing across all conditions.

**Parameters:**
- `item_type`: Type of item
- `item_no`: BrickLink item number

**Returns:**
- `DetailedPricing` object with multi-condition pricing

---

### ReportGenerator API

The `ReportGenerator` class creates professional valuation reports.

#### Class: `ReportGenerator`

**Constructor:**
```python
ReportGenerator(output_dir: str = "data/reports")
```

**Methods:**

##### `generate_all_formats(report: ValuationReport, image_path: Optional[str] = None) -> Dict[str, str]`

Generates reports in all supported formats.

**Parameters:**
- `report`: ValuationReport data
- `image_path`: Optional path to original image

**Returns:**
- Dictionary mapping format names to file paths

##### `generate_pdf(report: ValuationReport, image_path: Optional[str] = None) -> str`

Generates PDF report with embedded images.

##### `generate_html(report: ValuationReport, image_path: Optional[str] = None) -> str`

Generates HTML report with embedded images.

##### `generate_json(report: ValuationReport) -> str`

Generates JSON report with base64-encoded images.

##### `generate_markdown(report: ValuationReport) -> str`

Generates Markdown report for documentation.

---

## Data Schemas

### Core Models

#### `IdentificationResult`
```python
class IdentificationResult(BaseModel):
    confidence_score: float  # 0.0 to 1.0
    identified_items: List[LegoItem]
    description: str
    condition_assessment: str
```

#### `LegoItem`
```python
class LegoItem(BaseModel):
    item_number: Optional[str] = None
    name: str
    item_type: ItemType
    condition: ItemCondition
    year_released: Optional[int] = None
    theme: Optional[str] = None
    category: Optional[str] = None
    pieces: Optional[int] = None
```

#### `ValuationResult`
```python
class ValuationResult(BaseModel):
    estimated_value_usd: float
    estimated_value_eur: Optional[float] = None
    exchange_rate_usd_eur: Optional[float] = None
    confidence_score: float
    recommendation: RecommendationCategory
    reasoning: str
    suggested_platforms: List[PlatformType]
    market_data: Optional[MarketData] = None
    individual_valuations: Optional[List[ItemValuation]] = None
```

#### `ItemValuation`
```python
class ItemValuation(BaseModel):
    item: LegoItem
    estimated_individual_value_usd: float
    estimated_individual_value_eur: Optional[float] = None
    confidence_score: float
    detailed_pricing: Optional[DetailedPricing] = None
    notes: Optional[str] = None
```

#### `DetailedPricing`
```python
class DetailedPricing(BaseModel):
    msrp_usd: Optional[float] = None
    msrp_eur: Optional[float] = None
    sealed_new_usd: Optional[float] = None
    sealed_new_eur: Optional[float] = None
    used_complete_usd: Optional[float] = None
    used_complete_eur: Optional[float] = None
    used_incomplete_usd: Optional[float] = None
    used_incomplete_eur: Optional[float] = None
    missing_instructions_usd: Optional[float] = None
    missing_instructions_eur: Optional[float] = None
    missing_box_usd: Optional[float] = None
    missing_box_eur: Optional[float] = None
```

### Enums

#### `ItemType`
- `MINIFIGURE`: Individual minifigure
- `SET`: Complete LEGO set
- `PART`: Individual LEGO piece

#### `ItemCondition`
- `NEW`: Brand new condition
- `USED_COMPLETE`: Used but complete
- `USED_INCOMPLETE`: Used with missing parts

#### `RecommendationCategory`
- `MUSEUM`: High-value items for preservation ($500+)
- `RESALE`: Good market value items ($50-499)
- `COLLECTION`: Personal collection items (<$50)

#### `PlatformType`
- `BRICKLINK`: BrickLink marketplace
- `EBAY`: eBay auctions/listings
- `LOCAL_AUCTION`: Local auction houses
- `FACEBOOK_MARKETPLACE`: Facebook Marketplace

---

## Web API Endpoints

The FastAPI web interface provides REST endpoints for system interaction.

### Upload and Processing

#### `POST /upload`

Upload and process a LEGO image.

**Request:**
- Multipart form data with image file
- Optional `notes` field

**Response:**
```json
{
  "valuation_id": 123,
  "estimated_value_usd": 247.50,
  "estimated_value_eur": 211.43,
  "confidence_score": 0.82,
  "recommendation": "resale",
  "items_identified": 8,
  "report_paths": {
    "pdf": "/data/reports/report_123.pdf",
    "html": "/data/reports/report_123.html",
    "json": "/data/reports/report_123.json"
  }
}
```

### Data Retrieval

#### `GET /valuations`

List all valuations with pagination.

**Parameters:**
- `limit`: Maximum results (default: 50)
- `offset`: Starting offset (default: 0)

#### `GET /valuations/{id}`

Get specific valuation details.

#### `GET /inventory`

Get inventory summary statistics.

**Response:**
```json
{
  "total_items": 156,
  "total_value_usd": 12450.75,
  "museum_items": 8,
  "resale_items": 45,
  "collection_items": 103,
  "themes": {
    "Star Wars": 34,
    "City": 28,
    "Creator": 21
  }
}
```

### Report Generation

#### `GET /reports/generate/{id}`

Generate fresh reports for a valuation.

**Parameters:**
- `format`: Report format ("pdf", "html", "json", "markdown", "all")

---

## Rate Limiting System

### AnthropicRateLimiter

Prevents API rate limit violations through intelligent request management.

#### Configuration

```python
rate_limiter = AnthropicRateLimiter(
    max_input_tokens_per_minute=25000,  # Safety buffer under 30k limit
    max_requests_per_minute=50,
    window_seconds=60
)
```

#### Token Estimation

The system estimates token usage based on:
- **Images**: `(width * height) / 750` tokens
- **System Prompts**: ~1500 tokens base
- **User Messages**: ~100 tokens base

#### Usage Tracking

- **Rolling Window**: 60-second sliding window
- **Real-time Monitoring**: Tracks current vs maximum usage
- **Automatic Delays**: Waits when limits would be exceeded
- **Usage Analytics**: Detailed logging for optimization

---

## Image Processing System

### ImageProcessor

Handles image upload, optimization, and processing.

#### Methods

##### `save_image(image_data: bytes, filename: str) -> Tuple[str, UploadInfo]`

Saves uploaded image with metadata.

##### `optimize_image_for_ai(image_path: str) -> str`

Optimizes image for AI processing:
- Resizes to max 1024x1024 pixels
- Maintains aspect ratio
- Optimizes JPEG quality
- Converts formats as needed

### MinifigureImageService

Manages individual minifigure images for reports.

#### Methods

##### `get_or_create_image(item: LegoItem) -> Optional[str]`

Gets existing or creates new minifigure image:
1. Checks local cache
2. Downloads from BrickLink if available
3. Generates placeholder if needed
4. Returns path to image file

##### `create_placeholder_image(item_name: str, theme: str = "Unknown") -> str`

Creates LEGO-style placeholder images:
- Yellow minifigure head design
- Theme-appropriate styling
- Character name overlay
- Professional quality output

---

## Database Schema

### Tables

#### `valuations`
- `id`: Primary key
- `image_path`: Path to original image
- `upload_timestamp`: When uploaded
- `estimated_value_usd`: Total USD value
- `estimated_value_eur`: Total EUR value
- `exchange_rate_usd_eur`: Exchange rate used
- `confidence_score`: Overall confidence
- `recommendation`: Category recommendation
- `reasoning`: Valuation reasoning
- `individual_valuations`: JSON array of item details
- `report_data`: Complete report JSON
- `notes`: User notes

#### `inventory_items`
- `id`: Primary key
- `valuation_id`: Foreign key to valuations
- `item_number`: BrickLink item number
- `name`: Item name
- `item_type`: Type (minifigure/set/part)
- `condition`: Condition assessment
- `estimated_value_usd`: Individual USD value
- `theme`: LEGO theme
- `year_released`: Release year
- `added_to_inventory`: Timestamp

---

## Error Handling

### Exception Types

#### `RateLimitError`
Raised when rate limits would be exceeded.

#### `ImageProcessingError`
Raised for image processing failures.

#### `APIError`
Raised for external API failures.

#### `ValidationError`
Raised for data validation failures.

### Error Response Format

```json
{
  "error": "error_type",
  "message": "Human readable error message",
  "details": {
    "field": "specific error details"
  },
  "timestamp": "2025-01-15T10:30:00Z"
}
```

---

## Configuration

### Environment Variables

```env
# AI & APIs
ANTHROPIC_API_KEY=sk-ant-api03-...
BRICKLINK_CONSUMER_KEY=your_consumer_key
BRICKLINK_CONSUMER_SECRET=your_consumer_secret
BRICKLINK_TOKEN_VALUE=your_token_value
BRICKLINK_TOKEN_SECRET=your_token_secret

# Valuation Thresholds (USD)
MUSEUM_THRESHOLD=500
RARE_THRESHOLD=100

# File Handling
MAX_UPLOAD_SIZE=10485760
ALLOWED_IMAGE_TYPES=jpg,jpeg,png,webp,gif

# Rate Limiting
ANTHROPIC_MAX_TOKENS_PER_MINUTE=25000
ANTHROPIC_MAX_REQUESTS_PER_MINUTE=50

# Database
DATABASE_URL=sqlite:///data/minifigure_valuation.db

# Exchange Rates
EXCHANGE_RATE_API_KEY=your_api_key
```

### Settings Class

```python
from config.settings import settings

# Access configuration
print(settings.museum_threshold)  # 500.0
print(settings.max_upload_size)   # 10485760
print(settings.allowed_image_types)  # ['jpg', 'jpeg', 'png', 'webp', 'gif']
```

---

## Performance Optimization

### Caching Strategies

#### Image Caching
- **Location**: `data/minifigure_images/`
- **Format**: PNG files with BrickLink item numbers
- **Cleanup**: Manual cleanup of unused files

#### Rate Limit Tracking
- **Storage**: In-memory deque with timestamps
- **Window**: 60-second rolling window
- **Cleanup**: Automatic removal of old entries

#### Exchange Rate Caching
- **Frequency**: Hourly updates
- **Fallback**: Static rates if API unavailable
- **Storage**: Database with timestamps

### Memory Management

- **Image Processing**: Streams large images to avoid memory spikes
- **Report Generation**: Processes reports individually
- **Database**: Connection pooling for concurrent requests

---

## Security Considerations

### API Key Management
- Environment variable storage only
- No hardcoded keys in source code
- Separate keys for different services

### Image Upload Security
- File type validation
- Size limits enforced
- Temporary file cleanup
- No execution of uploaded files

### Data Sanitization
- SQL injection prevention through ORM
- XSS prevention in HTML reports
- Input validation on all endpoints

---

## Monitoring and Logging

### Logging Configuration

```python
import logging

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
```

### Key Metrics

- **API Usage**: Token consumption and request rates
- **Processing Time**: Image processing and valuation duration  
- **Success Rates**: Identification and valuation confidence
- **Error Rates**: Failed requests and processing errors

### Log Locations

- **Application Logs**: Console output and file logs
- **Access Logs**: Web server request logs
- **Error Logs**: Exception tracking and stack traces