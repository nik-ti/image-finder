# Python Microservice Specification: Image Finder for News/Tools

Create a Python microservice using FastAPI to find the best image for a news article or tool. **NO IMAGE GENERATION.**

## Endpoint

**POST** `/find_image`

### Input JSON
```json
{
  "title": "string",
  "research": "string",
  "source_url": "string (optional)",
  "images": ["url1", "url2", "url3"] (optional array)
}
```

## Logic Flow

### 1. Collect Image Candidates (Priority Order):

#### A. User-provided candidates (if `images` exists):
- Add all URLs from `images` array to evaluation pool
- **Priority:** Check these FIRST

#### B. If `source_url` is provided:
- Use **Playwright** → render page (headless mode, wait for load)
- Use **BeautifulSoup** → extract all `<img src>` tags (convert to absolute URLs)
- **Filter criteria:**
  - `width`/`height` > 500px (from attributes)
  - Not a logo (check if `alt`/`class` contains "logo"/"icon"/"favicon")
- Add filtered images to evaluation pool

#### C. If no good candidates yet - Perplexity Search:
- **Perplexity API** with Sonar model:
```python
  {
    "model": "sonar",
    "messages": [
      {
        "role": "user",
        "content": f"Find recent relevant images for: {title}. Context: {research}. Focus on screenshots, charts, interface demos, or event photos. Avoid stock photos, logos, and heavily watermarked images."
      }
    ],
    "return_images": true,
    "recency": "day"  # Last 24 hours only
  }
```
- Extract returned image URLs from response
- Add to evaluation pool

### 2. Image Analysis with Vision Model:

Send all collected images to **Vision LLM** (GPT-4o-mini or Claude with vision):

**Evaluation Criteria:**
```json
{
  "relevance_score": 1-10,
  "temporal_relevance": "check if dates/timestamps are current and match the news timeframe",
  "watermark_severity": "none / minimal / heavy",
  "ad_presence": "none / minimal / intrusive",
  "content_quality": "high / medium / low",
  "is_relevant_to_event": true/false,
  "contains_outdated_info": true/false,
  "reasoning": "brief explanation"
}
```

**Filtering Rules:**
1. **Temporal Check:** For time-sensitive news (price movements, charts, events):
   - Image MUST show current/recent data
   - Reject if dates/timestamps are outdated
   - Example: BTC price news today → chart must show today's date range

2. **Watermark/Ads:**
   - Reject if `watermark_severity: "heavy"`
   - Reject if `ad_presence: "intrusive"`
   - Accept if `watermark_severity: "minimal"` or `"none"`

3. **Relevance:**
   - Must have `relevance_score ≥ 8`
   - Must have `is_relevant_to_event: true`
   - Must have `contains_outdated_info: false`

4. **Quality:**
   - Prefer `content_quality: "high"`

### 3. Image Validation & Processing:

For the best candidate image:

#### A. URL Validation:
```python
async def validate_image_url(url: str) -> bool:
    try:
        response = await httpx.get(url, timeout=10, follow_redirects=True)
        if response.status_code == 200 and response.headers.get('content-type', '').startswith('image/'):
            return True
        return False
    except:
        return False
```

#### B. Image Download & Format Conversion:
```python
from PIL import Image
import io

async def process_image(url: str) -> dict:
    # Download image
    response = await httpx.get(url, timeout=10)
    img = Image.open(io.BytesIO(response.content))
    
    # Convert to RGB if needed (for JPEG)
    if img.mode in ('RGBA', 'LA', 'P'):
        img = img.convert('RGB')
    
    # Telegram size limits: max 10MB, recommended max dimension 1280px
    max_dimension = 1280
    if img.width > max_dimension or img.height > max_dimension:
        img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
    
    # Save as JPEG or PNG (prefer JPEG for smaller size)
    output = io.BytesIO()
    if img.mode == 'RGBA':
        img.save(output, format='PNG', optimize=True)
        format_used = 'png'
    else:
        img.save(output, format='JPEG', quality=90, optimize=True)
        format_used = 'jpeg'
    
    # Upload to temporary storage or return base64/URL
    # (implement your preferred storage solution here)
    
    return {
        "processed_url": "your_storage_url_here",
        "format": format_used,
        "dimensions": f"{img.width}x{img.height}",
        "size_kb": len(output.getvalue()) // 1024
    }
```

### 4. Fallback:
- If all methods fail or no valid images: Return **default fallback image** (pre-processed placeholder URL)

### 5. Caching:
- Store results in `cache.json` file
- **Cache key:** `hash(title + research + source_url + str(candidate_images))`
- Cache includes: original URL, processed URL, metadata
- If match found → validate cached URL still works → return from cache

## Output JSON
```json
{
  "image_url": "processed and validated image url",
  "original_url": "source image url before processing",
  "tool_used": "candidate / site / perplexity / default",
  "image_description": "short description of the image (from vision LLM)",
  "format": "jpeg / png",
  "dimensions": "1280x720",
  "quality_score": 9,
  "temporal_relevance": "current",
  "watermark_status": "minimal"
}
```

## Dependencies
- `fastapi`
- `uvicorn`
- `playwright`
- `beautifulsoup4`
- `openai` (for vision LLM analysis)
- `httpx` (for Perplexity API calls and image downloads)
- `Pillow` (PIL - for image processing and conversion)
- `python-multipart` (for file handling)

## Perplexity API Configuration
```python
PERPLEXITY_CONFIG = {
    "api_url": "https://api.perplexity.ai/chat/completions",
    "model": "sonar",
    "return_images": True,
    "recency": "day",  # Last 24 hours
    "max_tokens": 1000
}
```

## Image Storage Options
Choose one:
1. **S3/Cloud Storage** - Upload processed images, return public URL
2. **Base64 embedding** - Return image as base64 (not recommended for large images)
3. **Temporary CDN** - Use services like imgur API, cloudinary, etc.

## Error Handling
- Invalid URLs → skip and try next candidate
- Download failures → retry once, then skip
- Image processing errors → return original if valid
- Perplexity API errors → log and continue to fallback
- All sources exhausted → return default image
- Timeout limits: 30s per source, 60s total request

## Testing & Optimization
- Test with 10 examples:
  - Time-sensitive news (crypto prices, stock charts) - verify recency filter works
  - Tool announcements with screenshots
  - Event coverage with photos
  - Mix of: with/without `source_url`, with/without `candidate_images`
- **Improvements:**
  - Better temporal relevance detection in vision model
  - Stricter watermark/ad filtering
  - Optimize image compression (quality vs size)
  - Minimize token usage in vision analysis
  - Batch image validation for speed
  - Fine-tune Perplexity query for better image results
- Add comprehensive API documentation (OpenAPI/Swagger)
- Implement robust logging and monitoring

## Example Prompt for Vision Model
```python
vision_prompt = f"""
Analyze these images for news article: "{title}"
Context: {research}
Current date: {datetime.now().strftime('%Y-%m-%d')}

For each image, evaluate:
1. TEMPORAL RELEVANCE: Does it show current/recent data? Check dates, timestamps, chart timeframes.
   - For price/chart news: data must be from today or very recent
   - For event news: must show the actual event, not old stock photos
2. RELEVANCE: Directly related to the news? Score 1-10.
3. WATERMARKS: none/minimal/heavy (reject if heavy)
4. ADS: none/minimal/intrusive (reject if intrusive)
5. QUALITY: high/medium/low
6. OUTDATED INFO: Does it contain old/irrelevant information?

Return JSON array with evaluation for each image.
"""
```

## Flow Summary
```
1. Check candidate_images (if provided) → Vision analysis
   ↓ (if no good match)
2. Scrape source_url (if provided) → Vision analysis
   ↓ (if no good match)
3. Perplexity API (sonar, recency=day, return_images=true) → Vision analysis
   ↓ (if no good match)
4. Return default fallback image

For each step:
- Validate image URLs
- Process & resize images
- Convert to JPEG/PNG
- Cache results
```