"""
Configuration settings for Craigslist rental scraper.
"""

from dataclasses import dataclass
from typing import Dict, Any


@dataclass
class SearchConfig:
    """Configuration for a specific search area."""
    query: str
    city: str
    category: str
    filters: Dict[str, Any]
    name: str


class Config:
    """Main configuration class containing all application settings."""
    
    # Search configurations
    SEARCH_CONFIGS = {
        "SC": SearchConfig(
            query="",
            city="sfbay",
            category="apa",
            filters={
                "max_price": 3300,
                "lat": 36.9677,
                "lon": -121.985,
                "search_distance": 10,
            },
            name="Santa Cruz"
        ),
        "LG": SearchConfig(
            query="",
            city="sfbay", 
            category="apa",
            filters={
                "max_price": 4000,
                "postal": 95030,
                "search_distance": 5
            },
            name="Los Gatos"
        )
    }
    
    # File paths and naming
    DATA_FILE_TEMPLATE = "listings_{}.pkl"
    UNWANTED_FILE_TEMPLATE = "unwanted_listings_{}.pkl"
    HTML_PREVIEW_FILE = "email_preview.html"
    
    # Email settings
    SMTP_SERVER = "smtp.gmail.com"
    SMTP_PORT = 587
    EMAIL_SUBJECT_TEMPLATE = "New Apartment Listings! {}"
    
    # Environment variable names
    ENV_SENDER_EMAIL = "EMAIL_SENDER_ADDRESS"
    ENV_RECEIVER_EMAIL = "EMAIL_RECEIVER_ADDRESS"
    ENV_EMAIL_PASSWORD = "EMAIL_PASSWORD"
    
    # Default application settings
    DEFAULT_MAX_FETCHES = -1  # -1 means no limit
    DEFAULT_WAIT_MS = -1      # -1 means no wait
    DEFAULT_SEARCH_TYPE = "SC"
    
    # Rate limiting and error handling
    MAX_CONSECUTIVE_FAILS = 5
    SIMILARITY_THRESHOLD_TITLE = 0.9
    SIMILARITY_THRESHOLD_DESC = 0.8
    MIN_TITLE_LENGTH_FOR_SIMILARITY = 25
    MIN_DESC_LENGTH_FOR_SIMILARITY = 25
    
    # Application metadata
    APP_NAME = "Craigslist Rental Scraper"
    VERSION = "1.0.0"


# Convenience functions for getting configurations
def get_search_config(search_type: str) -> SearchConfig:
    """Get search configuration for the specified type."""
    if search_type not in Config.SEARCH_CONFIGS:
        raise ValueError(f"Unknown search type: {search_type}")
    return Config.SEARCH_CONFIGS[search_type]


def get_data_file_path(search_type: str) -> str:
    """Get the data file path for the specified search type."""
    return Config.DATA_FILE_TEMPLATE.format(search_type)


def get_unwanted_file_path(search_type: str) -> str:
    """Get the unwanted results file path for the specified search type."""
    return Config.UNWANTED_FILE_TEMPLATE.format(search_type)