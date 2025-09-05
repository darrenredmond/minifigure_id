from sqlalchemy import Column, Integer, String, Float, DateTime, Text, JSON, Boolean
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import relationship
from datetime import datetime

Base = declarative_base()


class ValuationRecord(Base):
    __tablename__ = "valuation_records"

    id = Column(Integer, primary_key=True, index=True)

    # Image information
    image_filename = Column(String(255), nullable=False)
    original_filename = Column(String(255))
    image_size = Column(Integer)  # File size in bytes
    upload_timestamp = Column(DateTime, default=datetime.utcnow)

    # Identification results (stored as JSON)
    identification_data = Column(JSON)  # Serialized IdentificationResult
    confidence_score = Column(Float)

    # Valuation results
    estimated_value = Column(Float)
    valuation_confidence = Column(Float)
    recommendation_category = Column(String(50))  # museum, resale, collection
    reasoning = Column(Text)
    suggested_platforms = Column(JSON)  # List of platform names

    # Market data (stored as JSON)
    market_data = Column(JSON)  # Serialized MarketData

    # Metadata
    notes = Column(Text)  # User notes
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)

    # Status tracking
    is_archived = Column(Boolean, default=False)
    status = Column(String(50), default="pending")  # pending, reviewed, sold, archived


class InventoryItem(Base):
    __tablename__ = "inventory_items"

    id = Column(Integer, primary_key=True, index=True)

    # LEGO item details
    item_number = Column(String(50))  # LEGO/BrickLink item number
    item_name = Column(String(255))
    item_type = Column(String(50))  # minifigure, set, part
    condition = Column(String(50))  # new, used_complete, etc.

    # Physical details
    year_released = Column(Integer)
    theme = Column(String(100))
    category = Column(String(100))
    pieces = Column(Integer)

    # Valuation
    estimated_value = Column(Float)
    purchase_price = Column(Float)
    current_market_price = Column(Float)
    last_price_update = Column(DateTime)

    # Location and status
    location = Column(String(255))  # Physical location in shop
    status = Column(
        String(50), default="in_inventory"
    )  # in_inventory, on_display, sold, reserved

    # Links
    valuation_record_id = Column(Integer)  # Link to original valuation

    # Metadata
    notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
    updated_at = Column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class SaleRecord(Base):
    __tablename__ = "sale_records"

    id = Column(Integer, primary_key=True, index=True)

    # Item reference
    inventory_item_id = Column(Integer)
    valuation_record_id = Column(Integer)

    # Sale details
    sale_price = Column(Float, nullable=False)
    platform_sold = Column(String(50))  # bricklink, ebay, etc.
    buyer_info = Column(String(255))  # Anonymized buyer reference

    # Dates
    listed_date = Column(DateTime)
    sold_date = Column(DateTime, nullable=False)

    # Financial
    platform_fees = Column(Float, default=0.0)
    shipping_cost = Column(Float, default=0.0)
    net_profit = Column(Float)  # Calculated field

    # Notes
    sale_notes = Column(Text)
    created_at = Column(DateTime, default=datetime.utcnow)
