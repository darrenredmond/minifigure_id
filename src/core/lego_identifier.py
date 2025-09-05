import base64
import json
from typing import List, Dict, Any
from pathlib import Path
import anthropic

from config.settings import settings
from src.models.schemas import IdentificationResult, LegoItem, ItemType, ItemCondition


class LegoIdentifier:
    def __init__(self):
        self.client = anthropic.Anthropic(api_key=settings.anthropic_api_key)

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

        Respond with a detailed analysis in JSON format matching this structure:
        {
            "confidence_score": 0.85,
            "identified_items": [
                {
                    "item_number": "sw0001a",
                    "name": "Luke Skywalker (Tatooine)",
                    "item_type": "minifigure",
                    "condition": "used_complete",
                    "year_released": 1999,
                    "theme": "Star Wars",
                    "category": "Episode IV",
                    "pieces": null
                }
            ],
            "description": "Single LEGO Star Wars minifigure of Luke Skywalker from 1999...",
            "condition_assessment": "Figure appears to be in good used condition with minor wear on printed torso..."
        }
        
        Be thorough but honest about uncertainty. If you're not sure about specific details, indicate lower confidence or use null values."""

    async def identify_lego_items(self, image_path: str) -> IdentificationResult:
        """Identify LEGO items in the provided image using Claude Vision"""
        try:
            # Encode image
            image_base64 = self._encode_image(image_path)
            image_media_type = "image/jpeg"  # Assuming optimized images are JPEG

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
