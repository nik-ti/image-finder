"""Configuration management for the image finder service."""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# API Keys
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PERPLEXITY_API_KEY = os.getenv("PERPLEXITY_API_KEY")

# Validate required keys
if not OPENAI_API_KEY:
    raise ValueError("OPENAI_API_KEY not found in environment variables")
if not PERPLEXITY_API_KEY:
    raise ValueError("PERPLEXITY_API_KEY not found in environment variables")

# Perplexity API Configuration
PERPLEXITY_CONFIG = {
    "api_url": "https://api.perplexity.ai/chat/completions",
    "model": "sonar",
    "return_images": True,
    "recency": "day",  # Last 24 hours
    "max_tokens": 1000
}

# OpenAI Configuration
OPENAI_MODEL = "gpt-4o-mini"

# Image Processing Settings
IMAGE_SETTINGS = {
    "max_dimension": 1280,  # Telegram recommended max
    "max_size_mb": 10,  # Telegram limit
    "jpeg_quality": 90,
    "min_image_size": 1000,  # Minimum width/height for scraped images
}

# Timeout Settings (in seconds)
TIMEOUTS = {
    "per_source": 30,
    "total_request": 60,
    "image_download": 10,
    "playwright_page_load": 15,
}

# Filtering Keywords (for logo/icon detection)
EXCLUDE_KEYWORDS = ["logo", "icon", "favicon", "avatar", "badge", "button"]

# Storage Settings
BASE_DIR = Path(__file__).parent
PROCESSED_IMAGES_DIR = BASE_DIR / "processed_images"
CACHE_FILE = BASE_DIR / "cache.json"

# Create directories if they don't exist
PROCESSED_IMAGES_DIR.mkdir(exist_ok=True)

# Default fallback image URL
DEFAULT_FALLBACK_IMAGE = "https://via.placeholder.com/1280x720/1a1a1a/ffffff?text=No+Image+Available"

# Server Settings
SERVER_HOST = os.getenv("SERVER_HOST", "0.0.0.0")
SERVER_PORT = int(os.getenv("SERVER_PORT", "8001"))

# Public URL for image links
PUBLIC_URL = os.getenv("PUBLIC_URL", "https://find-image.simple-flow.co")
