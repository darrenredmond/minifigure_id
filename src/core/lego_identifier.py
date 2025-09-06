import base64
import json
import os
from typing import List, Dict, Any
from pathlib import Path
import anthropic
import logging

from config.settings import settings
from src.models.schemas import IdentificationResult, LegoItem, ItemType, ItemCondition
from src.utils.rate_limiter import AnthropicRateLimiter

logger = logging.getLogger(__name__)


class LegoIdentifier:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
        # Initialize rate limiter
        self.rate_limiter = AnthropicRateLimiter()

    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 for Claude API"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")

    def _get_identification_prompt(self) -> str:
        """Get the system prompt for LEGO identification"""
        return """You are an expert LEGO appraiser and collector with deep knowledge of LEGO minifigures, sets, and parts. 
        Analyze the provided image and identify all LEGO items visible. For each item, provide:

        1. Item identification (set number, name, theme if known)
        2. Item type (minifigure, set, or individual part)
        3. Condition assessment (new, used_complete, used_incomplete, or damaged)
        4. Year of release (if identifiable)
        5. Rarity/availability assessment
        6. Notable features or variations
        7. Any visible wear, damage, or missing parts

        Pay special attention to:
        - Unique prints, accessories, or rare variants
        - Set completeness (all parts present)
        - Condition details that affect value
        - Authentication (genuine LEGO vs third-party)
        - Accurate theme identification (City, Creator, Friends, Ninjago, Castle, Space, Pirates, etc.)

        DO NOT assume themes - look carefully at actual visual details:
        - City theme: Construction workers, police, firefighters, civilians
        - Creator theme: Generic figures, animals, vehicles
        - Friends theme: Mini-doll figures, pastel colors
        - Ninjago theme: Ninja characters, Asian-inspired designs
        - Castle/Kingdoms theme: Knights, medieval elements
        - Space theme: Astronauts, futuristic elements
        - Pirates theme: Pirate characters, ships
        - And many others - be accurate!

        Respond with a detailed analysis in JSON format matching this structure:
        {
            "confidence_score": 0.75,
            "identified_items": [
                {
                    "item_number": "cty0123",
                    "name": "Construction Worker",
                    "item_type": "minifigure",
                    "condition": "used_complete",
                    "year_released": 2018,
                    "theme": "City",
                    "category": "Construction",
                    "pieces": null
                },
                {
                    "item_number": null,
                    "name": "Generic Female Civilian",
                    "item_type": "minifigure",
                    "condition": "used_complete",
                    "year_released": null,
                    "theme": "Creator/Generic",
                    "category": null,
                    "pieces": null
                }
            ],
            "description": "Collection of mixed LEGO minifigures from various themes...",
            "condition_assessment": "Figures appear to be in good used condition..."
        }
        
        Be thorough but honest about uncertainty. If you're not sure about specific details, indicate lower confidence or use null values.
        IMPORTANT: Only identify themes you can actually see evidence for - do not guess or assume popular themes!"""

    async def identify_lego_items(self, image_path: str) -> IdentificationResult:
        """Identify LEGO items in the provided image using Claude Vision with rate limiting"""
        try:
            # Encode image
            image_base64 = self._encode_image(image_path)
            image_media_type = "image/jpeg"  # Assuming optimized images are JPEG

            # Estimate token usage for rate limiting
            image_size = os.path.getsize(image_path)
            estimated_image_tokens = self.rate_limiter.estimate_image_tokens(image_size)
            prompt = self._get_identification_prompt()
            estimated_prompt_tokens = self.rate_limiter.estimate_prompt_tokens(prompt)
            total_estimated_tokens = estimated_image_tokens + estimated_prompt_tokens
            
            logger.info(f"Estimated tokens for request: {total_estimated_tokens} (image: {estimated_image_tokens}, prompt: {estimated_prompt_tokens})")
            
            # Check rate limits and wait if necessary
            await self.rate_limiter.wait_for_capacity(total_estimated_tokens)
            
            # Log usage stats before making request
            stats = self.rate_limiter.get_usage_stats()
            logger.info(f"Rate limiter stats: {stats['current_input_tokens']}/{stats['max_input_tokens_per_minute']} tokens used, {stats['current_requests']}/{stats['max_requests_per_minute']} requests made")

            # Make API call to Claude (using Claude 4 Sonnet for superior accuracy)
            # Note: The client.messages.create is not async in the anthropic package
            message = self.client.messages.create(
                model="claude-4-sonnet-20250514",
                max_tokens=2000,
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
                                "text": "Please analyze this image and identify all LEGO items visible. Follow the detailed instructions for identification and assessment.",
                            },
                        ],
                    }
                ],
                system=self._get_identification_prompt(),
            )
            
            # Record actual usage (estimate input tokens, get actual output tokens if available)
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

                # Convert to our schema
                identified_items = []
                for item_data in result_data.get("identified_items", []):
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

                return IdentificationResult(
                    confidence_score=result_data.get("confidence_score", 0.5),
                    identified_items=identified_items,
                    description=result_data.get("description", response_text[:500]),
                    condition_assessment=result_data.get(
                        "condition_assessment", "Assessment not available"
                    ),
                )
            else:
                # Fallback if JSON parsing fails
                return IdentificationResult(
                    confidence_score=0.3,
                    identified_items=[],
                    description=response_text[:500],
                    condition_assessment="Could not parse detailed assessment",
                )

        except Exception as e:
            # Return error result
            return IdentificationResult(
                confidence_score=0.0,
                identified_items=[],
                description=f"Error during identification: {str(e)}",
                condition_assessment="Could not assess condition due to error",
            )

    def _extract_keywords(self, description: str) -> List[str]:
        """Extract relevant keywords for further research"""
        # Simple keyword extraction - could be enhanced with NLP
        keywords = []
        important_terms = [
            "rare",
            "limited",
            "exclusive",
            "first edition",
            "variant",
            "misprint",
            "prototype",
            "unreleased",
            "promotional",
        ]

        description_lower = description.lower()
        for term in important_terms:
            if term in description_lower:
                keywords.append(term)

        return keywords
