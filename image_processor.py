"""Image processor for validation, download, and optimization."""
import io
from typing import Optional, Dict, Any, Tuple
import httpx
from PIL import Image

from config import IMAGE_SETTINGS, TIMEOUTS
from utils import logger, is_valid_url


class ImageProcessor:
    """Handles image validation, download, and processing."""
    
    async def validate_image_url(self, url: str) -> bool:
        """
        Validate that a URL points to an accessible image.
        
        Args:
            url: Image URL to validate
        
        Returns:
            True if URL is valid and accessible
        """
        if not is_valid_url(url):
            return False
        
        try:
            async with httpx.AsyncClient() as client:
                response = await client.head(
                    url, 
                    timeout=TIMEOUTS['image_download'],
                    follow_redirects=True
                )
                
                if response.status_code == 200:
                    content_type = response.headers.get('content-type', '')
                    
                    # Check content-type first
                    if content_type.startswith('image/'):
                        return True
                    
                    # Fallback: check file extension for common image formats
                    # (Some servers return application/octet-stream for images)
                    image_extensions = ('.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.svg')
                    if any(url.lower().endswith(ext) for ext in image_extensions):
                        return True
                    
                    return False
                
                return False
        except Exception as e:
            logger.debug(f"URL validation failed for {url}: {e}")
            return False
    
    async def download_image(self, url: str) -> Optional[bytes]:
        """
        Download image from URL.
        
        Args:
            url: Image URL
        
        Returns:
            Image bytes or None if download fails
        """
        try:
            async with httpx.AsyncClient() as client:
                response = await client.get(
                    url,
                    timeout=TIMEOUTS['image_download'],
                    follow_redirects=True
                )
                
                if response.status_code == 200:
                    return response.content
                else:
                    logger.warning(f"Failed to download image from {url}: status {response.status_code}")
                    return None
        except Exception as e:
            logger.error(f"Error downloading image from {url}: {e}")
            return None
    
    def process_image(self, image_data: bytes) -> Tuple[bytes, str, str, int]:
        """
        Process image: convert format, resize, optimize.
        
        Args:
            image_data: Raw image bytes
        
        Returns:
            Tuple of (processed_bytes, format, dimensions, size_kb)
        """
        try:
            # Open image
            img = Image.open(io.BytesIO(image_data))
            
            # Check minimum dimensions for Telegram posts
            min_dimension = IMAGE_SETTINGS['min_image_size']
            if img.width < min_dimension and img.height < min_dimension:
                logger.warning(f"Image too small: {img.width}x{img.height} (neither dimension >= {min_dimension})")
                return None
            
            # Convert to RGB if needed (for JPEG)
            original_mode = img.mode
            if img.mode in ('RGBA', 'LA', 'P'):
                # Keep RGBA for PNG, convert others to RGB
                if img.mode == 'RGBA':
                    pass  # Keep as-is for PNG
                else:
                    img = img.convert('RGB')
            elif img.mode not in ('RGB', 'RGBA'):
                img = img.convert('RGB')
            
            # Resize if needed (Telegram limits)
            max_dimension = IMAGE_SETTINGS['max_dimension']
            if img.width > max_dimension or img.height > max_dimension:
                img.thumbnail((max_dimension, max_dimension), Image.Resampling.LANCZOS)
                logger.info(f"Resized image from original to {img.width}x{img.height}")
            
            # Save with optimization
            output = io.BytesIO()
            if img.mode == 'RGBA':
                img.save(output, format='PNG', optimize=True)
                format_used = 'png'
            else:
                img.save(output, format='JPEG', quality=IMAGE_SETTINGS['jpeg_quality'], optimize=True)
                format_used = 'jpeg'
            
            processed_bytes = output.getvalue()
            dimensions = f"{img.width}x{img.height}"
            size_kb = len(processed_bytes) // 1024
            
            logger.info(f"Processed image: {format_used}, {dimensions}, {size_kb}KB")
            
            return processed_bytes, format_used, dimensions, size_kb
            
        except Exception as e:
            logger.error(f"Error processing image: {e}")
            return None
    
    async def validate_image_suitability(self, url: str) -> dict:
        """
        Check if an image meets Telegram requirements without downloading.
        
        Args:
            url: Image URL
        
        Returns:
            Dict with 'suitable' bool and 'reason' string
        """
        try:
            async with httpx.AsyncClient() as client:
                # HEAD request to get headers without downloading
                response = await client.head(
                    url,
                    timeout=TIMEOUTS['image_download'],
                    follow_redirects=True
                )
                
                if response.status_code != 200:
                    return {'suitable': False, 'reason': 'URL not accessible'}
                
                # Check content type
                content_type = response.headers.get('content-type', '')
                if not content_type.startswith('image/'):
                    return {'suitable': False, 'reason': 'Not an image'}
                
                # Check file size if available
                content_length = response.headers.get('content-length')
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > IMAGE_SETTINGS['max_size_mb']:
                        return {'suitable': False, 'reason': f'Too large ({size_mb:.1f}MB)'}
                
                # If we can't determine size or dimensions from headers,
                # we'll need to download to check - mark as needs_validation
                return {'suitable': True, 'reason': 'Appears suitable', 'needs_validation': True}
                
        except Exception as e:
            logger.debug(f"Validation failed for {url}: {e}")
            return {'suitable': False, 'reason': str(e)}
    
    async def process_image_url(self, url: str, force_process: bool = False) -> Optional[Dict[str, Any]]:
        """
        Download and process an image from URL, or return original if suitable.
        
        Args:
            url: Image URL
            force_process: If True, always process the image
        
        Returns:
            Dict with processed image data or original URL if suitable
        """
        # First, validate if processing is needed
        if not force_process:
            validation = await self.validate_image_suitability(url)
            if validation['suitable'] and not validation.get('needs_validation'):
                logger.info(f"Image suitable without processing: {url[:50]}...")
                return {
                    'original_url': url,
                    'needs_processing': False,
                    'format': 'original',
                    'dimensions': 'unknown',
                    'size_kb': 0
                }
        
        # Validate URL
        if not await self.validate_image_url(url):
            logger.warning(f"Invalid image URL: {url}")
            return None
        
        # Download image
        image_data = await self.download_image(url)
        if not image_data:
            return None
        
        # Process image
        try:
            result = self.process_image(image_data)
            if result is None:
                logger.warning(f"Image processing returned None for {url[:50]}...")
                return None
            
            processed_bytes, format_used, dimensions, size_kb = result
            
            return {
                'image_data': processed_bytes,
                'format': format_used,
                'dimensions': dimensions,
                'size_kb': size_kb,
                'needs_processing': True
            }
        except Exception as e:
            logger.error(f"Failed to process image from {url}: {e}")
            return None
