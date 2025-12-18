#!/bin/bash
# Cleanup script for old images
# Run daily via cron to remove images older than 3 days

cd /root/Systems/image_finder

# Run cleanup via Docker
docker exec image-finder python -c "
from storage import ImageStorage
storage = ImageStorage()
storage.delete_old_images(days=3)
print('Cleanup completed')
"
