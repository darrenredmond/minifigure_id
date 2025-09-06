# Testing and Deployment Guide

This guide covers comprehensive testing strategies and deployment procedures for the LEGO Valuation System.

## Testing Overview

The system uses pytest for comprehensive testing across multiple levels:
- **Unit Tests**: Individual component testing
- **Integration Tests**: API and system integration
- **End-to-End Tests**: Complete workflow validation

### Test Commands

```bash
# Run all tests
pytest

# Run specific test files
pytest tests/test_lego_identifier.py
pytest tests/test_valuation_engine.py
pytest tests/test_report_generator.py

# Run with coverage
pytest --cov=src --cov-report=term-missing

# Run integration tests (requires API keys)
pytest tests/test_integration.py -v -s

# Run specific integration test
pytest tests/test_integration.py::TestRealAPIIntegration::test_claude_vision_with_lego_image -v -s
```

## Test Structure

### Unit Tests

#### `tests/test_lego_identifier.py`
Tests for AI-powered LEGO identification:
- Image encoding and validation
- API parameter verification
- Rate limiting functionality
- Error handling scenarios
- JSON parsing and validation

**Key Test Cases:**
```python
@pytest.mark.asyncio
async def test_identify_lego_items_success(self, lego_identifier, sample_image_path):
    """Test successful LEGO identification with valid JSON response"""
    
@pytest.mark.asyncio  
async def test_identify_lego_items_invalid_json(self, lego_identifier, sample_image_path):
    """Test handling of invalid JSON response"""
```

#### `tests/test_valuation_engine.py`
Tests for market valuation logic:
- Individual item valuation
- Multi-currency pricing
- Recommendation logic
- BrickLink integration
- Exchange rate handling

#### `tests/test_report_generator.py`
Tests for report generation:
- PDF creation with images
- HTML generation with embedded assets
- JSON data export
- Markdown formatting
- Multi-format generation
- Error handling

**Key Test Cases:**
```python
def test_generate_pdf_report(self, mock_doc_class, report_generator, sample_report):
    """Test PDF report generation"""

def test_generate_html_report(self, report_generator, sample_report):
    """Test HTML report generation"""
```

### Integration Tests

#### `tests/test_integration.py`
Real API integration testing:

**BrickLink API Tests:**
```python
def test_bricklink_search_real(self, has_bricklink_keys):
    """Test BrickLink API search functionality"""
    
def test_bricklink_price_guide_real(self, has_bricklink_keys):
    """Test BrickLink price guide API"""
```

**Claude Vision Tests:**
```python
@pytest.mark.asyncio
async def test_claude_vision_with_lego_image(self, has_anthropic_key):
    """Test Claude Vision API with a LEGO-like test image"""
```

**End-to-End Workflow:**
```python
@pytest.mark.asyncio
async def test_full_valuation_pipeline(self, has_anthropic_key, has_bricklink_keys):
    """Test the complete valuation pipeline from image to valuation"""
```

## Test Configuration

### API Key Requirements

Integration tests require valid API keys:

```bash
# Required for Claude Vision tests
export ANTHROPIC_API_KEY=sk-ant-api03-...

# Required for BrickLink tests
export BRICKLINK_CONSUMER_KEY=your_key
export BRICKLINK_CONSUMER_SECRET=your_secret  
export BRICKLINK_TOKEN_VALUE=your_token
export BRICKLINK_TOKEN_SECRET=your_token_secret
```

### Test Fixtures

Common test fixtures provide reusable test data:

```python
@pytest.fixture
def sample_report(self):
    """Create sample valuation report"""
    return ValuationReport(
        image_filename="test_image.jpg",
        upload_timestamp=datetime(2024, 1, 15, 10, 30, 0),
        identification=identification,
        valuation=valuation
    )
```

### Mock Objects

Unit tests use extensive mocking to isolate components:

```python
@pytest.fixture
def mock_anthropic_client(self):
    """Mock Anthropic client for testing"""
    mock_client = Mock()
    mock_message = Mock()
    mock_client.messages.create.return_value = mock_message
    return mock_client
```

## Test Data Management

### Image Generation

Tests create synthetic LEGO images for consistent testing:

```python
def create_lego_test_image():
    """Create a test image that looks somewhat like LEGO bricks"""
    img = Image.new('RGB', (800, 600), color='white')
    draw = ImageDraw.Draw(img)
    
    # Draw brick-like rectangles with studs
    colors = [(255, 0, 0), (0, 255, 0), (0, 0, 255), (255, 255, 0)]
```

### Cleanup Strategies

Tests properly clean up temporary files:

```python
@pytest.fixture
def sample_image_path(self):
    """Create a temporary test image file"""
    with tempfile.NamedTemporaryFile(suffix='.jpg', delete=False) as temp_file:
        img = Image.new('RGB', (100, 100), color='red')
        img.save(temp_file.name, 'JPEG')
        yield temp_file.name
    
    # Cleanup
    Path(temp_file.name).unlink(missing_ok=True)
```

## Running Tests

### Local Development

```bash
# Set up environment
cp .env.example .env
# Edit .env with your API keys

# Install dependencies
pip install -r requirements.txt

# Run unit tests only
pytest tests/test_*.py -k "not integration"

# Run with verbose output
pytest -v -s

# Run specific test method
pytest tests/test_lego_identifier.py::TestLegoIdentifier::test_encode_image -v
```

### Continuous Integration

For CI/CD environments without API keys:

```bash
# Skip integration tests
pytest -m "not integration"

# Or run with mock data only
pytest tests/test_lego_identifier.py tests/test_valuation_engine.py tests/test_report_generator.py
```

### Performance Testing

```bash
# Run with timing information
pytest --durations=10

# Memory profiling
pytest --profile-svg
```

## Code Quality

### Linting

```bash
# Run pylint on all source code
pylint src/

# Run pylint on specific modules
pylint src/core/lego_identifier.py
pylint src/external/bricklink_client.py

# Check test files
pylint tests/
```

### Code Coverage

```bash
# Generate coverage report
pytest --cov=src --cov-report=html
open htmlcov/index.html

# Coverage with missing lines
pytest --cov=src --cov-report=term-missing

# Target specific modules
pytest --cov=src.core --cov-report=term-missing
```

### Type Checking

```bash
# Run mypy type checking
mypy src/

# Check specific files
mypy src/core/lego_identifier.py src/models/schemas.py
```

## Deployment

### Prerequisites

- Python 3.8+
- SQLite 3
- Required API keys (Anthropic, BrickLink)
- Sufficient disk space for images and reports

### Environment Setup

1. **Clone Repository:**
```bash
git clone <repository-url>
cd minifigure_id
```

2. **Create Virtual Environment:**
```bash
python -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows
```

3. **Install Dependencies:**
```bash
pip install -r requirements.txt
```

4. **Configure Environment:**
```bash
cp .env.example .env
# Edit .env with production values
```

5. **Initialize System:**
```bash
python main.py init
```

### Production Configuration

#### Environment Variables

```env
# Production API Keys
ANTHROPIC_API_KEY=sk-ant-api03-production-key
BRICKLINK_CONSUMER_KEY=prod_consumer_key
BRICKLINK_CONSUMER_SECRET=prod_consumer_secret
BRICKLINK_TOKEN_VALUE=prod_token_value  
BRICKLINK_TOKEN_SECRET=prod_token_secret

# Production Thresholds
MUSEUM_THRESHOLD=500
RARE_THRESHOLD=100

# File Limits
MAX_UPLOAD_SIZE=20971520  # 20MB for production
ALLOWED_IMAGE_TYPES=jpg,jpeg,png,webp,gif

# Rate Limiting - Conservative for production
ANTHROPIC_MAX_TOKENS_PER_MINUTE=20000
ANTHROPIC_MAX_REQUESTS_PER_MINUTE=40

# Database
DATABASE_URL=sqlite:///data/minifigure_valuation.db

# Logging
LOG_LEVEL=INFO
LOG_FILE=/var/log/lego_valuation.log
```

### Deployment Methods

#### 1. Standalone Server Deployment

```bash
# Run web server
python main.py server --host 0.0.0.0 --port 8000

# With production WSGI server
pip install uvicorn gunicorn
gunicorn -w 4 -k uvicorn.workers.UvicornWorker src.api.main:app
```

#### 2. Docker Deployment

**Dockerfile:**
```dockerfile
FROM python:3.9-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .
EXPOSE 8000

CMD ["python", "main.py", "server", "--host", "0.0.0.0", "--port", "8000"]
```

**Build and Run:**
```bash
docker build -t lego-valuation .
docker run -p 8000:8000 -v $(pwd)/data:/app/data lego-valuation
```

#### 3. Cloud Deployment

**For AWS/GCP/Azure:**
- Use managed container services (ECS, Cloud Run, Container Instances)
- Set environment variables through cloud configuration
- Use cloud storage for image persistence
- Configure load balancers for high availability

### Database Migration

For production deployments:

```bash
# Backup existing database
cp data/minifigure_valuation.db data/backup_$(date +%Y%m%d_%H%M%S).db

# Run any migrations
python -c "from src.database.database import init_db; init_db()"
```

### Monitoring Setup

#### Health Check Endpoint

```python
@app.get("/health")
async def health_check():
    return {
        "status": "healthy",
        "timestamp": datetime.utcnow().isoformat(),
        "version": "1.0.0"
    }
```

#### Logging Configuration

```python
import logging
from logging.handlers import RotatingFileHandler

# Configure production logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        RotatingFileHandler('/var/log/lego_valuation.log', maxBytes=10485760, backupCount=5),
        logging.StreamHandler()
    ]
)
```

### Performance Optimization

#### Production Settings

```python
# Rate limiting for production load
ANTHROPIC_MAX_TOKENS_PER_MINUTE = 20000
ANTHROPIC_MAX_REQUESTS_PER_MINUTE = 40

# Image processing optimization
IMAGE_OPTIMIZATION_QUALITY = 85
MAX_IMAGE_DIMENSION = 1024

# Caching settings
EXCHANGE_RATE_CACHE_HOURS = 1
MINIFIGURE_IMAGE_CACHE_DAYS = 30
```

#### Resource Allocation

- **CPU**: 2+ cores recommended for concurrent processing
- **RAM**: 4GB+ for image processing and AI operations
- **Disk**: 50GB+ for images, reports, and database
- **Network**: Stable internet for API calls

### Security Considerations

#### API Key Security

```bash
# Use secrets management in production
export ANTHROPIC_API_KEY=$(aws secretsmanager get-secret-value --secret-id anthropic-api-key --query SecretString --output text)
```

#### File Upload Security

```python
# Validate file types and sizes
ALLOWED_MIME_TYPES = ["image/jpeg", "image/png", "image/webp", "image/gif"]
MAX_UPLOAD_SIZE = 20 * 1024 * 1024  # 20MB

# Sanitize file names
def sanitize_filename(filename: str) -> str:
    return re.sub(r'[^a-zA-Z0-9._-]', '', filename)
```

#### Network Security

- Use HTTPS in production
- Configure firewall rules
- Implement rate limiting at network level
- Use VPN for administrative access

### Backup and Recovery

#### Database Backup

```bash
#!/bin/bash
# backup_database.sh
DATE=$(date +%Y%m%d_%H%M%S)
cp data/minifigure_valuation.db "backups/backup_${DATE}.db"

# Keep last 30 days of backups
find backups/ -name "backup_*.db" -mtime +30 -delete
```

#### File Backup

```bash
#!/bin/bash
# backup_files.sh
tar -czf "backups/files_$(date +%Y%m%d_%H%M%S).tar.gz" data/uploads/ data/reports/
```

### Troubleshooting Deployment

#### Common Issues

1. **API Key Issues:**
```bash
# Test API connectivity
python -c "from src.core.lego_identifier import LegoIdentifier; print('API key valid' if LegoIdentifier().client else 'API key invalid')"
```

2. **Permission Issues:**
```bash
# Fix file permissions
chmod -R 755 data/
chown -R www-data:www-data data/
```

3. **Port Conflicts:**
```bash
# Check port availability
netstat -tlnp | grep :8000
```

4. **Memory Issues:**
```bash
# Monitor memory usage
top -p $(pgrep -f "python main.py server")
```

### Performance Monitoring

#### Key Metrics to Monitor

- API response times
- Token usage rates
- Image processing times
- Database query performance
- Error rates by endpoint
- System resource utilization

#### Monitoring Tools

```python
# Add timing decorators
import time
from functools import wraps

def timed_operation(operation_name: str):
    def decorator(func):
        @wraps(func)
        async def wrapper(*args, **kwargs):
            start_time = time.time()
            result = await func(*args, **kwargs)
            duration = time.time() - start_time
            logger.info(f"{operation_name} completed in {duration:.2f}s")
            return result
        return wrapper
    return decorator
```

---

## Maintenance

### Regular Maintenance Tasks

1. **Clean up old files:**
```bash
# Remove old optimized images (>7 days)
find data/uploads/optimized/ -name "opt_*" -mtime +7 -delete

# Clean up old reports (>30 days)
find data/reports/ -name "*.pdf" -mtime +30 -delete
```

2. **Database maintenance:**
```bash
sqlite3 data/minifigure_valuation.db "VACUUM;"
sqlite3 data/minifigure_valuation.db "ANALYZE;"
```

3. **Log rotation:**
```bash
logrotate /etc/logrotate.d/lego-valuation
```

### Update Procedures

1. **Backup current installation**
2. **Test updates in staging environment**  
3. **Deploy during maintenance window**
4. **Verify all functionality post-deployment**
5. **Monitor for issues in first 24 hours**