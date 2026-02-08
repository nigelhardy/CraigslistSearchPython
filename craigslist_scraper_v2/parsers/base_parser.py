"""Base parser interface for converting HTML/data to Listing objects."""
from abc import ABC, abstractmethod
from typing import Optional
from bs4 import BeautifulSoup

from models import Listing


class ListingParser(ABC):
    """Abstract base class for parsing listing data from various sources.
    
    This abstraction allows us to parse listings from different sources
    (Craigslist, Facebook Marketplace, etc.) using the same interface.
    """
    
    @abstractmethod
    def parse(self, soup: BeautifulSoup, base_listing: Listing) -> Optional[Listing]:
        """Parse BeautifulSoup HTML into a fully populated Listing object.
        
        Args:
            soup: BeautifulSoup object containing the listing detail page HTML
            base_listing: Listing object with basic info (url, title, price, etc.)
                         from the search results page
                         
        Returns:
            Fully populated Listing object (Listing or VehicleListing), or None if parsing fails
        """
        pass
    
    @abstractmethod
    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Check if this parser can handle the given HTML.
        
        Args:
            soup: BeautifulSoup object to check
            
        Returns:
            True if this parser can parse this HTML structure
        """
        pass
