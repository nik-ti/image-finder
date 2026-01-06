"""Vision LLM analyzer for image evaluation."""
import json
import base64
from typing import List, Dict, Any, Optional
from datetime import datetime
import httpx
from openai import AsyncOpenAI

from config import OPENAI_API_KEY, OPENAI_MODEL
from models import ImageEvaluation
from utils import logger


class VisionAnalyzer:
    """Analyzes images using Vision LLM."""
    
    def __init__(self):
        self.client = AsyncOpenAI(api_key=OPENAI_API_KEY)
    
    async def analyze_images(
        self,
        image_urls: List[str],
        title: str,
        research: str,
        min_relevance_score: int = 8,
        min_resolution_px: int = 1000,
        fallback_mode: bool = False
    ) -> List[ImageEvaluation]:
        """
        Analyze multiple images and return evaluations.
        
        Args:
            image_urls: List of image URLs to analyze
            title: Article title
            research: Research context
        
        Returns:
            List of ImageEvaluation objects, sorted by quality
        """
        if not image_urls:
            return []
        
        # Filter to only supported formats for Vision API
        supported_extensions = ('.png', '.jpg', '.jpeg', '.gif', '.webp')
        filtered_urls = []
        for url in image_urls:
            # Extract path from URL (ignore query parameters)
            from urllib.parse import urlparse
            path = urlparse(url).path.lower()
            if any(path.endswith(ext) for ext in supported_extensions):
                filtered_urls.append(url)
        
        if not filtered_urls:
            logger.warning("No images with supported formats found")
            return []
            
        # Limit initial candidates to prevent excessive validation time
        # We only need 10 valid ones eventually, so starting with 20-30 is enough
        filtered_urls = filtered_urls[:20]
            
        # Validate accessibility in parallel
        import asyncio
        
        async def check_url(url):
            if await self._validate_accessibility(url):
                return url
            return None
            
        tasks = [check_url(url) for url in filtered_urls]
        results = await asyncio.gather(*tasks)
        
        valid_urls = [url for url in results if url is not None]
        filtered_urls = valid_urls
        
        if not filtered_urls:
            logger.warning("No accessible images found")
            return []
        
        # Limit to first 5 images to avoid excessive API costs and timeouts
        filtered_urls = filtered_urls[:5]
        
        logger.info(f"Analyzing {len(filtered_urls)} images with Vision LLM")
        
        # Build prompt
        current_date = datetime.now().strftime('%Y-%m-%d')
        prompt = self._build_analysis_prompt(title, research, current_date, min_resolution_px, fallback_mode)
        
        # Build messages with images
        messages = [
            {
                "role": "user",
                "content": [
                    {"type": "text", "text": prompt}
                ]
            }
        ]
        
        # Add images to the message
        for idx, url in enumerate(filtered_urls):
            messages[0]["content"].append({
                "type": "image_url",
                "image_url": {"url": url}
            })
        
        try:
            # Call OpenAI Vision API
            response = await self.client.chat.completions.create(
                model=OPENAI_MODEL,
                messages=messages,
                max_tokens=2000,
                temperature=0.1
            )
            
            # Parse response
            response_text = response.choices[0].message.content
            logger.debug(f"Vision LLM response: {response_text}")
            
            # Extract JSON from response
            evaluations = self._parse_evaluations(response_text, filtered_urls)
            
            # Filter and sort
            filtered = self._filter_evaluations(evaluations)
            
            logger.info(f"Filtered to {len(filtered)} high-quality images")
            return filtered
            
        except Exception as e:
            logger.error(f"Error analyzing images with Vision LLM: {e}")
            return []
    
    def _build_analysis_prompt(self, title: str, research: str, current_date: str, min_resolution_px: int, fallback_mode: bool) -> str:
        """Build the analysis prompt for Vision LLM."""
        
        # Adjust prompt based on fallback mode
        resolution_instruction = f"The image MUST be high-resolution (approx >{min_resolution_px}px). REJECT small thumbnails."
        if min_resolution_px < 500:
            resolution_instruction = "Image size is flexible, but clear vectors or logos are preferred over blurry thumbnails."
            
        relevance_instruction = "10=Exact match (official/news). 1=Irrelevant."
        if fallback_mode:
            relevance_instruction = "Score LENIENTLY. 10=Good concept/Logo. 6=Acceptable Generic/Abstract. 1=Total Junk."

        return f"""Analyze these images for news article: "{title}"
Context: {research}
Current date: {current_date}

STRICT VALIDATION RULES:
1. RESOLUTION: {resolution_instruction}
2. RELEVANCE: If specific entities are mentioned, look for them. IF FALLBACK/LOGO SEARCH: Accept official logos or abstract representations if they look professional.
3. QUALITY: Reject pixelated/blurry images.
4. BANNED: No random stock photos of "people shaking hands" or "smiling office workers".

For each image (in order), evaluate:
1. TEMPORAL RELEVANCE: Check dates if visible. (Ignore for logos/abstract).
2. RELEVANCE SCORE 1-10: {relevance_instruction}
   - REJECT if score < 4.
3. WATERMARKS: none/minimal/heavy.
4. ADS: none/minimal/intrusive.
5. QUALITY: high/medium/low.
6. OUTDATED: true/false.

Return a JSON array with one evaluation per image, in the same order as provided.
Each evaluation should have this structure:
{{
  "image_index": 0,
  "relevance_score": 8,
  "temporal_relevance": "current" or "outdated" or "not_applicable",
  "watermark_severity": "none" or "minimal" or "heavy",
  "ad_presence": "none" or "minimal" or "intrusive",
  "content_quality": "high" or "medium" or "low",
  "is_relevant_to_event": true or false,
  "contains_outdated_info": true or false,
  "reasoning": "brief explanation"
}}

Return ONLY the JSON array."""
    
    def _parse_evaluations(self, response_text: str, image_urls: List[str]) -> List[ImageEvaluation]:
        """Parse Vision LLM response into ImageEvaluation objects."""
        evaluations = []
        
        try:
            # Try to extract JSON from response
            # Sometimes the model wraps it in markdown code blocks
            response_text = response_text.strip()
            if response_text.startswith('```'):
                # Remove markdown code blocks
                lines = response_text.split('\n')
                response_text = '\n'.join(lines[1:-1])
            
            # Parse JSON
            data = json.loads(response_text)
            
            # Convert to ImageEvaluation objects
            for item in data:
                idx = item.get('image_index', 0)
                if idx < len(image_urls):
                    evaluation = ImageEvaluation(
                        image_url=image_urls[idx],
                        relevance_score=item.get('relevance_score', 5),
                        temporal_relevance=item.get('temporal_relevance', 'not_applicable'),
                        watermark_severity=item.get('watermark_severity', 'none'),
                        ad_presence=item.get('ad_presence', 'none'),
                        content_quality=item.get('content_quality', 'medium'),
                        is_relevant_to_event=item.get('is_relevant_to_event', False),
                        contains_outdated_info=item.get('contains_outdated_info', False),
                        reasoning=item.get('reasoning', '')
                    )
                    evaluations.append(evaluation)
        
        except json.JSONDecodeError as e:
            logger.error(f"Failed to parse Vision LLM response as JSON: {e}")
            logger.debug(f"Response text: {response_text}")
        except Exception as e:
            logger.error(f"Error parsing evaluations: {e}")
        
        return evaluations
    
    def _filter_evaluations(self, evaluations: List[ImageEvaluation], min_relevance: int = 8) -> List[ImageEvaluation]:
        """
        Filter evaluations based on quality criteria and sort by score.
        
        Args:
            evaluations: List of image evaluations
            min_relevance: Minimum relevance score (default 8, can be lowered for fallback)
        
        Filtering rules:
        1. Reject if watermark_severity == "heavy"
        2. Reject if ad_presence == "intrusive"
        3. Reject if relevance_score < min_relevance
        4. Reject if is_relevant_to_event == False
        5. Reject if contains_outdated_info == True
        """
        filtered = []
        
        for eval in evaluations:
            # Apply filtering rules
            if eval.watermark_severity == "heavy":
                logger.debug(f"Rejected {eval.image_url[:50]}... - heavy watermark")
                continue
            
            if eval.ad_presence == "intrusive":
                logger.debug(f"Rejected {eval.image_url[:50]}... - intrusive ads")
                continue
            
            if eval.relevance_score < min_relevance:
                logger.debug(f"Rejected {eval.image_url[:50]}... - low relevance score: {eval.relevance_score} (min: {min_relevance})")
                continue
            
            if not eval.is_relevant_to_event:
                logger.debug(f"Rejected {eval.image_url[:50]}... - not relevant to event")
                continue
            
            if eval.contains_outdated_info:
                logger.debug(f"Rejected {eval.image_url[:50]}... - contains outdated info")
                continue
            
            filtered.append(eval)
        
        # Sort by relevance score (descending), then by quality
        quality_order = {"high": 3, "medium": 2, "low": 1}
        filtered.sort(
            key=lambda x: (x.relevance_score, quality_order.get(x.content_quality, 0)),
            reverse=True
        )
        
        return filtered
    
    async def _validate_accessibility(self, url: str) -> bool:
        """Check if image URL is accessible and responsive."""
        try:
            async with httpx.AsyncClient() as client:
                response = await client.head(
                    url, 
                    timeout=5.0,  # Short timeout for validation
                    follow_redirects=True
                )
                
                if response.status_code != 200:
                    return False
                
                # Check file size (limit to 10MB for OpenAI Vision API)
                content_length = response.headers.get('content-length')
                if content_length:
                    size_mb = int(content_length) / (1024 * 1024)
                    if size_mb > 10:
                        logger.debug(f"Image too large for Vision API: {url[:50]}... ({size_mb:.1f}MB)")
                        return False
                
                return True
        except Exception as e:
            logger.debug(f"Image accessibility check failed for {url}: {e}")
            return False
