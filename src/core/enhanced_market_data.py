"""
Enhanced Market Data Aggregator with multiple sources and fallback strategies
"""
import asyncio
import logging
from typing import List, Dict, Any, Optional, Tuple
from datetime import datetime, timedelta
import requests
from dataclasses import dataclass

from src.models.schemas import MarketData, DetailedPricing
from src.external.bricklink_client import BrickLinkClient

logger = logging.getLogger(__name__)


@dataclass
class MarketDataSource:
    """Represents a market data source with reliability metrics"""
    name: str
    reliability_score: float
    last_success: Optional[datetime] = None
    failure_count: int = 0
    max_failures: int = 3


class EnhancedMarketDataAggregator:
    """Enhanced market data aggregation with multiple sources and fallback strategies"""
    
    def __init__(self):
        self.bricklink_client = BrickLinkClient()
        self.sources = {
            'bricklink': MarketDataSource('BrickLink', 0.9),
            'ebay_estimate': MarketDataSource('eBay Estimate', 0.7),
            'local_market': MarketDataSource('Local Market', 0.6),
        }
        self.cache = {}
        self.cache_duration = timedelta(hours=6)  # Cache for 6 hours
    
    def _get_cache_key(self, item_number: str, item_type: str, condition: str) -> str:
        """Generate cache key for market data"""
        return f"{item_type}_{item_number}_{condition}"
    
    def _is_cache_valid(self, cache_entry: Dict[str, Any]) -> bool:
        """Check if cache entry is still valid"""
        if not cache_entry:
            return False
        cached_time = cache_entry.get('timestamp')
        if not cached_time:
            return False
        return datetime.now() - cached_time < self.cache_duration
    
    async def get_enhanced_market_data(self, item: 'LegoItem') -> MarketData:
        """Get enhanced market data with multiple sources and fallback strategies"""
        if not item.item_number:
            return self._create_fallback_market_data(item)
        
        # Check cache first
        cache_key = self._get_cache_key(
            item.item_number, 
            item.item_type.value if item.item_type else "minifigure",
            item.condition.value if item.condition else "used_complete"
        )
        
        if cache_key in self.cache and self._is_cache_valid(self.cache[cache_key]):
            logger.info(f"Using cached market data for {item.item_number}")
            return MarketData(**self.cache[cache_key]['data'])
        
        # Try multiple sources in parallel
        tasks = []
        if self.sources['bricklink'].failure_count < self.sources['bricklink'].max_failures:
            tasks.append(self._get_bricklink_data(item))
        
        tasks.append(self._get_ebay_estimate(item))
        tasks.append(self._get_local_market_estimate(item))
        
        # Run all tasks in parallel
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results and create aggregated market data
        market_data = self._aggregate_market_data(item, results)
        
        # Cache the result
        self.cache[cache_key] = {
            'data': market_data.model_dump(),
            'timestamp': datetime.now()
        }
        
        return market_data
    
    async def _get_bricklink_data(self, item: 'LegoItem') -> Optional[MarketData]:
        """Get data from BrickLink API"""
        try:
            bl_item_type = "MINIFIG" if item.item_type.value == "minifigure" else "SET"
            condition_code = "N" if item.condition.value == "new" else "U"
            
            market_data = self.bricklink_client.get_price_guide(
                bl_item_type, item.item_number, condition_code
            )
            
            if market_data and market_data.current_price:
                self.sources['bricklink'].last_success = datetime.now()
                self.sources['bricklink'].failure_count = 0
                return market_data
            else:
                self.sources['bricklink'].failure_count += 1
                return None
                
        except Exception as e:
            logger.error(f"BrickLink API error: {e}")
            self.sources['bricklink'].failure_count += 1
            return None
    
    async def _get_ebay_estimate(self, item: 'LegoItem') -> Optional[MarketData]:
        """Get estimated data from eBay (simulated - would need actual eBay API)"""
        try:
            # This is a placeholder - in reality you'd call eBay API
            # For now, we'll create a reasonable estimate based on item characteristics
            estimated_price = self._estimate_price_from_characteristics(item)
            
            if estimated_price:
                return MarketData(
                    current_price=estimated_price,
                    avg_price_6m=estimated_price * 0.95,  # Slightly lower 6-month average
                    times_sold=5,  # Estimated
                    availability="uncommon",
                    last_sold_date=datetime.now() - timedelta(days=30)
                )
            return None
            
        except Exception as e:
            logger.error(f"eBay estimate error: {e}")
            return None
    
    async def _get_local_market_estimate(self, item: 'LegoItem') -> Optional[MarketData]:
        """Get local market estimate (simulated)"""
        try:
            # This would integrate with local market data sources
            # For now, create a conservative estimate
            estimated_price = self._estimate_price_from_characteristics(item)
            
            if estimated_price:
                # Local market typically 10-20% lower than online
                local_price = estimated_price * 0.85
                return MarketData(
                    current_price=local_price,
                    avg_price_6m=local_price,
                    times_sold=2,
                    availability="rare",
                    last_sold_date=datetime.now() - timedelta(days=60)
                )
            return None
            
        except Exception as e:
            logger.error(f"Local market estimate error: {e}")
            return None
    
    def _estimate_price_from_characteristics(self, item: 'LegoItem') -> Optional[float]:
        """Estimate price based on item characteristics when no market data available"""
        base_price = 0.0
        
        # Base price by type
        if item.item_type and item.item_type.value == "minifigure":
            base_price = 5.0  # Base minifigure price
        elif item.item_type and item.item_type.value == "set":
            base_price = 20.0  # Base set price
        else:
            base_price = 2.0  # Base part price
        
        # Adjust for theme rarity
        theme_multipliers = {
            "Star Wars": 2.0,
            "Super Heroes": 1.8,
            "Ninjago": 1.5,
            "Friends": 1.2,
            "City": 1.0,
            "Creator": 0.8,
        }
        
        if item.theme and item.theme in theme_multipliers:
            base_price *= theme_multipliers[item.theme]
        
        # Adjust for age (older items generally more valuable)
        if item.year_released:
            current_year = datetime.now().year
            age = current_year - item.year_released
            if age > 20:
                base_price *= 2.0  # Vintage bonus
            elif age > 10:
                base_price *= 1.5  # Classic bonus
            elif age > 5:
                base_price *= 1.2  # Recent bonus
        
        # Adjust for condition
        condition_multipliers = {
            "new": 1.0,
            "used_complete": 0.8,
            "used_incomplete": 0.4,
            "damaged": 0.2,
        }
        
        if item.condition and item.condition.value in condition_multipliers:
            base_price *= condition_multipliers[item.condition.value]
        
        return base_price if base_price > 0 else None
    
    def _aggregate_market_data(self, item: 'LegoItem', results: List[Any]) -> MarketData:
        """Aggregate market data from multiple sources"""
        valid_results = [r for r in results if isinstance(r, MarketData) and r.current_price]
        
        if not valid_results:
            return self._create_fallback_market_data(item)
        
        # Weight sources by reliability
        total_weight = 0
        weighted_price = 0
        weighted_6m_price = 0
        total_times_sold = 0
        availability_scores = []
        
        for result in valid_results:
            # Determine source reliability (simplified)
            source_weight = 0.8  # Default weight
            if hasattr(result, 'source') and result.source in self.sources:
                source_weight = self.sources[result.source].reliability_score
            
            weighted_price += result.current_price * source_weight
            if result.avg_price_6m:
                weighted_6m_price += result.avg_price_6m * source_weight
            if result.times_sold:
                total_times_sold += result.times_sold
            if result.availability:
                availability_scores.append(result.availability)
            
            total_weight += source_weight
        
        if total_weight == 0:
            return self._create_fallback_market_data(item)
        
        # Calculate weighted averages
        final_price = weighted_price / total_weight
        final_6m_price = weighted_6m_price / total_weight if weighted_6m_price > 0 else final_price
        
        # Determine availability based on times sold
        avg_times_sold = total_times_sold / len(valid_results)
        if avg_times_sold == 0:
            availability = "very_rare"
        elif avg_times_sold < 5:
            availability = "rare"
        elif avg_times_sold < 20:
            availability = "uncommon"
        else:
            availability = "common"
        
        return MarketData(
            current_price=final_price,
            avg_price_6m=final_6m_price,
            times_sold=int(avg_times_sold),
            availability=availability,
            last_sold_date=datetime.now() - timedelta(days=7)  # Recent estimate
        )
    
    def _create_fallback_market_data(self, item: 'LegoItem') -> MarketData:
        """Create fallback market data when no sources are available"""
        estimated_price = self._estimate_price_from_characteristics(item)
        
        return MarketData(
            current_price=estimated_price,
            avg_price_6m=estimated_price * 0.95 if estimated_price else None,
            times_sold=0,
            availability="unknown",
            last_sold_date=None
        )
    
    def get_source_reliability_report(self) -> Dict[str, Any]:
        """Get a report on source reliability"""
        report = {}
        for name, source in self.sources.items():
            report[name] = {
                'reliability_score': source.reliability_score,
                'failure_count': source.failure_count,
                'last_success': source.last_success.isoformat() if source.last_success else None,
                'status': 'healthy' if source.failure_count < source.max_failures else 'degraded'
            }
        return report
    
    def clear_cache(self):
        """Clear the market data cache"""
        self.cache.clear()
        logger.info("Market data cache cleared")
