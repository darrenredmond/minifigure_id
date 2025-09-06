from typing import List, Dict, Tuple
from datetime import datetime, timedelta

from config.settings import settings
from src.models.schemas import (
    IdentificationResult,
    ValuationResult,
    MarketData,
    LegoItem,
    RecommendationCategory,
    PlatformType,
    ItemCondition,
    ItemType,
    ItemValuation,
    DetailedPricing,
)
from src.external.bricklink_client import BrickLinkClient


class ValuationEngine:
    def __init__(self):
        self.bricklink_client = BrickLinkClient()

    async def evaluate_item(
        self, identification: IdentificationResult
    ) -> ValuationResult:
        """Main evaluation method that combines all valuation factors with individual item breakdown"""
        if not identification.identified_items:
            return self._create_fallback_valuation(identification)

        # Get current exchange rate
        exchange_rate = self.bricklink_client.get_current_exchange_rate()

        # Create individual valuations for each item
        individual_valuations = []
        total_estimated_value_usd = 0.0
        confidence_scores = []
        market_data_list = []

        for item in identification.identified_items:
            # Create individual valuation
            item_valuation = await self._create_individual_valuation(item, exchange_rate)
            individual_valuations.append(item_valuation)
            
            # Add to totals
            if item_valuation.estimated_individual_value_usd:
                total_estimated_value_usd += item_valuation.estimated_individual_value_usd
            confidence_scores.append(item_valuation.confidence_score)
            
            # Collect market data for reasoning
            if item_valuation.market_data:
                market_data_list.append(item_valuation.market_data)

        # Calculate EUR total
        total_estimated_value_eur = None
        if exchange_rate and total_estimated_value_usd > 0:
            total_estimated_value_eur = total_estimated_value_usd * exchange_rate

        # Calculate overall confidence
        avg_confidence = (
            sum(confidence_scores) / len(confidence_scores)
            if confidence_scores
            else 0.3
        )

        # Adjust for identification confidence
        final_confidence = (avg_confidence + identification.confidence_score) / 2

        # Determine recommendation category
        recommendation = self._determine_recommendation_category(
            total_estimated_value_usd, identification
        )

        # Get suggested platforms
        suggested_platforms = self._get_suggested_platforms(
            total_estimated_value_usd, identification.identified_items
        )

        # Create reasoning
        reasoning = self._generate_reasoning(
            identification, market_data_list, total_estimated_value_usd, recommendation
        )

        # Use the first market data item for the combined result
        combined_market_data = market_data_list[0] if market_data_list else None

        return ValuationResult(
            estimated_value=total_estimated_value_usd,
            estimated_value_eur=total_estimated_value_eur,
            confidence_score=final_confidence,
            recommendation=recommendation,
            reasoning=reasoning,
            suggested_platforms=suggested_platforms,
            market_data=combined_market_data,
            individual_valuations=individual_valuations,
            exchange_rate_usd_eur=exchange_rate,
        )

    async def _get_market_data(self, item: LegoItem) -> MarketData:
        """Get market data for a specific LEGO item"""
        if not item.item_number:
            return MarketData()  # Empty market data

        # Determine BrickLink item type
        bl_item_type = "MINIFIG" if item.item_type == ItemType.MINIFIGURE else "SET"

        # Determine condition code
        condition_code = "N" if item.condition == ItemCondition.NEW else "U"

        # Get price guide from BrickLink
        market_data = self.bricklink_client.get_price_guide(
            bl_item_type, item.item_number, condition_code
        )

        return market_data or MarketData()

    async def _create_individual_valuation(
        self, item: LegoItem, exchange_rate: float
    ) -> ItemValuation:
        """Create detailed individual valuation for a single item"""
        
        # Get basic market data
        market_data = await self._get_market_data(item)
        
        # Get detailed pricing if item number is available
        detailed_pricing = None
        if item.item_number:
            bl_item_type = "MINIFIG" if item.item_type == ItemType.MINIFIGURE else "SET"
            detailed_pricing = self.bricklink_client.get_detailed_pricing(
                bl_item_type, item.item_number
            )
        
        # Calculate individual item value
        item_value_usd, item_confidence = self._calculate_item_value(item, market_data)
        
        # Calculate EUR value
        item_value_eur = None
        if exchange_rate and item_value_usd > 0:
            item_value_eur = item_value_usd * exchange_rate
        
        # Create notes based on item characteristics
        notes = []
        if item.theme:
            notes.append(f"Theme: {item.theme}")
        if item.year_released:
            current_year = datetime.now().year
            age = current_year - item.year_released
            if age > 20:
                notes.append("Vintage item (20+ years old)")
            elif age > 10:
                notes.append("Classic item (10+ years old)")
        if market_data and market_data.availability:
            notes.append(f"Availability: {market_data.availability}")
        
        notes_text = "; ".join(notes) if notes else None
        
        return ItemValuation(
            item=item,
            detailed_pricing=detailed_pricing,
            estimated_individual_value_usd=item_value_usd if item_value_usd > 0 else None,
            estimated_individual_value_eur=item_value_eur if item_value_eur and item_value_eur > 0 else None,
            confidence_score=item_confidence,
            market_data=market_data,
            notes=notes_text,
        )

    def _calculate_item_value(
        self, item: LegoItem, market_data: MarketData
    ) -> Tuple[float, float]:
        """Calculate the estimated value and confidence for a single item"""
        base_value = market_data.current_price or 0.0
        confidence = 0.5

        # Adjust based on condition
        condition_multipliers = {
            ItemCondition.NEW: 1.0,
            ItemCondition.USED_COMPLETE: 0.8,
            ItemCondition.USED_INCOMPLETE: 0.4,
            ItemCondition.DAMAGED: 0.2,
        }

        condition_multiplier = condition_multipliers.get(item.condition, 0.6)
        adjusted_value = base_value * condition_multiplier

        # Increase confidence if we have market data
        if market_data.current_price:
            confidence += 0.3

        # Adjust for rarity
        if market_data.availability:
            rarity_multipliers = {
                "very_rare": 2.0,
                "rare": 1.5,
                "uncommon": 1.1,
                "common": 1.0,
            }
            rarity_multiplier = rarity_multipliers.get(market_data.availability, 1.0)
            adjusted_value *= rarity_multiplier

            if market_data.availability in ["rare", "very_rare"]:
                confidence += 0.1

        # Age factor - older items may be worth more
        if item.year_released:
            current_year = datetime.now().year
            age = current_year - item.year_released
            if age > 20:
                adjusted_value *= 1.3  # Vintage bonus
                confidence += 0.1
            elif age > 10:
                adjusted_value *= 1.1

        return max(adjusted_value, 0.0), min(confidence, 1.0)

    def _determine_recommendation_category(
        self, estimated_value: float, identification: IdentificationResult
    ) -> RecommendationCategory:
        """Determine whether item should go to museum, resale, or collection"""

        # Museum criteria
        if estimated_value >= settings.museum_threshold:
            return RecommendationCategory.MUSEUM

        # Check for special characteristics that warrant museum preservation
        description_lower = identification.description.lower()
        museum_keywords = [
            "rare",
            "prototype",
            "limited edition",
            "exclusive",
            "first edition",
            "unreleased",
            "test",
            "employee",
            "promotional",
        ]

        if any(keyword in description_lower for keyword in museum_keywords):
            return RecommendationCategory.MUSEUM

        # Resale if above rare threshold
        if estimated_value >= settings.rare_threshold:
            return RecommendationCategory.RESALE

        # Otherwise, collection
        return RecommendationCategory.COLLECTION

    def _get_suggested_platforms(
        self, estimated_value: float, items: List[LegoItem]
    ) -> List[PlatformType]:
        """Suggest the best platforms for resale based on value and item type"""
        platforms = []

        # High-value items
        if estimated_value >= 200:
            platforms.extend([PlatformType.BRICKLINK, PlatformType.LOCAL_AUCTION])

        # Medium-value items
        elif estimated_value >= 50:
            platforms.extend([PlatformType.BRICKLINK, PlatformType.EBAY])

        # Lower-value items
        else:
            platforms.extend([PlatformType.FACEBOOK_MARKETPLACE, PlatformType.EBAY])

        # Always include BrickLink for LEGO items as it's the specialist marketplace
        if PlatformType.BRICKLINK not in platforms:
            platforms.insert(0, PlatformType.BRICKLINK)

        return platforms[:3]  # Limit to top 3 recommendations

    def _generate_reasoning(
        self,
        identification: IdentificationResult,
        market_data_list: List[MarketData],
        estimated_value: float,
        recommendation: RecommendationCategory,
    ) -> str:
        """Generate human-readable reasoning for the valuation"""
        reasoning_parts = []

        # Identification confidence
        if identification.confidence_score >= 0.8:
            reasoning_parts.append("High confidence in item identification.")
        elif identification.confidence_score >= 0.5:
            reasoning_parts.append("Moderate confidence in item identification.")
        else:
            reasoning_parts.append(
                "Lower confidence in identification - manual verification recommended."
            )

        # Market data availability
        has_market_data = any(md.current_price for md in market_data_list)
        if has_market_data:
            reasoning_parts.append("Current market data available from BrickLink.")
        else:
            reasoning_parts.append(
                "Limited market data - valuation based on similar items."
            )

        # Value assessment
        if estimated_value >= settings.museum_threshold:
            reasoning_parts.append(
                f"High estimated value (${estimated_value:.2f}) suggests museum-quality piece."
            )
        elif estimated_value >= settings.rare_threshold:
            reasoning_parts.append(
                f"Estimated value of ${estimated_value:.2f} indicates good resale potential."
            )
        else:
            reasoning_parts.append(
                f"Estimated value of ${estimated_value:.2f} suggests personal collection value."
            )

        # Condition impact
        condition_text = identification.condition_assessment
        if "excellent" in condition_text.lower() or "mint" in condition_text.lower():
            reasoning_parts.append("Excellent condition enhances value.")
        elif "damage" in condition_text.lower() or "wear" in condition_text.lower():
            reasoning_parts.append("Condition issues may reduce market value.")

        # Recommendation explanation
        if recommendation == RecommendationCategory.MUSEUM:
            reasoning_parts.append(
                "Recommended for museum due to rarity, value, or historical significance."
            )
        elif recommendation == RecommendationCategory.RESALE:
            reasoning_parts.append("Good candidate for resale to collectors.")
        else:
            reasoning_parts.append("Suitable for personal collection or local sale.")

        return " ".join(reasoning_parts)

    def _create_fallback_valuation(
        self, identification: IdentificationResult
    ) -> ValuationResult:
        """Create a fallback valuation when no items are identified"""
        return ValuationResult(
            estimated_value=0.0,
            estimated_value_eur=0.0,
            confidence_score=0.1,
            recommendation=RecommendationCategory.COLLECTION,
            reasoning="Unable to identify specific LEGO items in the image. Manual assessment recommended.",
            suggested_platforms=[PlatformType.FACEBOOK_MARKETPLACE],
            market_data=None,
            individual_valuations=[],
            exchange_rate_usd_eur=None,
        )
