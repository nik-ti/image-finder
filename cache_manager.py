"""Cache manager for storing and retrieving image search results."""
import json
import asyncio
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime, timedelta
import httpx

from config import CACHE_FILE
from utils import logger, generate_cache_key


class CacheManager:
    """Manages caching of image search results."""
    
    def __init__(self, cache_file: Path = CACHE_FILE):
        self.cache_file = cache_file
        self._cache: Dict[str, Any] = {}
        self._load_cache()
    
    def _load_cache(self):
        """Load cache from file."""
        if self.cache_file.exists():
            try:
                with open(self.cache_file, 'r') as f:
                    self._cache = json.load(f)
                logger.info(f"Loaded {len(self._cache)} items from cache")
            except Exception as e:
                logger.error(f"Error loading cache: {e}")
                self._cache = {}
        else:
            self._cache = {}
    
    def _save_cache(self):
        """Save cache to file."""
        try:
            with open(self.cache_file, 'w') as f:
                json.dump(self._cache, f, indent=2)
            logger.info(f"Saved {len(self._cache)} items to cache")
        except Exception as e:
            logger.error(f"Error saving cache: {e}")
    
    async def _validate_url(self, url: str) -> bool:
        """Validate that a cached URL still works."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.head(url, timeout=5, follow_redirects=True)
                return response.status_code == 200
        except Exception as e:
            logger.debug(f"URL validation failed for {url}: {e}")
            return False
    
    async def get(self, title: str, research: str, source_url: Optional[str], 
                  images: Optional[list]) -> Optional[Dict[str, Any]]:
        """Get cached result if available and valid."""
        cache_key = generate_cache_key(title, research, source_url, images)
        
        if cache_key not in self._cache:
            return None
        
        cached_data = self._cache[cache_key]
        
        # Check if cache is too old (older than 7 days)
        cached_time = datetime.fromisoformat(cached_data.get('cached_at', '2000-01-01'))
        if datetime.now() - cached_time > timedelta(days=7):
            logger.info(f"Cache expired for key {cache_key[:8]}...")
            del self._cache[cache_key]
            self._save_cache()
            return None
        
        # Validate that the URL still works
        image_url = cached_data.get('image_url')
        if image_url and await self._validate_url(image_url):
            logger.info(f"Cache hit for key {cache_key[:8]}...")
            cached_data['cached'] = True
            return cached_data
        else:
            logger.info(f"Cached URL no longer valid for key {cache_key[:8]}...")
            del self._cache[cache_key]
            self._save_cache()
            return None
    
    def set(self, title: str, research: str, source_url: Optional[str], 
            images: Optional[list], result: Dict[str, Any]):
        """Store result in cache."""
        cache_key = generate_cache_key(title, research, source_url, images)
        
        result['cached_at'] = datetime.now().isoformat()
        self._cache[cache_key] = result
        self._save_cache()
        logger.info(f"Cached result for key {cache_key[:8]}...")
