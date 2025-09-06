from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Any
from datetime import datetime
from enum import Enum


class ItemType(str, Enum):
    MINIFIGURE = "minifigure"
    SET = "set"
    PART = "part"


class ItemCondition(str, Enum):
    NEW = "new"
    USED_COMPLETE = "used_complete"
    USED_INCOMPLETE = "used_incomplete"
    DAMAGED = "damaged"


class RecommendationCategory(str, Enum):
    MUSEUM = "museum"
    RESALE = "resale"
    COLLECTION = "collection"


class PlatformType(str, Enum):
    BRICKLINK = "bricklink"
    EBAY = "ebay"
    FACEBOOK_MARKETPLACE = "facebook_marketplace"
    LOCAL_AUCTION = "local_auction"


class LegoItem(BaseModel):
    item_number: Optional[str] = None
    name: Optional[str] = None
    item_type: ItemType
    condition: ItemCondition
    year_released: Optional[int] = None
    theme: Optional[str] = None
    category: Optional[str] = None
    pieces: Optional[int] = None


class MarketData(BaseModel):
    current_price: Optional[float] = None
    avg_price_6m: Optional[float] = None
    price_trend: Optional[str] = None  # "increasing", "decreasing", "stable"
    times_sold: Optional[int] = None
    last_sold_date: Optional[datetime] = None
    availability: Optional[str] = None  # "common", "uncommon", "rare", "very_rare"


class DetailedPricing(BaseModel):
    """Detailed pricing for different conditions"""
    msrp_usd: Optional[float] = None
    msrp_eur: Optional[float] = None
    sealed_new_usd: Optional[float] = None
    sealed_new_eur: Optional[float] = None
    used_complete_usd: Optional[float] = None
    used_complete_eur: Optional[float] = None
    used_incomplete_usd: Optional[float] = None
    used_incomplete_eur: Optional[float] = None
    missing_instructions_usd: Optional[float] = None
    missing_instructions_eur: Optional[float] = None
    missing_box_usd: Optional[float] = None
    missing_box_eur: Optional[float] = None


class ItemValuation(BaseModel):
    """Individual item valuation with detailed pricing"""
    item: LegoItem
    detailed_pricing: Optional[DetailedPricing] = None
    estimated_individual_value_usd: Optional[float] = None
    estimated_individual_value_eur: Optional[float] = None
    confidence_score: float = Field(ge=0, le=1)
    market_data: Optional[MarketData] = None
    notes: Optional[str] = None


class ValuationResult(BaseModel):
    estimated_value: float
    estimated_value_eur: Optional[float] = None
    confidence_score: float = Field(ge=0, le=1)
    recommendation: RecommendationCategory
    reasoning: str
    suggested_platforms: List[PlatformType]
    market_data: Optional[MarketData] = None
    individual_valuations: List[ItemValuation] = []
    exchange_rate_usd_eur: Optional[float] = None


class IdentificationResult(BaseModel):
    confidence_score: float = Field(ge=0, le=1)
    identified_items: List[LegoItem]
    description: str
    condition_assessment: str


class ValuationReport(BaseModel):
    id: Optional[str] = None
    image_filename: str
    image_path: Optional[str] = None
    upload_timestamp: datetime
    identification: IdentificationResult
    valuation: ValuationResult
    notes: Optional[str] = None
    created_at: datetime = Field(default_factory=datetime.now)


class ImageUpload(BaseModel):
    filename: str
    content_type: str
    size: int
