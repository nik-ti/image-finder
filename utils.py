"""Utility functions for the image finder service."""
import hashlib
import logging
from urllib.parse import urljoin, urlparse
from typing import Optional

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


def generate_cache_key(title: str, research: str, source_url: Optional[str], images: Optional[list]) -> str:
    """Generate a hash key for caching based on input parameters."""
    content = f"{title}|{research}|{source_url or ''}|{str(images or [])}"
    return hashlib.sha256(content.encode()).hexdigest()


def normalize_url(url: str, base_url: Optional[str] = None) -> str:
    """Normalize and convert relative URLs to absolute URLs."""
    if not url:
        return url
    
    # If it's already absolute, return as-is
    if url.startswith(('http://', 'https://')):
        return url
    
    # If base_url provided, join them
    if base_url:
        return urljoin(base_url, url)
    
    return url


def is_valid_url(url: str) -> bool:
    """Check if a URL is valid."""
    try:
        result = urlparse(url)
        return all([result.scheme, result.netloc])
    except Exception:
        return False


def is_likely_logo_or_icon(img_tag) -> bool:
    """Check if an image tag is likely a logo or icon based on attributes."""
    from config import EXCLUDE_KEYWORDS
    
    # Check alt text
    alt_text = (img_tag.get('alt') or '').lower()
    if any(keyword in alt_text for keyword in EXCLUDE_KEYWORDS):
        return True
    
    # Check class names
    class_names = ' '.join(img_tag.get('class', [])).lower()
    if any(keyword in class_names for keyword in EXCLUDE_KEYWORDS):
        return True
    
    # Check src
    src = (img_tag.get('src') or '').lower()
    if any(keyword in src for keyword in EXCLUDE_KEYWORDS):
        return True
    
    return False


def get_image_dimensions(img_tag) -> tuple:
    """Extract width and height from image tag attributes."""
    width = img_tag.get('width')
    height = img_tag.get('height')
    
    try:
        width = int(width) if width else 0
        height = int(height) if height else 0
    except (ValueError, TypeError):
        width = 0
        height = 0
    
    return width, height
