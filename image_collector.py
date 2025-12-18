"""Image collector from multiple sources."""
import asyncio
from typing import List, Optional
from bs4 import BeautifulSoup
from playwright.async_api import async_playwright, TimeoutError as PlaywrightTimeout
import httpx

from config import (
    PERPLEXITY_CONFIG, PERPLEXITY_API_KEY, IMAGE_SETTINGS, 
    TIMEOUTS, EXCLUDE_KEYWORDS
)
from utils import logger, normalize_url, is_likely_logo_or_icon, get_image_dimensions


class ImageCollector:
    """Collects image candidates from multiple sources."""
    
    async def collect_all(
        self, 
        title: str,
        research: str,
        source_url: Optional[str] = None,
        candidate_images: Optional[List[str]] = None
    ) -> List[str]:
        """
        Collect images from all available sources.
        
        Args:
            title: Article title
            research: Research context
            source_url: Optional source URL to scrape
            candidate_images: Optional user-provided images
        
        Returns:
            List of image URLs
        """
        all_images = []
        
        # Priority 1: User-provided candidates
        if candidate_images:
            logger.info(f"Using {len(candidate_images)} user-provided images")
            all_images.extend(candidate_images)
        
        # Priority 2: Scrape source URL
        if source_url:
            try:
                scraped_images = await asyncio.wait_for(
                    self.scrape_source_url(source_url),
                    timeout=TIMEOUTS['per_source']
                )
                logger.info(f"Scraped {len(scraped_images)} images from source URL")
                all_images.extend(scraped_images)
            except asyncio.TimeoutError:
                logger.warning(f"Timeout scraping source URL: {source_url}")
            except Exception as e:
                logger.error(f"Error scraping source URL: {e}")
        
        # Priority 3: Perplexity search (only if we don't have enough candidates)
        if len(all_images) < 5:
            try:
                perplexity_images = await asyncio.wait_for(
                    self.search_perplexity(title, research),
                    timeout=TIMEOUTS['per_source']
                )
                logger.info(f"Found {len(perplexity_images)} images from Perplexity")
                all_images.extend(perplexity_images)
            except asyncio.TimeoutError:
                logger.warning("Timeout searching Perplexity")
            except Exception as e:
                logger.error(f"Error searching Perplexity: {e}")
        
        # Remove duplicates while preserving order
        unique_images = []
        seen = set()
        for img in all_images:
            if img not in seen:
                unique_images.append(img)
                seen.add(img)
        
        logger.info(f"Collected {len(unique_images)} unique images total")
        return unique_images
    
    async def scrape_source_url(self, url: str) -> List[str]:
        """
        Scrape images from source URL using Playwright and BeautifulSoup.
        
        Args:
            url: Source URL to scrape
        
        Returns:
            List of filtered image URLs
        """
        images = []
        
        try:
            async with async_playwright() as p:
                browser = await p.chromium.launch(headless=True)
                page = await browser.new_page()
                
                # Navigate to page
                await page.goto(url, wait_until='networkidle', timeout=TIMEOUTS['playwright_page_load'] * 1000)
                
                # Get page content
                content = await page.content()
                await browser.close()
                
                # Parse with BeautifulSoup
                soup = BeautifulSoup(content, 'lxml')
                
                # Find all img tags
                img_tags = soup.find_all('img')
                
                for img_tag in img_tags:
                    # Skip if likely logo/icon
                    if is_likely_logo_or_icon(img_tag):
                        continue
                    
                    # Get image URL
                    img_url = img_tag.get('src') or img_tag.get('data-src')
                    if not img_url:
                        continue
                    
                    # Normalize URL
                    img_url = normalize_url(img_url, url)
                    
                    # Check dimensions
                    width, height = get_image_dimensions(img_tag)
                    min_size = IMAGE_SETTINGS['min_image_size']
                    
                    # If dimensions are available, filter by size
                    if width > 0 and height > 0:
                        if width >= min_size and height >= min_size:
                            images.append(img_url)
                    else:
                        # If no dimensions, include it (will be validated later)
                        images.append(img_url)
                
        except PlaywrightTimeout:
            logger.warning(f"Playwright timeout loading {url}")
        except Exception as e:
            logger.error(f"Error scraping {url}: {e}")
        
        return images
    
    async def search_perplexity(self, title: str, research: str, retry_attempt: int = 1) -> List[str]:
        """
        Search for images using Perplexity API.
        
        Args:
            title: Article title
            research: Research context
            retry_attempt: Attempt number (1 or 2) to vary the query
        
        Returns:
            List of image URLs from Perplexity
        """
        images = []
        
        try:
            # Build search query - vary based on retry attempt
            if retry_attempt == 1:
                query = (
                    f"Find recent relevant images for: {title}. "
                    f"Context: {research}. "
                    f"Focus on screenshots, charts, interface demos, or event photos. "
                    f"Avoid stock photos, logos, and heavily watermarked images."
                )
            else:
                # Second attempt: broaden search with alternative phrasing
                query = (
                    f"Search for high-quality visual content related to: {title}. "
                    f"Background: {research}. "
                    f"Prioritize: infographics, data visualizations, product images, or news photos. "
                    f"Exclude: generic stock images, company logos, low-resolution thumbnails."
                )
            
            # Make API request
            headers = {
                "Authorization": f"Bearer {PERPLEXITY_API_KEY}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": PERPLEXITY_CONFIG['model'],
                "messages": [
                    {
                        "role": "user",
                        "content": query
                    }
                ],
                "return_images": PERPLEXITY_CONFIG['return_images'],
                "search_recency_filter": PERPLEXITY_CONFIG['recency'],
                "max_tokens": PERPLEXITY_CONFIG['max_tokens']
            }
            
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    PERPLEXITY_CONFIG['api_url'],
                    json=payload,
                    headers=headers,
                    timeout=TIMEOUTS['per_source']
                )
                
                if response.status_code == 200:
                    data = response.json()
                    
                    # Extract images from response
                    # Perplexity returns images in the response
                    raw_images = []
                    if 'images' in data:
                        raw_images = data['images']
                    elif 'choices' in data and len(data['choices']) > 0:
                        # Sometimes images are in the message content
                        message = data['choices'][0].get('message', {})
                        if 'images' in message:
                            raw_images = message['images']
                    
                    # Extract URLs from images (they might be dicts or strings)
                    for img in raw_images:
                        if isinstance(img, str):
                            images.append(img)
                        elif isinstance(img, dict):
                            # Try to extract URL from dict
                            url = img.get('url') or img.get('src') or img.get('image_url')
                            if url:
                                images.append(url)
                    
                    logger.info(f"Perplexity API returned {len(images)} images")
                else:
                    logger.warning(f"Perplexity API error: {response.status_code} - {response.text}")
        
        except Exception as e:
            logger.error(f"Error calling Perplexity API: {e}")
        
        return images
