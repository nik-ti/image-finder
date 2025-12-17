# Deployment Guide

## Deployment Summary

The Image Finder microservice has been successfully deployed with the following configuration:

- **Repository**: https://github.com/nik-ti/image-finder.git
- **URL**: http://find-image.simple-flow.co
- **Port**: 8001 (internal), 80 (external via Nginx)
- **Container**: image-finder (Docker)

## Architecture

```
Internet → Nginx (find-image.simple-flow.co:80) → Docker Container (localhost:8001) → FastAPI App
```

## Deployment Steps Completed

1. ✅ Created Dockerfile with Python 3.11 and Playwright
2. ✅ Created docker-compose.yml with health checks
3. ✅ Pushed code to GitHub repository
4. ✅ Built Docker image (204s build time)
5. ✅ Started Docker container
6. ✅ Configured Nginx reverse proxy
7. ✅ Started Nginx service

## Container Management

### View logs
```bash
docker logs image-finder
docker logs image-finder --tail 50 -f
```

### Restart container
```bash
cd /root/Systems/image_finder
docker compose restart
```

### Stop container
```bash
docker compose down
```

### Rebuild and restart
```bash
docker compose down
docker compose build
docker compose up -d
```

## Nginx Configuration

Location: `/etc/nginx/sites-available/find-image.simple-flow.co`

Key features:
- 90s timeout for image processing
- 20MB max body size
- 7-day caching for images
- Reverse proxy to localhost:8001

### Reload Nginx
```bash
sudo nginx -t
sudo systemctl reload nginx
```

## Environment Variables

The container uses environment variables from `.env`:
- `OPENAI_API_KEY`
- `PERPLEXITY_API_KEY`

To update:
1. Edit `.env` file
2. Restart container: `docker compose restart`

## Health Check

```bash
curl http://find-image.simple-flow.co/health
```

Expected response: `{"status":"healthy"}`

## API Endpoint

```bash
curl -X POST http://find-image.simple-flow.co/find_image \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Your News Title",
    "research": "Context and description",
    "images": ["https://example.com/image.jpg"]
  }'
```

## Monitoring

### Check container status
```bash
docker ps | grep image-finder
```

### Check container health
```bash
docker inspect image-finder | grep -A 10 Health
```

### View resource usage
```bash
docker stats image-finder
```

## Troubleshooting

### Container not starting
```bash
docker logs image-finder
docker compose down
docker compose up -d
```

### Nginx errors
```bash
sudo nginx -t
sudo journalctl -u nginx -n 50
```

### API not responding
```bash
# Check if container is running
docker ps | grep image-finder

# Check container logs
docker logs image-finder --tail 100

# Test direct connection
curl http://localhost:8001/health
```

## Backup and Restore

### Backup cache
```bash
cp /root/Systems/image_finder/cache.json /root/Systems/image_finder/cache.json.backup
```

### Backup processed images
```bash
tar -czf processed_images_backup.tar.gz /root/Systems/image_finder/processed_images/
```

## Updates

To update the service:

```bash
cd /root/Systems/image_finder
git pull origin main
docker compose down
docker compose build
docker compose up -d
```

## Auto-restart on Reboot

The container is configured with `restart: unless-stopped` in docker-compose.yml, so it will automatically restart on system reboot.

To ensure Docker starts on boot:
```bash
sudo systemctl enable docker
```
