"""
Alternative image identification methods for cost reduction
"""
import base64
import json
import logging
from typing import List, Dict, Any, Optional, Tuple
from pathlib import Path
import requests
from PIL import Image
import io

from src.models.schemas import IdentificationResult, LegoItem, ItemType, ItemCondition

logger = logging.getLogger(__name__)


class OpenAIVisionIdentifier:
    """OpenAI GPT-4 Vision as alternative to Claude"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://api.openai.com/v1/chat/completions"
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 for OpenAI API"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    
    async def identify_lego_items(self, image_path: str) -> IdentificationResult:
        """Identify LEGO items using OpenAI Vision"""
        try:
            # Encode image
            image_base64 = self._encode_image(image_path)
            
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            payload = {
                "model": "gpt-4-vision-preview",
                "messages": [
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": "Identify all LEGO items in this image. Return JSON with confidence_score, identified_items array, description, and condition_assessment. Each item should have item_number, name, item_type, condition, year_released, theme, category, pieces."
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": f"data:image/jpeg;base64,{image_base64}"
                                }
                            }
                        ]
                    }
                ],
                "max_tokens": 2000
            }
            
            response = requests.post(self.base_url, headers=headers, json=payload, timeout=30)
            response.raise_for_status()
            
            data = response.json()
            content = data['choices'][0]['message']['content']
            
            # Parse JSON response
            json_start = content.find("{")
            json_end = content.rfind("}") + 1
            
            if json_start >= 0 and json_end > json_start:
                json_str = content[json_start:json_end]
                result_data = json.loads(json_str)
                
                # Convert to our schema
                identified_items = []
                for item_data in result_data.get("identified_items", []):
                    item = self._convert_to_lego_item(item_data)
                    if item:
                        identified_items.append(item)
                
                return IdentificationResult(
                    confidence_score=result_data.get("confidence_score", 0.5),
                    identified_items=identified_items,
                    description=result_data.get("description", content[:500]),
                    condition_assessment=result_data.get("condition_assessment", "Assessment not available")
                )
            else:
                return IdentificationResult(
                    confidence_score=0.3,
                    identified_items=[],
                    description=content[:500],
                    condition_assessment="Could not parse detailed assessment"
                )
                
        except Exception as e:
            logger.error(f"OpenAI Vision error: {e}")
            return IdentificationResult(
                confidence_score=0.0,
                identified_items=[],
                description=f"Error during identification: {str(e)}",
                condition_assessment="Could not assess condition due to error"
            )
    
    def _convert_to_lego_item(self, item_data: Dict[str, Any]) -> Optional[LegoItem]:
        """Convert API response to LegoItem"""
        try:
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
            item_type = ItemType(item_type_mapping.get(item_type_raw, "minifigure"))

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
            condition = ItemCondition(condition_mapping.get(condition_raw, "used_complete"))

            return LegoItem(
                item_number=item_data.get("item_number"),
                name=item_data.get("name"),
                item_type=item_type,
                condition=condition,
                year_released=item_data.get("year_released"),
                theme=item_data.get("theme"),
                category=item_data.get("category"),
                pieces=item_data.get("pieces"),
            )
        except Exception as e:
            logger.error(f"Error converting item data: {e}")
            return None


class GoogleVisionIdentifier:
    """Google Cloud Vision API as alternative"""
    
    def __init__(self, api_key: str):
        self.api_key = api_key
        self.base_url = "https://vision.googleapis.com/v1/images:annotate"
    
    def _encode_image(self, image_path: str) -> str:
        """Encode image to base64 for Google Vision API"""
        with open(image_path, "rb") as image_file:
            return base64.b64encode(image_file.read()).decode("utf-8")
    
    async def identify_lego_items(self, image_path: str) -> IdentificationResult:
        """Identify LEGO items using Google Vision API"""
        try:
            image_base64 = self._encode_image(image_path)
            
            payload = {
                "requests": [
                    {
                        "image": {
                            "content": image_base64
                        },
                        "features": [
                            {
                                "type": "LABEL_DETECTION",
                                "maxResults": 20
                            },
                            {
                                "type": "TEXT_DETECTION",
                                "maxResults": 10
                            }
                        ]
                    }
                ]
            }
            
            response = requests.post(
                f"{self.base_url}?key={self.api_key}",
                json=payload,
                timeout=30
            )
            response.raise_for_status()
            
            data = response.json()
            
            # Process Google Vision results
            identified_items = []
            description_parts = []
            
            if 'responses' in data and data['responses']:
                response_data = data['responses'][0]
                
                # Process labels
                labels = response_data.get('labelAnnotations', [])
                lego_related_labels = [label for label in labels if 'lego' in label['description'].lower()]
                
                for label in lego_related_labels:
                    if label['score'] > 0.7:  # High confidence threshold
                        # Create a generic LEGO item based on label
                        item = LegoItem(
                            item_number=None,
                            name=label['description'],
                            item_type=ItemType.MINIFIGURE,  # Default assumption
                            condition=ItemCondition.USED_COMPLETE,
                            year_released=None,
                            theme=None,
                            category=None,
                            pieces=None,
                        )
                        identified_items.append(item)
                        description_parts.append(f"Detected: {label['description']} (confidence: {label['score']:.2f})")
                
                # Process text (might contain set numbers, names)
                text_annotations = response_data.get('textAnnotations', [])
                for text in text_annotations:
                    text_content = text['description'].lower()
                    if any(keyword in text_content for keyword in ['lego', 'minifigure', 'set']):
                        description_parts.append(f"Text found: {text['description']}")
            
            return IdentificationResult(
                confidence_score=0.6 if identified_items else 0.2,
                identified_items=identified_items,
                description="; ".join(description_parts) if description_parts else "No LEGO items clearly identified",
                condition_assessment="Cannot assess condition from basic vision analysis"
            )
            
        except Exception as e:
            logger.error(f"Google Vision error: {e}")
            return IdentificationResult(
                confidence_score=0.0,
                identified_items=[],
                description=f"Error during identification: {str(e)}",
                condition_assessment="Could not assess condition due to error"
            )


class LocalImageAnalysisIdentifier:
    """Local image analysis using computer vision libraries"""
    
    def __init__(self):
        try:
            import cv2
            import numpy as np
            self.cv2 = cv2
            self.np = np
            self.available = True
        except ImportError:
            logger.warning("OpenCV not available for local image analysis")
            self.available = False
    
    async def identify_lego_items(self, image_path: str) -> IdentificationResult:
        """Basic local image analysis for LEGO detection"""
        if not self.available:
            return IdentificationResult(
                confidence_score=0.0,
                identified_items=[],
                description="Local image analysis not available (OpenCV required)",
                condition_assessment="Cannot assess"
            )
        
        try:
            # Load image
            image = self.cv2.imread(image_path)
            if image is None:
                return IdentificationResult(
                    confidence_score=0.0,
                    identified_items=[],
                    description="Could not load image",
                    condition_assessment="Cannot assess"
                )
            
            # Convert to different color spaces for analysis
            hsv = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2HSV)
            gray = self.cv2.cvtColor(image, self.cv2.COLOR_BGR2GRAY)
            
            # Look for LEGO-like features
            lego_features = self._detect_lego_features(image, hsv, gray)
            
            # Create basic identification results
            identified_items = []
            if lego_features['minifigure_count'] > 0:
                for i in range(lego_features['minifigure_count']):
                    item = LegoItem(
                        item_number=None,
                        name=f"LEGO Minifigure {i+1}",
                        item_type=ItemType.MINIFIGURE,
                        condition=ItemCondition.USED_COMPLETE,
                        year_released=None,
                        theme=None,
                        category=None,
                        pieces=None,
                    )
                    identified_items.append(item)
            
            description_parts = []
            if lego_features['minifigure_count'] > 0:
                description_parts.append(f"Detected {lego_features['minifigure_count']} potential minifigures")
            if lego_features['color_count'] > 0:
                description_parts.append(f"Found {lego_features['color_count']} distinct colors")
            if lego_features['rectangular_shapes'] > 0:
                description_parts.append(f"Detected {lego_features['rectangular_shapes']} rectangular shapes")
            
            return IdentificationResult(
                confidence_score=0.4 if identified_items else 0.1,
                identified_items=identified_items,
                description="; ".join(description_parts) if description_parts else "No clear LEGO features detected",
                condition_assessment="Cannot assess condition from basic analysis"
            )
            
        except Exception as e:
            logger.error(f"Local image analysis error: {e}")
            return IdentificationResult(
                confidence_score=0.0,
                identified_items=[],
                description=f"Error during local analysis: {str(e)}",
                condition_assessment="Could not assess condition due to error"
            )
    
    def _detect_lego_features(self, image, hsv, gray):
        """Detect LEGO-like features in the image"""
        features = {
            'minifigure_count': 0,
            'color_count': 0,
            'rectangular_shapes': 0
        }
        
        try:
            # Detect colors (LEGO pieces are typically bright and distinct)
            # Convert to HSV and find distinct color regions
            color_ranges = [
                ([0, 50, 50], [10, 255, 255]),    # Red
                ([20, 50, 50], [30, 255, 255]),   # Yellow
                ([100, 50, 50], [130, 255, 255]), # Blue
                ([40, 50, 50], [80, 255, 255]),   # Green
            ]
            
            distinct_colors = set()
            for lower, upper in color_ranges:
                mask = self.cv2.inRange(hsv, self.np.array(lower), self.np.array(upper))
                if self.cv2.countNonZero(mask) > 100:  # Significant color presence
                    distinct_colors.add(tuple(lower))
            
            features['color_count'] = len(distinct_colors)
            
            # Detect rectangular shapes (LEGO pieces are often rectangular)
            edges = self.cv2.Canny(gray, 50, 150)
            contours, _ = self.cv2.findContours(edges, self.cv2.RETR_EXTERNAL, self.cv2.CHAIN_APPROX_SIMPLE)
            
            rectangular_count = 0
            for contour in contours:
                approx = self.cv2.approxPolyDP(contour, 0.02 * self.cv2.arcLength(contour, True), True)
                if len(approx) == 4:  # Rectangular shape
                    area = self.cv2.contourArea(contour)
                    if 100 < area < 10000:  # Reasonable size for LEGO pieces
                        rectangular_count += 1
            
            features['rectangular_shapes'] = rectangular_count
            
            # Estimate minifigure count based on detected features
            # This is a very basic heuristic
            if features['color_count'] >= 3 and features['rectangular_shapes'] >= 2:
                features['minifigure_count'] = min(features['rectangular_shapes'] // 2, 5)
            
        except Exception as e:
            logger.error(f"Error in LEGO feature detection: {e}")
        
        return features


class HybridIdentifier:
    """Hybrid identifier that tries multiple methods in order of cost"""
    
    def __init__(self, claude_api_key: str, openai_api_key: str = None, google_api_key: str = None):
        self.identifiers = []
        
        # Add Claude as primary (most accurate but most expensive)
        from src.core.lego_identifier import LegoIdentifier
        self.identifiers.append(('claude', LegoIdentifier()))
        
        # Add alternatives in order of cost (cheapest first)
        if openai_api_key:
            self.identifiers.append(('openai', OpenAIVisionIdentifier(openai_api_key)))
        
        if google_api_key:
            self.identifiers.append(('google', GoogleVisionIdentifier(google_api_key)))
        
        # Always add local analysis as fallback
        self.identifiers.append(('local', LocalImageAnalysisIdentifier()))
    
    async def identify_lego_items(self, image_path: str, max_cost: str = 'medium') -> IdentificationResult:
        """Identify LEGO items using the most cost-effective method that meets requirements"""
        
        # Define cost tiers
        cost_tiers = {
            'low': ['local', 'google'],
            'medium': ['local', 'google', 'openai'],
            'high': ['local', 'google', 'openai', 'claude']
        }
        
        allowed_methods = cost_tiers.get(max_cost, cost_tiers['medium'])
        
        for method_name, identifier in self.identifiers:
            if method_name not in allowed_methods:
                continue
            
            try:
                logger.info(f"Trying {method_name} identifier")
                result = await identifier.identify_lego_items(image_path)
                
                # If we get a good result, use it
                if result.confidence_score > 0.5 or (result.identified_items and result.confidence_score > 0.3):
                    logger.info(f"Using {method_name} result with confidence {result.confidence_score:.2f}")
                    return result
                
                # If confidence is too low, try next method
                logger.info(f"{method_name} confidence too low ({result.confidence_score:.2f}), trying next method")
                
            except Exception as e:
                logger.error(f"{method_name} failed: {e}, trying next method")
                continue
        
        # If all methods failed, return the last result (likely from local analysis)
        logger.warning("All identification methods failed, returning fallback result")
        return IdentificationResult(
            confidence_score=0.1,
            identified_items=[],
            description="All identification methods failed",
            condition_assessment="Cannot assess"
        )
    
    def get_cost_estimate(self, method: str) -> Dict[str, Any]:
        """Get cost estimate for different methods"""
        cost_estimates = {
            'claude': {
                'cost_per_image': 0.01,  # Approximate
                'accuracy': 0.9,
                'speed': 'medium'
            },
            'openai': {
                'cost_per_image': 0.005,  # Approximate
                'accuracy': 0.8,
                'speed': 'fast'
            },
            'google': {
                'cost_per_image': 0.001,  # Approximate
                'accuracy': 0.6,
                'speed': 'fast'
            },
            'local': {
                'cost_per_image': 0.0,
                'accuracy': 0.4,
                'speed': 'very_fast'
            }
        }
        
        return cost_estimates.get(method, {})
