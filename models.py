"""Pydantic models for request/response validation."""
from typing import Optional, List, Union
from pydantic import BaseModel, Field, field_validator


class ImageRequest(BaseModel):
    """Request model for finding images."""
    title: str = Field(..., description="Title of the news article or tool")
    research: str = Field(..., description="Research context or description")
    source_url: Optional[str] = Field(None, description="Optional source URL to scrape images from")
    images: Optional[Union[List[str], str]] = Field(None, description="Optional array of candidate image URLs or comma-separated string")
    
    @field_validator('images', mode='before')
    @classmethod
    def normalize_images(cls, v):
        """Normalize images to list format - accepts array or comma-separated string."""
        if v is None:
            return None
        if isinstance(v, str):
            # Split by comma and strip whitespace
            return [url.strip() for url in v.split(',') if url.strip()]
        return v


class ImageEvaluation(BaseModel):
    """Internal model for vision analysis results."""
    image_url: str
    relevance_score: int = Field(..., ge=1, le=10)
    temporal_relevance: str
    watermark_severity: str  # none / minimal / heavy
    ad_presence: str  # none / minimal / intrusive
    content_quality: str  # high / medium / low
    is_relevant_to_event: bool
    contains_outdated_info: bool
    reasoning: str


class ImageResponse(BaseModel):
    """Response model for found images."""
    image_found: bool = Field(..., description="Whether a suitable image was found")
    image_url: Optional[str] = Field(None, description="Processed and validated image URL")
    original_url: Optional[str] = Field(None, description="Source image URL before processing")
    tool_used: Optional[str] = Field(None, description="Source of the image: candidate / site / perplexity / default")
    image_description: Optional[str] = Field(None, description="Short description of the image")
    format: Optional[str] = Field(None, description="Image format: jpeg / png")
    dimensions: Optional[str] = Field(None, description="Image dimensions (e.g., 1280x720)")
    quality_score: Optional[int] = Field(None, ge=1, le=10, description="Quality score from vision analysis")
    temporal_relevance: Optional[str] = Field(None, description="Temporal relevance assessment")
    watermark_status: Optional[str] = Field(None, description="Watermark status: none / minimal / heavy")
    cached: bool = Field(False, description="Whether result was retrieved from cache")
