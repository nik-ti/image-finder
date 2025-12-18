"""Image storage handler for saving and serving processed images."""
import uuid
from pathlib import Path
from typing import Tuple
import io

from config import PROCESSED_IMAGES_DIR
from utils import logger


class ImageStorage:
    """Handles storage of processed images."""
    
    def __init__(self, storage_dir: Path = PROCESSED_IMAGES_DIR):
        self.storage_dir = storage_dir
        self.storage_dir.mkdir(exist_ok=True)
    
    def save_image(self, image_data: bytes, format: str) -> Tuple[str, Path]:
        """
        Save processed image to local storage.
        
        Args:
            image_data: Image bytes
            format: Image format (jpeg/png)
        
        Returns:
            Tuple of (filename, full_path)
        """
        # Generate unique filename
        file_extension = 'jpg' if format == 'jpeg' else format
        filename = f"{uuid.uuid4()}.{file_extension}"
        file_path = self.storage_dir / filename
        
        # Save to disk
        try:
            with open(file_path, 'wb') as f:
                f.write(image_data)
            logger.info(f"Saved image to {file_path}")
            return filename, file_path
        except Exception as e:
            logger.error(f"Error saving image: {e}")
            raise
    
    def get_image_url(self, filename: str, base_url: str = None) -> str:
        """
        Get the URL for a stored image.
        
        Args:
            filename: Image filename
            base_url: Base URL of the server (defaults to PUBLIC_URL from config)
        
        Returns:
            Full URL to access the image
        """
        if base_url is None:
            from config import PUBLIC_URL
            base_url = PUBLIC_URL
        return f"{base_url}/images/{filename}"
    
    def delete_old_images(self, days: int = 30):
        """
        Delete images older than specified days.
        
        Args:
            days: Number of days to keep images
        """
        import time
        current_time = time.time()
        deleted_count = 0
        
        for image_file in self.storage_dir.glob("*"):
            if image_file.is_file():
                file_age_days = (current_time - image_file.stat().st_mtime) / 86400
                if file_age_days > days:
                    try:
                        image_file.unlink()
                        deleted_count += 1
                    except Exception as e:
                        logger.error(f"Error deleting {image_file}: {e}")
        
        if deleted_count > 0:
            logger.info(f"Deleted {deleted_count} old images")
