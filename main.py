"""Main FastAPI application for image finder service."""
import asyncio
from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager

from models import ImageRequest, ImageResponse
from image_collector import ImageCollector
from vision_analyzer import VisionAnalyzer
from image_processor import ImageProcessor
from storage import ImageStorage
from cache_manager import CacheManager
from config import PROCESSED_IMAGES_DIR, DEFAULT_FALLBACK_IMAGE, TIMEOUTS
from utils import logger


# Initialize components
cache_manager = CacheManager()
image_collector = ImageCollector()
vision_analyzer = VisionAnalyzer()
image_processor = ImageProcessor()
image_storage = ImageStorage()


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Lifespan context manager for startup/shutdown events."""
    # Startup
    logger.info("Starting Image Finder service...")
    yield
    # Shutdown
    logger.info("Shutting down Image Finder service...")


# Create FastAPI app
app = FastAPI(
    title="Image Finder API",
    description="Find the best image for news articles and tools",
    version="1.0.0",
    lifespan=lifespan
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount static files for serving processed images
app.mount("/images", StaticFiles(directory=str(PROCESSED_IMAGES_DIR)), name="images")


@app.get("/")
async def root():
    """Root endpoint."""
    return {
        "service": "Image Finder API",
        "version": "1.0.0",
        "status": "running"
    }


@app.get("/health")
async def health_check():
    """Health check endpoint."""
    return {"status": "healthy"}


@app.post("/", response_model=ImageResponse)
@app.post("/find_image", response_model=ImageResponse)  # Keep old endpoint for compatibility
async def find_image(request: ImageRequest):
    """
    Find the best image for a news article or tool.
    
    Args:
        request: ImageRequest with title, research, optional source_url and images
    
    Returns:
        ImageResponse with processed image URL and metadata
    """
    logger.info(f"Processing request for: {request.title}")
    
    try:
        # Check cache first
        cached_result = await cache_manager.get(
            request.title,
            request.research,
            request.source_url,
            request.images
        )
        
        if cached_result:
            logger.info("Returning cached result")
            return ImageResponse(**cached_result)
        
        # Set overall timeout
        try:
            result = await asyncio.wait_for(
                _find_image_internal(request),
                timeout=TIMEOUTS['total_request']
            )
            
            # Cache the result
            cache_manager.set(
                request.title,
                request.research,
                request.source_url,
                request.images,
                result.model_dump()
            )
            
            return result
            
        except asyncio.TimeoutError:
            logger.error("Total request timeout exceeded")
            raise HTTPException(status_code=504, detail="Request timeout")
    
    except Exception as e:
        logger.error(f"Error processing request: {e}")
        raise HTTPException(status_code=500, detail=str(e))


async def _find_image_internal(request: ImageRequest) -> ImageResponse:
    """
    Internal function to find the best image.
    
    Args:
        request: ImageRequest
    
    Returns:
        ImageResponse
    """
    # Step 1: Collect image candidates
    image_urls = await image_collector.collect_all(
        title=request.title,
        research=request.research,
        source_url=request.source_url,
        candidate_images=request.images
    )
    
    if not image_urls:
        logger.warning("No images collected, using fallback")
        return _create_fallback_response()
    
    # Step 2: Analyze images with Vision LLM
    evaluations = await vision_analyzer.analyze_images(
        image_urls=image_urls,
        title=request.title,
        research=request.research
    )
    
    if not evaluations:
        logger.warning("No images passed evaluation, trying Perplexity fallback...")
        # Jump to Perplexity fallback instead of returning default immediately
        evaluations = []  # Empty list to skip the processing loop below
    
    # Step 3: Process the best image
    for evaluation in evaluations:
        logger.info(f"Attempting to process top candidate: {evaluation.image_url[:50]}...")
        
        processed = await image_processor.process_image_url(evaluation.image_url)
        
        if processed:
            # Determine tool used
            tool_used = _determine_tool_used(evaluation.image_url, request)
            
            # Check if image needs processing or can use original URL
            if processed.get('needs_processing', True):
                # Save to storage
                filename, file_path = image_storage.save_image(
                    processed['image_data'],
                    processed['format']
                )
                
                # Generate URL
                image_url = image_storage.get_image_url(filename)
            else:
                # Use original URL - no processing needed
                image_url = evaluation.image_url
                logger.info(f"Using original URL without processing: {image_url[:50]}...")
            
            return ImageResponse(
                image_url=image_url,
                original_url=evaluation.image_url,
                tool_used=tool_used,
                image_description=evaluation.reasoning,
                format=processed.get('format', 'original'),
                dimensions=processed.get('dimensions', 'unknown'),
                quality_score=evaluation.relevance_score,
                temporal_relevance=evaluation.temporal_relevance,
                watermark_status=evaluation.watermark_severity,
                cached=False
            )
    
    # If all processing attempts failed, try Perplexity as fallback
    logger.warning("All image processing attempts failed, trying Perplexity fallback...")
    
    # Check if we already tried Perplexity
    if not request.source_url and not request.images:
        # Already using Perplexity, no more fallbacks
        logger.warning("Perplexity already tried, using default fallback")
        return _create_fallback_response()
    
    # Try Perplexity as last resort
    try:
        perplexity_images = await image_collector.search_perplexity(
            title=request.title,
            research=request.research
        )
        
        if perplexity_images:
            logger.info(f"Perplexity fallback found {len(perplexity_images)} images")
            
            # Analyze Perplexity images
            perplexity_evaluations = await vision_analyzer.analyze_images(
                image_urls=perplexity_images,
                title=request.title,
                research=request.research
            )
            
            # Try to process Perplexity images
            for evaluation in perplexity_evaluations:
                logger.info(f"Attempting Perplexity candidate: {evaluation.image_url[:50]}...")
                processed = await image_processor.process_image_url(evaluation.image_url)
                
                if processed:
                    tool_used = "perplexity"
                    
                    if processed.get('needs_processing', True):
                        filename, file_path = image_storage.save_image(
                            processed['image_data'],
                            processed['format']
                        )
                        image_url = image_storage.get_image_url(filename)
                    else:
                        image_url = evaluation.image_url
                    
                    return ImageResponse(
                        image_url=image_url,
                        original_url=evaluation.image_url,
                        tool_used=tool_used,
                        image_description=evaluation.reasoning,
                        format=processed.get('format', 'original'),
                        dimensions=processed.get('dimensions', 'unknown'),
                        quality_score=evaluation.relevance_score,
                        temporal_relevance=evaluation.temporal_relevance,
                        watermark_status=evaluation.watermark_severity,
                        cached=False
                    )
    except Exception as e:
        logger.error(f"Perplexity fallback failed: {e}")
    
    # Final fallback
    logger.warning("All attempts failed including Perplexity, using default fallback")
    return _create_fallback_response()


def _determine_tool_used(image_url: str, request: ImageRequest) -> str:
    """Determine which tool/source was used to find the image."""
    if request.images and image_url in request.images:
        return "candidate"
    elif request.source_url and request.source_url in image_url:
        return "site"
    else:
        return "perplexity"


def _create_fallback_response() -> ImageResponse:
    """Create a fallback response when no suitable image is found."""
    return ImageResponse(
        image_url=DEFAULT_FALLBACK_IMAGE,
        original_url=DEFAULT_FALLBACK_IMAGE,
        tool_used="default",
        image_description="Default fallback image - no suitable image found",
        format="png",
        dimensions="1280x720",
        quality_score=1,
        temporal_relevance="not_applicable",
        watermark_status="none",
        cached=False
    )


if __name__ == "__main__":
    import uvicorn
    from config import SERVER_HOST, SERVER_PORT
    
    uvicorn.run(
        "main:app",
        host=SERVER_HOST,
        port=SERVER_PORT,
        reload=True,
        log_level="info"
    )
