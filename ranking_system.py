"""
Abstract base classes and interfaces for ranking algorithms.

This module provides the foundation for creating custom ranking algorithms
for different types of Craigslist searches (apartments, auto parts, etc.).
"""

from abc import ABC, abstractmethod
from typing import Dict, List, Tuple, Any, Optional
from dataclasses import dataclass


@dataclass
class RankingResult:
    """Result of a ranking operation."""
    sorted_listings: List[Dict]
    unwanted_listings: List[Dict]
    total_processed: int
    
    
class BaseRankingAlgorithm(ABC):
    """
    Abstract base class for all ranking algorithms.
    
    Each ranking algorithm should inherit from this class and implement
    the required methods for scoring and filtering listings.
    """
    
    def __init__(self, search_type: str):
        """
        Initialize the ranking algorithm.
        
        Args:
            search_type: Identifier for this search type (e.g., 'SC', 'LG', 'E39_PARTS')
        """
        self.search_type = search_type
    
    @abstractmethod
    def calculate_scores(self, listings: List[Dict]) -> RankingResult:
        """
        Calculate scores for a list of listings and return sorted results.
        
        Args:
            listings: List of listing dictionaries to score
            
        Returns:
            RankingResult containing sorted and unwanted listings
        """
        pass
    
    @abstractmethod
    def get_minimum_score_threshold(self) -> float:
        """
        Get the minimum score threshold for a listing to be considered.
        
        Returns:
            Minimum score threshold
        """
        pass
    
    @abstractmethod
    def get_search_categories(self) -> List[str]:
        """
        Get the Craigslist categories this algorithm should search.
        
        Returns:
            List of category codes (e.g., ['apa'], ['pts', 'wto'])
        """
        pass
    
    @abstractmethod
    def get_target_location(self) -> Optional[Tuple[float, float]]:
        """
        Get the target location for distance-based scoring.
        
        Returns:
            Tuple of (latitude, longitude) or None if location not relevant
        """
        pass
    
    def get_spam_filters(self) -> Dict[str, List[str]]:
        """
        Get spam/unwanted content filters.
        
        Returns:
            Dictionary with keys 'title', 'description', 'attributes' 
            and lists of strings to filter out
        """
        return {
            "title": [],
            "description": [],
            "attributes": []
        }
    
    def preprocess_listing(self, listing: Dict) -> Dict:
        """
        Preprocess a listing before scoring (e.g., extract additional fields).
        
        Args:
            listing: Raw listing dictionary
            
        Returns:
            Processed listing dictionary
        """
        return listing
    
    def get_algorithm_name(self) -> str:
        """Get a human-readable name for this algorithm."""
        return f"{self.__class__.__name__} ({self.search_type})"
    
    def format_results_to_html(self, sorted_listings: List[Dict]) -> str:
        """
        Format results as HTML for email/display.
        
        Args:
            sorted_listings: List of sorted listing dictionaries
            
        Returns:
            HTML string with formatted results
        """
        if not sorted_listings:
            return self._get_empty_results_html()
        
        table_html = self._get_table_header()
        
        for listing in sorted_listings:
            table_html += self._format_listing_row(listing)
        
        table_html += "</table>"
        
        return self._wrap_in_html_document(table_html)
    
    def format_results_to_console(self, sorted_listings: List[Dict]) -> str:
        """
        Format results as a nicely formatted console table.
        
        Args:
            sorted_listings: List of sorted listing dictionaries
            
        Returns:
            Formatted string for console display
        """
        if not sorted_listings:
            return "No results found matching the criteria.\n"
        
        # Get column definitions
        columns = self._get_console_columns()
        
        # Calculate column widths
        col_widths = {}
        for col_key, col_info in columns.items():
            # Start with header width
            col_widths[col_key] = len(col_info['header'])
            # Check all data values
            for listing in sorted_listings[:20]:  # Only check first 20 for performance
                value = self._format_console_value(listing, col_key, col_info)
                col_widths[col_key] = max(col_widths[col_key], len(str(value)))
            # Add some padding
            col_widths[col_key] += 2
        
        # Build the table
        output = []
        
        # Header
        header_parts = []
        separator_parts = []
        for col_key, col_info in columns.items():
            header_parts.append(col_info['header'].ljust(col_widths[col_key]))
            separator_parts.append('-' * col_widths[col_key])
        
        output.append('┌' + '┬'.join(separator_parts) + '┐')
        output.append('│' + '│'.join(header_parts) + '│')
        output.append('├' + '┼'.join(separator_parts) + '┤')
        
        # Data rows
        for i, listing in enumerate(sorted_listings[:15]):  # Limit to 15 for readability
            row_parts = []
            for col_key, col_info in columns.items():
                value = self._format_console_value(listing, col_key, col_info)
                if col_info.get('align') == 'right':
                    formatted_value = str(value).rjust(col_widths[col_key])
                elif col_info.get('align') == 'center':
                    formatted_value = str(value).center(col_widths[col_key])
                else:
                    formatted_value = str(value).ljust(col_widths[col_key])
                row_parts.append(formatted_value)
            output.append('│' + '│'.join(row_parts) + '│')
        
        output.append('└' + '┴'.join(separator_parts) + '┘')
        
        # Add summary
        total_count = len(sorted_listings)
        if total_count > 15:
            output.append(f"\nShowing top 15 of {total_count} results")
        else:
            output.append(f"\nTotal: {total_count} results")
        
        return '\n'.join(output)
    
    def _get_console_columns(self) -> Dict[str, Dict]:
        """
        Get column definitions for console output. Override in subclasses.
        
        Returns:
            Dict with column definitions: {
                'column_key': {
                    'header': 'Column Name',
                    'width': 20,  # optional max width
                    'align': 'left|right|center'  # optional
                }
            }
        """
        return {
            'title': {'header': 'Title', 'width': 40},
            'score': {'header': 'Score', 'align': 'center'},
            'price': {'header': 'Price', 'align': 'right'},
            'url': {'header': 'URL', 'width': 50}
        }
    
    def _format_console_value(self, listing: Dict, col_key: str, col_info: Dict) -> str:
        """Format a single value for console display."""
        if col_key == 'title':
            title = listing.get('title', 'No Title')
            max_width = col_info.get('width', 40)
            return title[:max_width-3] + '...' if len(title) > max_width else title
        
        elif col_key == 'score':
            return f"{listing.get('score', 0):.1f}"
        
        elif col_key == 'price':
            price = listing.get('price', 0)
            return f"${price:,}" if price > 0 else "N/A"
        
        elif col_key == 'url':
            url = listing.get('url', '')
            max_width = col_info.get('width', 50)
            return url[:max_width-3] + '...' if len(url) > max_width else url
        
        return str(listing.get(col_key, 'N/A'))
    
    def _get_table_header(self) -> str:
        """Get the HTML table header. Override in subclasses for custom columns."""
        return """
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f2f2f2;">
            <th>Title (Link)</th>
            <th>Description</th>
            <th>Score</th>
            <th>Price</th>
        </tr>
        """
    
    def _format_listing_row(self, listing: Dict) -> str:
        """Format a single listing as an HTML table row. Override in subclasses."""
        title = listing.get('title', 'No Title')
        url = listing.get('url', '#')
        description = listing.get('description', 'No Description')[:200] + "..."
        score = listing.get('score', 0)
        price = listing.get('price', 0)
        
        return f"""
        <tr>
            <td><strong><a href="{url}" target="_blank">{title}</a></strong></td>
            <td>{description}</td>
            <td align="center">{round(score, 1)}</td>
            <td align="right">${price:,}</td>
        </tr>
        """
    
    def _get_empty_results_html(self) -> str:
        """Get HTML for when there are no results."""
        return """
        <html>
        <body>
            <h2>No Results Found</h2>
            <p>No listings found matching the criteria.</p>
        </body>
        </html>
        """
    
    def _wrap_in_html_document(self, table_html: str) -> str:
        """Wrap the table in a complete HTML document."""
        search_name = getattr(self, 'search_type', 'Search')
        return f"""
        <html>
        <body>
            <h2>{search_name} Results</h2>
            <p>Here are the top-ranked listings:</p>
            {table_html}
        </body>
        </html>
        """


class ScoreCalculator:
    """Helper class for common scoring operations."""
    
    @staticmethod
    def calculate_distance_score(
        listing_coords: Tuple[float, float],
        target_coords: Tuple[float, float],
        max_distance: float = 50.0
    ) -> float:
        """
        Calculate distance-based score using haversine formula.
        
        Args:
            listing_coords: (latitude, longitude) of listing
            target_coords: (latitude, longitude) of target location
            max_distance: Maximum distance in miles
            
        Returns:
            Distance-based score (higher is better)
        """
        import math
        
        lat1, lon1 = map(math.radians, listing_coords)
        lat2, lon2 = map(math.radians, target_coords)
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Radius of Earth in kilometers, convert to miles
        distance_miles = c * 6371 * 0.62137273665
        
        if distance_miles > max_distance:
            return -10  # Very negative score for listings too far away
        
        # Linear score: closer is better
        return max_distance - distance_miles
    
    @staticmethod
    def calculate_price_score(
        price: float,
        target_price: float,
        price_tolerance: float = 0.2
    ) -> float:
        """
        Calculate price-based score.
        
        Args:
            price: Listing price
            target_price: Target/ideal price
            price_tolerance: Acceptable price deviation (as fraction)
            
        Returns:
            Price-based score
        """
        if price <= 0:
            return -5  # Invalid price
        
        price_diff_ratio = abs(price - target_price) / target_price
        
        if price_diff_ratio <= price_tolerance:
            return 5  # Within acceptable range
        elif price_diff_ratio <= price_tolerance * 2:
            return 2  # Somewhat acceptable
        else:
            return -3  # Too far from target
    
    @staticmethod
    def calculate_keyword_score(
        text: str,
        positive_keywords: Dict[str, float],
        negative_keywords: Dict[str, float]
    ) -> float:
        """
        Calculate score based on keyword matching.
        
        Args:
            text: Text to search for keywords
            positive_keywords: Dict of {keyword: score_boost}
            negative_keywords: Dict of {keyword: score_penalty}
            
        Returns:
            Keyword-based score
        """
        score = 0.0
        text_lower = text.lower()
        
        for keyword, boost in positive_keywords.items():
            if keyword.lower() in text_lower:
                score += boost
        
        for keyword, penalty in negative_keywords.items():
            if keyword.lower() in text_lower:
                score -= penalty
        
        return score
    
    @staticmethod
    def is_spam_listing(
        listing: Dict,
        spam_filters: Dict[str, List[str]]
    ) -> bool:
        """
        Check if a listing should be filtered out as spam.
        
        Args:
            listing: Listing dictionary
            spam_filters: Dictionary of spam patterns
            
        Returns:
            True if listing should be filtered out
        """
        # Check title
        title = listing.get('title', '').lower()
        for spam_pattern in spam_filters.get('title', []):
            if spam_pattern.lower() in title:
                return True
        
        # Check description
        description = listing.get('description', '').lower()
        for spam_pattern in spam_filters.get('description', []):
            if spam_pattern.lower() in description:
                return True
        
        # Check attributes
        attributes = listing.get('attributes', [])
        if isinstance(attributes, list):
            attributes_text = ' '.join(str(attr).lower() for attr in attributes)
            for spam_pattern in spam_filters.get('attributes', []):
                if spam_pattern.lower() in attributes_text:
                    return True
        
        return False


class RankingAlgorithmRegistry:
    """Registry for managing different ranking algorithms."""
    
    _algorithms: Dict[str, BaseRankingAlgorithm] = {}
    
    @classmethod
    def register(cls, algorithm: BaseRankingAlgorithm) -> None:
        """Register a ranking algorithm."""
        cls._algorithms[algorithm.search_type] = algorithm
    
    @classmethod
    def get_algorithm(cls, search_type: str) -> BaseRankingAlgorithm:
        """Get a ranking algorithm by search type."""
        if search_type not in cls._algorithms:
            raise ValueError(f"No ranking algorithm registered for search type: {search_type}")
        return cls._algorithms[search_type]
    
    @classmethod
    def get_available_search_types(cls) -> List[str]:
        """Get list of available search types."""
        return list(cls._algorithms.keys())
    
    @classmethod
    def list_algorithms(cls) -> Dict[str, str]:
        """Get a dictionary of search_type -> algorithm_name."""
        return {
            search_type: algorithm.get_algorithm_name()
            for search_type, algorithm in cls._algorithms.items()
        }