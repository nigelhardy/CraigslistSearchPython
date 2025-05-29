"""
Configuration settings for Craigslist scraper.
"""

from dataclasses import dataclass
from typing import Dict, Any, List


@dataclass
class SearchConfig:
    """Configuration for a specific search area."""
    query: str
    city: str
    categories: List[str]  # Now supports multiple categories
    filters: Dict[str, Any]
    name: str
    description: str


class Config:
    """Main configuration class containing all application settings."""

    # Search configurations
    SEARCH_CONFIGS = {
        "SC": SearchConfig(
            query="",
            city="sfbay",
            categories=["apa"],
            filters={
                "max_price": 3300,
                "lat": 36.9677,
                "lon": -121.985,
                "search_distance": 10,
            },
            name="Santa Cruz",
            description="Santa Cruz apartment search near boardwalk"
        ),
        "LG": SearchConfig(
            query="",
            city="sfbay",
            categories=["apa"],
            filters={
                "max_price": 4000,
                "postal": 95030,
                "search_distance": 5
            },
            name="Los Gatos",
            description="Los Gatos apartment search near work"
        ),
        "E39_PARTS": SearchConfig(
            query="e39",
            city="sfbay",
            categories=["pta", "wta"],  # auto parts and wheels/tires (correct codes)
            filters={
                "max_price": 1000,  # Reasonable max for most parts
                "min_price": 10,    # Avoid super cheap junk
            },
            name="BMW E39 Parts",
            description="BMW E39 540i parts search in multiple categories"
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

    # Available search types for CLI
    AVAILABLE_SEARCH_TYPES = list(SEARCH_CONFIGS.keys())

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
