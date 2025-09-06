"""
Enhanced LEGO Identifier with multiple strategies and accuracy improvements
"""
import base64
import json
import os
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import anthropic
import logging
from PIL import Image
import hashlib

from config.settings import settings
from src.models.schemas import IdentificationResult, LegoItem, ItemType, ItemCondition
from src.utils.rate_limiter import AnthropicRateLimiter

logger = logging.getLogger(__name__)


class ImageQualityAssessment:
    """Assess image quality before processing"""
    
    @staticmethod
    def assess_quality(image_path: str) -> Dict[str, Any]:
        """Assess image quality and return recommendations"""
        try:
            with Image.open(image_path) as img:
                width, height = img.size
                total_pixels = width * height
                
                # Check resolution
                resolution_score = min(total_pixels / (1024 * 1024), 1.0)  # Normalize to 1MP
                
                # Check aspect ratio (prefer square-ish images for LEGO)
                aspect_ratio = max(width, height) / min(width, height)
                aspect_score = 1.0 if aspect_ratio < 2.0 else 0.7
                
                # Check if image is too dark or too bright
                if img.mode == 'RGB':
                    # Convert to grayscale for brightness analysis
                    gray = img.convert('L')
                    pixels = list(gray.getdata())
                    avg_brightness = sum(pixels) / len(pixels)
                    brightness_score = 1.0 - abs(avg_brightness - 128) / 128
                else:
                    brightness_score = 0.8  # Assume decent if not RGB
                
                # Overall quality score
                quality_score = (resolution_score * 0.4 + aspect_score * 0.3 + brightness_score * 0.3)
                
                return {
                    'quality_score': quality_score,
                    'resolution': f"{width}x{height}",
                    'total_pixels': total_pixels,
                    'aspect_ratio': aspect_ratio,
                    'brightness_score': brightness_score,
                    'recommendations': ImageQualityAssessment._get_recommendations(
                        quality_score, resolution_score, aspect_ratio, brightness_score
                    )
                }
        except Exception as e:
            logger.error(f"Error assessing image quality: {e}")
            return {
                'quality_score': 0.3,
                'error': str(e),
                'recommendations': ['Image quality assessment failed']
            }
    
    @staticmethod
    def _get_recommendations(quality_score: float, resolution_score: float, 
                           aspect_ratio: float, brightness_score: float) -> List[str]:
        """Generate recommendations based on quality assessment"""
        recommendations = []
        
        if quality_score < 0.5:
            recommendations.append("Image quality is poor - results may be inaccurate")
        
        if resolution_score < 0.3:
            recommendations.append("Image resolution is very low - consider using a higher resolution image")
        
        if aspect_ratio > 3.0:
            recommendations.append("Image is very wide/tall - consider cropping to focus on LEGO items")
        
        if brightness_score < 0.4:
            recommendations.append("Image is too dark or too bright - adjust lighting")
        
        if quality_score > 0.8:
            recommendations.append("Image quality is excellent")
        
        return recommendations


class EnhancedLegoIdentifier:
    """Enhanced LEGO identifier with multiple strategies and accuracy improvements"""
    
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        self.rate_limiter = AnthropicRateLimiter()
        self.quality_assessor = ImageQualityAssessment()
        
        # Cache for repeated identifications
        self.identification_cache = {}
    
    def _get_image_hash(self, image_path: str) -> str:
        """Generate hash for image caching"""
        with open(image_path, 'rb') as f:
            return hashlib.md5(f.read()).hexdigest()
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 for Claude API"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    
    def _get_enhanced_identification_prompt(self) -> str:
        """Enhanced prompt with better accuracy instructions"""
        return """You are an expert LEGO appraiser and collector with deep knowledge of LEGO minifigures, sets, and parts. 
        Analyze the provided image and identify all LEGO items visible. For each item, provide:

        1. Item identification (set number, name, theme if known)
        2. Item type (minifigure, set, or individual part)
        3. Condition assessment (new, used_complete, used_incomplete, or damaged)
        4. Year of release (if identifiable)
        5. Rarity/availability assessment
        6. Notable features or variations
        7. Any visible wear, damage, or missing parts

        ACCURACY REQUIREMENTS:
        - Only identify items you are confident about (confidence > 0.7)
        - If uncertain about specific details, use null values
        - Pay special attention to distinguishing between similar minifigures
        - Look for unique identifying features (prints, accessories, colors)
        - Verify theme identification with visual evidence

        THEME IDENTIFICATION GUIDELINES:
        - City theme: Construction workers, police, firefighters, civilians, vehicles
        - Creator theme: Generic figures, animals, basic vehicles
        - Friends theme: Mini-doll figures, pastel colors, heart patterns
        - Ninjago theme: Ninja characters, Asian-inspired designs, elemental powers
        - Castle/Kingdoms theme: Knights, medieval elements, dragons
        - Space theme: Astronauts, futuristic elements, space vehicles
        - Pirates theme: Pirate characters, ships, treasure
        - Star Wars theme: Character-specific designs, movie references
        - Super Heroes theme: DC/Marvel characters, capes, masks
        - And many others - be accurate!

        Respond with a detailed analysis in JSON format matching this structure:
        {
            "confidence_score": 0.85,
            "image_quality_assessment": "Good lighting and resolution",
            "identified_items": [
                {
                    "item_number": "sw0001a",
                    "name": "Luke Skywalker (Tatooine)",
                    "item_type": "minifigure",
                    "condition": "used_complete",
                    "year_released": 1999,
                    "theme": "Star Wars",
                    "category": "Episode IV",
                    "pieces": null,
                    "identifying_features": ["Yellow head", "Brown hair", "Tan torso with utility belt"],
                    "confidence": 0.9
                }
            ],
            "description": "Collection of mixed LEGO minifigures from various themes...",
            "condition_assessment": "Figures appear to be in good used condition...",
            "quality_notes": "Image quality allows for accurate identification"
        }
        
        Be thorough but honest about uncertainty. If you're not sure about specific details, indicate lower confidence or use null values.
        IMPORTANT: Only identify themes you can actually see evidence for - do not guess or assume popular themes!"""
    
    async def identify_lego_items_enhanced(self, image_path: str) -> IdentificationResult:
        """Enhanced identification with quality assessment and caching"""
        try:
            # Check cache first
            image_hash = self._get_image_hash(image_path)
            if image_hash in self.identification_cache:
                logger.info("Using cached identification result")
                return self.identification_cache[image_hash]
            
            # Assess image quality first
            quality_assessment = self.quality_assessor.assess_quality(image_path)
            logger.info(f"Image quality score: {quality_assessment['quality_score']:.2f}")
            
            # If quality is too low, return low confidence result
            if quality_assessment['quality_score'] < 0.3:
                return IdentificationResult(
                    confidence_score=0.1,
                    identified_items=[],
                    description=f"Image quality too low for accurate identification. Quality score: {quality_assessment['quality_score']:.2f}",
                    condition_assessment="Cannot assess due to poor image quality"
                )
            
            # Encode image
            image_base64 = self._encode_image(image_path)
            image_media_type = "image/jpeg"

            # Estimate token usage for rate limiting
            image_size = os.path.getsize(image_path)
            estimated_image_tokens = self.rate_limiter.estimate_image_tokens(image_size)
            prompt = self._get_enhanced_identification_prompt()
            estimated_prompt_tokens = self.rate_limiter.estimate_prompt_tokens(prompt)
            total_estimated_tokens = estimated_image_tokens + estimated_prompt_tokens
            
            logger.info(f"Estimated tokens for request: {total_estimated_tokens}")
            
            # Check rate limits and wait if necessary
            await self.rate_limiter.wait_for_capacity(total_estimated_tokens)
            
            # Make API call to Claude
            message = self.client.messages.create(
                model="claude-3-5-sonnet-20241022",  # Use latest model
                max_tokens=3000,  # Increased for more detailed responses
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": image_media_type,
                                    "data": image_base64,
                                },
                            },
                            {
                                "type": "text",
                                "text": f"Please analyze this image and identify all LEGO items visible. Image quality assessment: {quality_assessment['quality_score']:.2f}/1.0. Follow the detailed instructions for identification and assessment.",
                            },
                        ],
                    }
                ],
                system=self._get_enhanced_identification_prompt(),
            )
            
            # Record actual usage
            actual_input_tokens = getattr(message.usage, 'input_tokens', total_estimated_tokens)
            actual_output_tokens = getattr(message.usage, 'output_tokens', 0)
            self.rate_limiter.record_usage(actual_input_tokens, actual_output_tokens)
            
            logger.info(f"API call completed. Actual tokens: input={actual_input_tokens}, output={actual_output_tokens}")

            # Parse response
            response_text = message.content[0].text

            # Try to extract JSON from response
            json_start = response_text.find("{")
            json_end = response_text.rfind("}") + 1

            if json_start >= 0 and json_end > json_start:
                json_str = response_text[json_start:json_end]
                result_data = json.loads(json_str)

                # Convert to our schema with enhanced validation
                identified_items = []
                for item_data in result_data.get("identified_items", []):
                    # Only include items with high confidence
                    item_confidence = item_data.get("confidence", 0.8)
                    if item_confidence < 0.5:
                        logger.warning(f"Skipping low confidence item: {item_data.get('name', 'Unknown')}")
                        continue
                    
                    # Handle common variations in item_type
                    item_type_raw = item_data.get("item_type", "minifigure").lower()
                    item_type_mapping = {
                        "minifigure": "minifigure",
                        "minifig": "minifigure",
                        "figure": "minifigure",
                        "set": "set",
                        "part": "part",
                        "parts": "part",
                        "piece": "part",
                        "pieces": "part"
                    }
                    item_type = item_type_mapping.get(item_type_raw, "minifigure")

                    # Handle common variations in condition
                    condition_raw = item_data.get("condition", "used_complete").lower()
                    condition_mapping = {
                        "new": "new",
                        "mint": "new",
                        "used": "used_complete",
                        "used_complete": "used_complete",
                        "complete": "used_complete",
                        "used_incomplete": "used_incomplete",
                        "incomplete": "used_incomplete",
                        "damaged": "damaged",
                        "worn": "damaged"
                    }
                    condition = condition_mapping.get(condition_raw, "used_complete")

                    item = LegoItem(
                        item_number=item_data.get("item_number"),
                        name=item_data.get("name"),
                        item_type=ItemType(item_type),
                        condition=ItemCondition(condition),
                        year_released=item_data.get("year_released"),
                        theme=item_data.get("theme"),
                        category=item_data.get("category"),
                        pieces=item_data.get("pieces"),
                    )
                    identified_items.append(item)

                # Adjust confidence based on image quality
                base_confidence = result_data.get("confidence_score", 0.5)
                quality_adjusted_confidence = base_confidence * quality_assessment['quality_score']
                
                # Cache the result
                result = IdentificationResult(
                    confidence_score=quality_adjusted_confidence,
                    identified_items=identified_items,
                    description=result_data.get("description", response_text[:500]),
                    condition_assessment=result_data.get(
                        "condition_assessment", "Assessment not available"
                    ),
                )
                
                self.identification_cache[image_hash] = result
                return result
            else:
                # Fallback if JSON parsing fails
                return IdentificationResult(
                    confidence_score=0.2,
                    identified_items=[],
                    description=response_text[:500],
                    condition_assessment="Could not parse detailed assessment",
                )

        except Exception as e:
            logger.error(f"Error during enhanced identification: {e}")
            return IdentificationResult(
                confidence_score=0.0,
                identified_items=[],
                description=f"Error during identification: {str(e)}",
                condition_assessment="Could not assess condition due to error",
            )
    
    def clear_cache(self):
        """Clear the identification cache"""
        self.identification_cache.clear()
        logger.info("Identification cache cleared")
