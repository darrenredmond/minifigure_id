# Troubleshooting Guide

This guide provides solutions to common issues encountered with the LEGO Valuation System.

## Common Issues and Solutions

### 1. API Rate Limiting Issues

#### Problem: 429 Rate Limit Exceeded Errors
```
anthropic.RateLimitError: 429 Too Many Requests
```

**Causes:**
- Exceeding 30,000 input tokens per minute
- Too many concurrent requests
- Rate limiter not properly configured

**Solutions:**

1. **Check Rate Limiter Configuration:**
```python
# Verify rate limiter settings
from src.utils.rate_limiter import AnthropicRateLimiter

rate_limiter = AnthropicRateLimiter(
    max_input_tokens_per_minute=25000,  # Under 30k limit
    max_requests_per_minute=50,
    window_seconds=60
)
```

2. **Monitor Token Usage:**
```bash
# Enable debug logging to see token consumption
export LOG_LEVEL=DEBUG
python main.py process image.jpg
```

3. **Reduce Processing Load:**
```python
# Process images sequentially instead of in parallel
for image in images:
    result = await identifier.identify_lego_items(image)
    time.sleep(2)  # Add delays between requests
```

#### Problem: Slow Processing Due to Rate Limiting
**Solutions:**
- Increase `window_seconds` for more granular control
- Implement priority queuing for urgent requests
- Use multiple API keys with load balancing

---

### 2. Image Processing Issues

#### Problem: "Image file not found" Error
```
FileNotFoundError: [Errno 2] No such file or directory: '/path/to/image.jpg'
```

**Solutions:**

1. **Verify File Path:**
```bash
# Check if file exists
ls -la /path/to/image.jpg

# Use absolute paths
python main.py process /full/absolute/path/to/image.jpg
```

2. **Check File Permissions:**
```bash
chmod 644 /path/to/image.jpg
```

3. **Verify Image Format:**
```bash
file /path/to/image.jpg  # Should show image type
```

#### Problem: "Unsupported image format" Error
**Supported formats:** JPG, JPEG, PNG, WebP, GIF

**Solutions:**

1. **Convert Image Format:**
```python
from PIL import Image

# Convert to JPEG
img = Image.open('input.bmp')
img.convert('RGB').save('output.jpg', 'JPEG')
```

2. **Update Settings for New Formats:**
```env
# In .env file
ALLOWED_IMAGE_TYPES=jpg,jpeg,png,webp,gif,bmp
```

#### Problem: "Image too large" Error
**Solutions:**

1. **Resize Image:**
```python
from PIL import Image

img = Image.open('large_image.jpg')
img.thumbnail((1024, 1024), Image.Resampling.LANCZOS)
img.save('resized_image.jpg', optimize=True, quality=85)
```

2. **Increase Size Limit:**
```env
# In .env file
MAX_UPLOAD_SIZE=20971520  # 20MB
```

---

### 3. API Authentication Issues

#### Problem: Invalid Anthropic API Key
```
AuthenticationError: Invalid API key
```

**Solutions:**

1. **Verify API Key Format:**
```bash
# Should start with sk-ant-api03-
echo $ANTHROPIC_API_KEY | head -c 20
```

2. **Check Environment Variables:**
```bash
# Verify key is set
env | grep ANTHROPIC_API_KEY

# Test key validity
python -c "
from anthropic import Anthropic
client = Anthropic()
print('API key is valid')
"
```

3. **Reset API Key:**
- Visit https://console.anthropic.com/
- Generate new API key
- Update .env file

#### Problem: BrickLink API Authentication Failed
```
requests.exceptions.HTTPError: 401 Client Error: Unauthorized
```

**Solutions:**

1. **Verify All BrickLink Credentials:**
```bash
# Check all required variables are set
env | grep BRICKLINK_
```

2. **Test OAuth Signature:**
```python
from src.external.bricklink_client import BrickLinkClient

client = BrickLinkClient()
try:
    result = client.search_items("MINIFIG", "Luke")
    print("Authentication successful")
except Exception as e:
    print(f"Authentication failed: {e}")
```

3. **Check IP Whitelist:**
- BrickLink requires IP whitelisting
- Add your server IP to BrickLink developer console
- Verify current IP: `curl ifconfig.me`

---

### 4. Database Issues

#### Problem: Database File Not Found
```
sqlite3.OperationalError: unable to open database file
```

**Solutions:**

1. **Initialize Database:**
```bash
python main.py init
```

2. **Check Permissions:**
```bash
ls -la data/minifigure_valuation.db
chmod 666 data/minifigure_valuation.db
```

3. **Verify Directory Structure:**
```bash
mkdir -p data/uploads data/reports data/minifigure_images
```

#### Problem: Database Corruption
```
sqlite3.DatabaseError: database disk image is malformed
```

**Solutions:**

1. **Backup and Repair:**
```bash
# Create backup
cp data/minifigure_valuation.db data/backup.db

# Attempt repair
sqlite3 data/minifigure_valuation.db "PRAGMA integrity_check;"
sqlite3 data/minifigure_valuation.db ".recover" | sqlite3 data/recovered.db
```

2. **Restore from Backup:**
```bash
cp data/backup.db data/minifigure_valuation.db
```

---

### 5. Web Interface Issues

#### Problem: Server Won't Start
```
OSError: [Errno 48] Address already in use
```

**Solutions:**

1. **Check Port Usage:**
```bash
lsof -i :8000
netstat -tulpn | grep :8000
```

2. **Kill Existing Process:**
```bash
pkill -f "python main.py server"
```

3. **Use Different Port:**
```bash
python main.py server --port 8080
```

#### Problem: File Upload Fails
**Solutions:**

1. **Check File Size:**
```bash
ls -lh image.jpg  # Compare to MAX_UPLOAD_SIZE
```

2. **Verify Upload Directory Permissions:**
```bash
chmod 755 data/uploads/
```

3. **Check Disk Space:**
```bash
df -h .
```

---

### 6. Report Generation Issues

#### Problem: PDF Generation Failed
```
ImportError: No module named 'reportlab'
```

**Solutions:**

1. **Install Missing Dependencies:**
```bash
pip install reportlab pillow
```

2. **Verify Font Availability:**
```python
from reportlab.pdfbase import pdfmetrics
print(pdfmetrics.getRegisteredFontNames())
```

#### Problem: HTML Reports Missing Images
**Solutions:**

1. **Check Image Paths:**
```python
# Verify image exists before embedding
import os
if os.path.exists(image_path):
    # Embed image
    pass
```

2. **Base64 Encoding Issues:**
```python
import base64

# Test base64 encoding
with open('image.jpg', 'rb') as f:
    encoded = base64.b64encode(f.read()).decode()
    print(f"Encoded length: {len(encoded)}")
```

---

### 7. Performance Issues

#### Problem: Slow Image Processing
**Solutions:**

1. **Optimize Image Before Processing:**
```python
from src.utils.image_processor import ImageProcessor

processor = ImageProcessor()
optimized_path = processor.optimize_image_for_ai(image_path)
```

2. **Monitor Resource Usage:**
```bash
top -p $(pgrep -f "python main.py")
iostat 1
```

3. **Implement Caching:**
```python
# Cache processed results
import functools

@functools.lru_cache(maxsize=128)
def cached_identification(image_hash):
    # Implementation
    pass
```

#### Problem: High Memory Usage
**Solutions:**

1. **Process Images Individually:**
```python
# Instead of loading all images at once
for image_path in image_paths:
    result = process_single_image(image_path)
    # Clean up immediately
    del result
```

2. **Limit Concurrent Processing:**
```python
import asyncio

semaphore = asyncio.Semaphore(2)  # Max 2 concurrent processes

async def limited_process(image_path):
    async with semaphore:
        return await process_image(image_path)
```

---

### 8. Configuration Issues

#### Problem: Environment Variables Not Loading
**Solutions:**

1. **Verify .env File Location:**
```bash
ls -la .env
cat .env | grep ANTHROPIC_API_KEY
```

2. **Check Loading Logic:**
```python
from config.settings import settings
print(settings.anthropic_api_key[:10] + "...")  # First 10 chars
```

3. **Manual Environment Setup:**
```bash
export ANTHROPIC_API_KEY=sk-ant-api03-...
export BRICKLINK_CONSUMER_KEY=your_key
```

#### Problem: Wrong Configuration Values
**Solutions:**

1. **Validate Settings:**
```python
from config.settings import settings

assert settings.museum_threshold > 0
assert settings.max_upload_size > 0
assert len(settings.allowed_image_types) > 0
```

---

## Debugging Techniques

### 1. Enable Verbose Logging

```python
import logging

logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)

# Enable specific loggers
logging.getLogger('src.core.lego_identifier').setLevel(logging.DEBUG)
logging.getLogger('src.external.bricklink_client').setLevel(logging.DEBUG)
```

### 2. Test Individual Components

```python
# Test image encoding
from src.core.lego_identifier import LegoIdentifier
identifier = LegoIdentifier()
encoded = identifier._encode_image('test_image.jpg')
print(f"Image encoded successfully: {len(encoded)} characters")

# Test BrickLink connection
from src.external.bricklink_client import BrickLinkClient
client = BrickLinkClient()
results = client.search_items("MINIFIG", "test")
print(f"BrickLink connection: {'OK' if isinstance(results, list) else 'Failed'}")
```

### 3. API Response Debugging

```python
# Log API responses
import json

def debug_api_response(response):
    print("=== API Response Debug ===")
    print(f"Status: {response.status_code}")
    print(f"Headers: {dict(response.headers)}")
    try:
        print(f"Content: {json.dumps(response.json(), indent=2)}")
    except:
        print(f"Content: {response.text[:500]}...")
    print("=========================")
```

### 4. Memory and Performance Profiling

```bash
# Install profiling tools
pip install memory-profiler line-profiler

# Profile memory usage
python -m memory_profiler main.py process image.jpg

# Profile line-by-line performance
kernprof -l -v main.py process image.jpg
```

---

## Error Codes and Messages

### System Error Codes

| Code | Message | Solution |
|------|---------|----------|
| `ERR_001` | API rate limit exceeded | Implement rate limiting |
| `ERR_002` | Invalid image format | Convert to supported format |
| `ERR_003` | File too large | Resize or compress image |
| `ERR_004` | Authentication failed | Check API keys |
| `ERR_005` | Database connection failed | Initialize database |
| `ERR_006` | Image processing failed | Check image integrity |
| `ERR_007` | Report generation failed | Check dependencies |
| `ERR_008` | Network timeout | Check internet connection |

### API Error Response Format

```json
{
  "error": "ERR_001",
  "message": "API rate limit exceeded",
  "details": {
    "current_usage": 28500,
    "limit": 30000,
    "reset_time": "2025-01-15T10:35:00Z"
  },
  "suggestion": "Wait 120 seconds before retrying"
}
```

---

## Getting Help

### 1. Check Logs First

```bash
# Application logs
tail -f lego_valuation.log

# System logs (if using systemd)
journalctl -u lego-valuation -f
```

### 2. Test with Minimal Example

```python
# Minimal working example
import asyncio
from src.core.lego_identifier import LegoIdentifier

async def test_basic_functionality():
    identifier = LegoIdentifier()
    # Use a simple test image
    result = await identifier.identify_lego_items('test_image.jpg')
    print(f"Confidence: {result.confidence_score}")
    print(f"Description: {result.description}")

asyncio.run(test_basic_functionality())
```

### 3. Collect System Information

```bash
# System info script
cat > debug_info.sh << 'EOF'
#!/bin/bash
echo "=== System Information ==="
python --version
pip list | grep -E "(anthropic|requests|pillow|reportlab)"
echo "=== Environment Variables ==="
env | grep -E "(ANTHROPIC|BRICKLINK)" | sed 's/=.*/=***/'
echo "=== File Permissions ==="
ls -la data/
echo "=== Disk Space ==="
df -h .
echo "=== Process Information ==="
ps aux | grep python
EOF
chmod +x debug_info.sh
./debug_info.sh
```

### 4. Create Minimal Reproduction Case

When reporting issues, provide:

1. **Error message** (full stack trace)
2. **Steps to reproduce**
3. **System information** (from debug_info.sh)
4. **Configuration** (anonymized .env values)
5. **Sample image** (if issue is image-specific)

### 5. Recovery Procedures

#### Complete System Reset

```bash
# Backup important data
cp data/minifigure_valuation.db backup/
cp -r data/uploads backup/

# Clean slate
rm -rf data/*
python main.py init

# Restore data if needed
cp backup/minifigure_valuation.db data/
cp -r backup/uploads data/
```

#### Emergency Recovery

If system is completely broken:

```bash
# Minimal working setup
mkdir -p data/{uploads,reports,minifigure_images}
python -c "
from src.database.database import init_db
init_db()
print('Database initialized')
"

# Test basic functionality
python -c "
import asyncio
from src.core.lego_identifier import LegoIdentifier
print('System components can be imported successfully')
"
```

---

## Prevention Best Practices

### 1. Regular Monitoring

```bash
# Daily health check script
#!/bin/bash
curl -f http://localhost:8000/health || echo "Service down"
df -h . | awk 'NR==2 {if($5 > 80) print "Disk space low: " $5}'
```

### 2. Automated Backups

```bash
# Backup script
#!/bin/bash
DATE=$(date +%Y%m%d_%H%M%S)
tar -czf "backups/system_backup_${DATE}.tar.gz" data/ .env
find backups/ -name "system_backup_*.tar.gz" -mtime +7 -delete
```

### 3. Configuration Validation

```python
# Startup validation
def validate_configuration():
    from config.settings import settings
    
    assert settings.anthropic_api_key, "Anthropic API key required"
    assert settings.max_upload_size > 0, "Max upload size must be positive"
    assert Path("data").exists(), "Data directory must exist"
    
    print("Configuration validation passed")

if __name__ == "__main__":
    validate_configuration()
```

### 4. Testing in Staging

Always test changes in a staging environment:

```bash
# Staging environment setup
cp .env .env.staging
sed -i 's/prod_/staging_/g' .env.staging
python main.py --env staging server --port 8001
```