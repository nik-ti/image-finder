# Image Finder Microservice

An intelligent FastAPI-based microservice that finds the best images for news articles and tools to be posted on Telegram news channels. Uses AI-powered analysis to ensure high-quality, relevant, and temporally accurate images.

## 🎯 Overview

The Image Finder service intelligently selects images by:
1. **Collecting** images from multiple sources (user-provided, web scraping, Perplexity API)
2. **Analyzing** with AI vision models to evaluate quality, relevance, and temporal accuracy
3. **Processing** only when needed (hybrid approach to minimize resource usage)
4. **Optimizing** for Telegram's requirements (max 1280px, max 10MB)

## 🔍 Search Logic & Fallback Strategy

The service employs a smart 3-tier fallback system to identify the best possible image, relaxing constraints only when necessary:

### Tier 1: Strict News Search
- **Goal**: Find high-resolution, recent news visuals.
- **Process**:
    1.  **Attempt 1**: Specific query ("Official press photos", "Charts") | Strict filters (>1000px).
    2.  **Attempt 2**: Flexible query ("Visual event summary") | Strict filters.
- **Recency**: Last 24 hours.

### Tier 2: Low-Res Logo Fallback
- **Trigger**: If Tier 1 fails to find any images.
- **Goal**: Find official company branding/logos.
- **Process**: Search for official vector/brand identities.
- **Filters**: Relaxed Size (>200px) | Recency: Anytime.

### Tier 3: Generic Concept Fallback
- **Trigger**: If Tier 2 fails.
- **Goal**: Find high-quality abstract wallpapers relevant to the topic.
- **Process**: Search for abstract backgrounds (e.g., "AI Technology Background").
- **Filters**: High-Res (>1000px) | Relaxed Relevance | Recency: Anytime.

## 🏗️ Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    FastAPI Application                       │
│                    (main.py - Port 8001)                     │
└───────────────┬─────────────────────────────────────────────┘
                │
        ┌───────┴────────┐
        │  Cache Manager │  (7-day cache with URL validation)
        └───────┬────────┘
                │
    ┌───────────┴──────────────┐
    │   Image Collector        │
    ├──────────────────────────┤
    │ 1. User-provided (P1)    │
    │ 2. Web scraping (P2)     │
    │ 3. Perplexity API (P3)   │
    └───────────┬──────────────┘
                │
    ┌───────────┴──────────────┐
    │   Vision Analyzer        │
    │   (GPT-4o-mini Vision)   │
    ├──────────────────────────┤
    │ • Relevance scoring      │
    │ • Temporal validation    │
    │ • Watermark detection    │
    │ • Quality assessment     │
    └───────────┬──────────────┘
                │
    ┌───────────┴──────────────┐
    │   Image Processor        │
    │   (Hybrid Processing)    │
    ├──────────────────────────┤
    │ • Validate suitability   │
    │ • Download if needed     │
    │ • Resize & optimize      │
    │ • Format conversion      │
    └───────────┬──────────────┘
                │
    ┌───────────┴──────────────┐
    │   Storage Manager        │
    │   (3-day retention)      │
    └──────────────────────────┘
```

## 🧠 AI Models & Components

### Vision Analysis: OpenAI GPT-4o-mini
- **Purpose**: Evaluate image quality, relevance, and temporal accuracy
- **Evaluation Criteria**:
  - Relevance score (1-10)
  - Temporal relevance (current/outdated/not_applicable)
  - Watermark severity (none/minimal/heavy)
  - Ad presence (none/minimal/intrusive)
  - Content quality (high/medium/low)
  - Outdated information detection

### Image Search: Perplexity Sonar
- **Model**: Sonar with image search
- **Recency Filter**: Last 24 hours
- **Purpose**: Find recent, relevant images when other sources fail

### Web Scraping: Playwright + BeautifulSoup
- **Browser**: Chromium (headless)
- **Filtering**: Size >500px, exclude logos/icons
- **Purpose**: Extract images from source articles

## 🚀 Quick Start

### Using Docker (Recommended)

```bash
# Clone repository
git clone https://github.com/nik-ti/image-finder.git
cd image-finder

# Create .env file
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
PUBLIC_URL=https://your-domain.com
EOF

# Build and run
docker compose up -d

# Check health
curl http://localhost:8001/health
```

### Manual Installation

```bash
# Install dependencies
pip install -r requirements.txt
playwright install chromium

# Run server
python main.py
```

## 📡 API Usage

### Endpoint

**POST** `/` or **POST** `/find_image`

### Request

```json
{
  "title": "Article title",
  "research": "Article context/description",
  "source_url": "https://example.com/article (optional)",
  "images": ["https://example.com/image1.jpg"] (optional)
}
```

### Response

```json
{
  "image_url": "https://find-image.simple-flow.co/images/abc123.jpg",
  "original_url": "https://source.com/original.jpg",
  "tool_used": "perplexity",
  "image_description": "AI-generated description",
  "format": "jpeg",
  "dimensions": "1280x720",
  "quality_score": 9,
  "temporal_relevance": "current",
  "watermark_status": "none",
  "cached": false
}
```

### Example

```bash
curl -X POST https://find-image.simple-flow.co/ \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Bitcoin Surges Past $100,000",
    "research": "Bitcoin reaches new all-time high amid institutional adoption",
    "images": ["https://example.com/bitcoin-chart.jpg"]
  }'
```

## 🔧 Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `OPENAI_API_KEY` | Required | OpenAI API key for vision analysis |
| `PERPLEXITY_API_KEY` | Required | Perplexity API key for image search |
| `PUBLIC_URL` | `https://find-image.simple-flow.co` | Public URL for image links |
| `SERVER_HOST` | `0.0.0.0` | Server bind address |
| `SERVER_PORT` | `8001` | Server port |

### Image Settings (config.py)

```python
IMAGE_SETTINGS = {
    "max_dimension": 1280,      # Telegram max recommended
    "max_size_mb": 10,          # Telegram limit
    "jpeg_quality": 90,         # Quality for JPEG compression
    "min_image_size": 500,      # Min size for scraped images
}
```

### Timeout Settings

```python
TIMEOUTS = {
    "per_source": 30,           # Timeout per image source
    "total_request": 60,        # Total request timeout
    "image_download": 10,       # Image download timeout
    "playwright_page_load": 15, # Page load timeout
}
```

## 💾 Storage & Cleanup

### Hybrid Processing
The service uses a **hybrid approach** to minimize resource usage:

1. **Validate First**: Check if image meets Telegram requirements
2. **Use Original**: If suitable, return original URL (no processing/storage)
3. **Process Only When Needed**: Download and optimize only problematic images

### Automatic Cleanup
- **Retention Period**: 3 days
- **Cleanup Schedule**: Daily at 3:00 AM (cron job)
- **Manual Cleanup**: `docker exec image-finder python -c "from storage import ImageStorage; ImageStorage().delete_old_images()"`

### Cron Job
```bash
# Installed automatically during deployment
0 3 * * * /root/Systems/image_finder/cleanup_images.sh >> /var/log/image_finder_cleanup.log 2>&1
```

## 🎯 Filtering Rules

Images are filtered based on:

1. **Temporal Relevance**
   - For time-sensitive news: data must be current
   - Charts/graphs must show recent dates
   - Event photos must be from the actual event

2. **Quality Thresholds**
   - Relevance score ≥ 8/10
   - Must be relevant to event
   - No outdated information

3. **Watermarks & Ads**
   - Reject if watermark severity = "heavy"
   - Reject if ad presence = "intrusive"
   - Accept "minimal" or "none"

4. **Content Quality**
   - Prefer "high" quality
   - Accept "medium" quality
   - Reject "low" quality

## 🤖 AI Logic & Cost Analysis

The system uses a multi-step AI pipeline to ensure image quality. Below is the breakdown of API calls per request:

### Standard Flow (Success on Tier 1)
1.  **Search**: 1 Perplexity Call (News Search).
2.  **Analysis**: 1 OpenAI Vision Call (Batched analysis of top 5 images).
3.  **Verification**: 1 OpenAI Vision Call (Strict check on winner).
*   **Total**: ~3 LLM Calls.

### Worst Case (Fallback to Tier 3)
If Tier 1 and Tier 2 fail:
1.  **Tier 1**: 2 Perplexity Calls (Retry) + 2 Vision Calls.
2.  **Tier 2**: 1 Perplexity Call (Logo) + 1 Vision Call.
3.  **Tier 3**: 2 Perplexity Calls (Generic) + 2 Vision Calls.
*   **Total**: ~10-12 LLM Calls (Rare).

### Why this structure?
- **Batch Analysis**: We analyze 5 images in a single GPT-4o-mini call to save costs.
- **Fail-Fast Verification**: We only verify the *winning* candidate.
- **Blind Fallback**: If OpenAI imposes rate limits (429), we switch to "Blind Mode" (0 Vision calls) to ensure the service never crashes.

## 📊 Performance

- **Average Response Time**: 5-15 seconds
- **Cache Hit Rate**: ~30% (reduces API costs)
- **Storage Usage**: Minimal (hybrid processing + 3-day cleanup)
- **Bandwidth**: Optimized (only process when needed)

## 🔍 Monitoring

### Health Check
```bash
curl https://find-image.simple-flow.co/health
```

### Container Logs
```bash
docker logs image-finder -f
```

### Resource Usage
```bash
docker stats image-finder
```

### Cleanup Logs
```bash
tail -f /var/log/image_finder_cleanup.log
```

## 🛠️ Development

### Project Structure

```
image_finder/
├── main.py                 # FastAPI application
├── image_collector.py      # Multi-source image collection
├── vision_analyzer.py      # AI-powered image analysis
├── image_processor.py      # Image validation & processing
├── cache_manager.py        # Result caching
├── storage.py              # Image storage & cleanup
├── config.py               # Configuration
├── models.py               # Pydantic models
├── utils.py                # Utility functions
├── Dockerfile              # Docker configuration
├── docker-compose.yml      # Docker Compose setup
├── cleanup_images.sh       # Cleanup cron script
└── requirements.txt        # Python dependencies
```

### Key Dependencies

- **FastAPI**: Web framework
- **Uvicorn**: ASGI server
- **Playwright**: Headless browser for web scraping
- **BeautifulSoup4**: HTML parsing
- **OpenAI**: Vision LLM analysis
- **Pillow**: Image processing
- **httpx**: HTTP client

## 🚢 Deployment

### Production URL
https://find-image.simple-flow.co

### Reverse Proxy (Caddy)
```
find-image.simple-flow.co {
    reverse_proxy localhost:8001
}
```

### Auto-restart
The container is configured with `restart: unless-stopped` for automatic recovery.

### Updates
```bash
cd /root/Systems/image_finder
git pull origin main
docker compose down
docker compose build
docker compose up -d
```

## 🔒 Security

- API keys stored in `.env` (not committed to git)
- HTTPS enforced via Caddy
- Input validation via Pydantic models
- Timeout limits to prevent abuse
- Resource limits via Docker

## 📈 Future Enhancements

- [ ] Cloud storage integration (S3/R2)
- [ ] Rate limiting
- [ ] Prometheus metrics
- [ ] Image CDN integration
- [ ] Advanced caching strategies
- [ ] Multi-language support

