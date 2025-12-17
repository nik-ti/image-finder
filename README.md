# Image Finder Microservice

A FastAPI-based microservice that intelligently finds the best images for news articles and tools to be posted on Telegram news channels.

## Features

- **Multiple Image Sources**: Collects images from user-provided candidates, web scraping, and Perplexity API
- **AI-Powered Analysis**: Uses OpenAI GPT-4o-mini Vision to evaluate image quality, relevance, and temporal accuracy
- **Smart Filtering**: Automatically rejects images with heavy watermarks, intrusive ads, or outdated information
- **Telegram Optimization**: Resizes and optimizes images for Telegram's requirements (max 1280px, max 10MB)
- **Caching**: Stores results to avoid redundant processing
- **Fallback Handling**: Returns a default image when no suitable image is found

## Quick Start with Docker

### Prerequisites

- Docker and Docker Compose installed
- OpenAI API key
- Perplexity API key

### Setup

1. Clone the repository:
```bash
git clone https://github.com/nik-ti/image-finder.git
cd image-finder
```

2. Create `.env` file:
```bash
cat > .env << EOF
OPENAI_API_KEY=your_openai_api_key
PERPLEXITY_API_KEY=your_perplexity_api_key
EOF
```

3. Build and run with Docker Compose:
```bash
docker-compose up -d
```

4. Check health:
```bash
curl http://localhost:8001/health
```

## API Usage

### Endpoint

**POST** `/find_image`

### Request Body

```json
{
  "title": "Article title",
  "research": "Article context/description",
  "source_url": "https://example.com/article (optional)",
  "images": ["https://example.com/image1.jpg", "..."] (optional)
}
```

### Response

```json
{
  "image_url": "http://localhost:8001/images/abc123.jpg",
  "original_url": "https://source.com/original.jpg",
  "tool_used": "candidate / site / perplexity / default",
  "image_description": "Description from Vision LLM",
  "format": "jpeg",
  "dimensions": "1280x720",
  "quality_score": 9,
  "temporal_relevance": "current",
  "watermark_status": "minimal",
  "cached": false
}
```

### Example

```bash
curl -X POST http://localhost:8001/find_image \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Bitcoin Surges Past $45,000",
    "research": "Bitcoin has broken through the $45,000 resistance level today.",
    "images": ["https://images.unsplash.com/photo-1518546305927-5a555bb7020d"]
  }'
```

## Development

### Local Installation

1. Install dependencies:
```bash
pip install -r requirements.txt
playwright install chromium
```

2. Run the server:
```bash
python main.py
```

### Configuration

Edit `config.py` to customize:
- Image size limits
- Timeout settings
- Quality thresholds
- API endpoints
- Storage paths

## Architecture

```
┌─────────────────┐
│  FastAPI App    │
└────────┬────────┘
         │
    ┌────┴────┐
    │  Cache  │
    └────┬────┘
         │
    ┌────┴──────────────────┐
    │  Image Collector      │
    ├───────────────────────┤
    │ • User-provided       │
    │ • Web scraping        │
    │ • Perplexity API      │
    └────┬──────────────────┘
         │
    ┌────┴──────────────────┐
    │  Vision Analyzer      │
    │  (GPT-4o-mini)        │
    └────┬──────────────────┘
         │
    ┌────┴──────────────────┐
    │  Image Processor      │
    │  • Download           │
    │  • Resize             │
    │  • Optimize           │
    └────┬──────────────────┘
         │
    ┌────┴──────────────────┐
    │  Storage Manager      │
    └───────────────────────┘
```

## Deployment

### Docker

```bash
# Build image
docker build -t image-finder .

# Run container
docker run -d \
  -p 8001:8001 \
  -e OPENAI_API_KEY=your_key \
  -e PERPLEXITY_API_KEY=your_key \
  --name image-finder \
  image-finder
```

### With Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name find-image.simple-flow.co;

    location / {
        proxy_pass http://localhost:8001;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        
        # Increase timeout for image processing
        proxy_read_timeout 90s;
        proxy_connect_timeout 90s;
    }
}
```

## License

MIT
