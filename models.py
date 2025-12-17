"""Pydantic models for request/response validation."""
from typing import Optional, List
from pydantic import BaseModel, Field, HttpUrl


class ImageRequest(BaseModel):
    """Request model for finding images."""
    title: str = Field(..., description="Title of the news article or tool")
    research: str = Field(..., description="Research context or description")
    source_url: Optional[str] = Field(None, description="Optional source URL to scrape images from")
    images: Optional[List[str]] = Field(None, description="Optional array of candidate image URLs")


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
    image_url: str = Field(..., description="Processed and validated image URL")
    original_url: str = Field(..., description="Source image URL before processing")
    tool_used: str = Field(..., description="Source of the image: candidate / site / perplexity / default")
    image_description: str = Field(..., description="Short description of the image")
    format: str = Field(..., description="Image format: jpeg / png")
    dimensions: str = Field(..., description="Image dimensions (e.g., 1280x720)")
    quality_score: int = Field(..., ge=1, le=10, description="Quality score from vision analysis")
    temporal_relevance: str = Field(..., description="Temporal relevance assessment")
    watermark_status: str = Field(..., description="Watermark status: none / minimal / heavy")
    cached: bool = Field(False, description="Whether result was retrieved from cache")
