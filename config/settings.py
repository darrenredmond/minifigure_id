from pydantic_settings import BaseSettings
from typing import List


class Settings(BaseSettings):
    # API Keys
    anthropic_api_key: str
    bricklink_consumer_key: str = ""
    bricklink_consumer_secret: str = ""
    bricklink_token_value: str = ""
    bricklink_token_secret: str = ""
    
    # Database
    database_url: str = "sqlite:///./data/minifigure_valuation.db"
    
    # App settings
    debug: bool = False
    max_upload_size: int = 10485760  # 10MB
    allowed_image_types: List[str] = ["jpg", "jpeg", "png", "webp"]
    
    # Valuation thresholds
    museum_threshold: float = 500.0
    rare_threshold: float = 100.0
    
    class Config:
        env_file = ".env"
        case_sensitive = False


settings = Settings()