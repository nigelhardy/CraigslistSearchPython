"""
Apartment ranking algorithms for Santa Cruz and Los Gatos areas.

This module contains the original apartment ranking logic refactored
to use the new plugin-based ranking system.
"""

import math
from typing import Dict, List, Tuple, Optional

from ranking_system import BaseRankingAlgorithm, RankingResult, ScoreCalculator


class SantaCruzApartmentRanking(BaseRankingAlgorithm):
    """Ranking algorithm for Santa Cruz apartment searches."""
    
    def __init__(self):
        super().__init__("SC")
        self.target_location = (36.964967039128446, -122.01459377274979)  # Santa Cruz boardwalk
        self.max_price = 3300
    
    def get_target_location(self) -> Tuple[float, float]:
        return self.target_location
    
    def get_search_categories(self) -> List[str]:
        return ["apa"]  # apartments/housing
    
    def get_minimum_score_threshold(self) -> float:
        return 0.0
    
    def get_spam_filters(self) -> Dict[str, List[str]]:
        return {
            "description": [
                "🆃🅴🆇🆃 ME NUMBER!!!!",
                "TEXT YOUR CONTACT NOW",
                "TEXT ME NUMBER!!!!",
                "Luxury lobby and reception area fully attended",
                "💫Pre-installed intrusion alarm"
            ],
            "attributes": [
                "CENTURY 21 VERDESCHI AND WALSH REALTY.;".lower(),
                "CENTURY 21 VERDESCHI AND WALSH REALTY".lower(),
                "BRAZEN MANAGEMENT CORP".lower(),
                "Golden Gate Sotheby's International Realty".lower()
            ],
            "title": ["Rooms for rent"]
        }
    
    def calculate_scores(self, listings: List[Dict]) -> RankingResult:
        """Calculate scores for Santa Cruz apartment listings."""
        scored_listings = []
        unwanted_listings = []
        
        for listing in listings:
            # Preprocess the listing
            processed_listing = self.preprocess_listing(listing)
            
            # Check for spam
            if ScoreCalculator.is_spam_listing(processed_listing, self.get_spam_filters()):
                unwanted_listings.append(processed_listing)
                continue
            
            # Calculate score
            score = self._calculate_listing_score(processed_listing)
            processed_listing['score'] = score
            
            if score > self.get_minimum_score_threshold():
                scored_listings.append(processed_listing)
            else:
                unwanted_listings.append(processed_listing)
        
        # Sort by score (highest first)
        scored_listings.sort(key=lambda x: x['score'], reverse=True)
        
        return RankingResult(
            sorted_listings=scored_listings,
            unwanted_listings=unwanted_listings,
            total_processed=len(listings)
        )
    
    def preprocess_listing(self, listing: Dict) -> Dict:
        """Extract square footage and other apartment-specific data."""
        processed = listing.copy()
        processed['sqr_foot'] = -1
        
        # Extract square footage from attributes
        for attr in listing.get('attributes', []):
            attr_lower = str(attr).lower()
            if "ft2" in attr_lower:
                try:
                    sqr_foot = int(attr_lower.split("ft2")[0])
                    processed['sqr_foot'] = sqr_foot
                    break
                except (ValueError, IndexError):
                    continue
        
        # Calculate distance if coordinates available
        if 'coord' in listing and listing['coord']:
            try:
                lat, lon = map(float, listing['coord'].split(';'))
                distance = self._calculate_distance(lat, lon)
                processed['distance'] = distance
            except (ValueError, AttributeError):
                processed['distance'] = -1
        else:
            processed['distance'] = -1
        
        return processed
    
    def _calculate_listing_score(self, listing: Dict) -> float:
        """Calculate the total score for a Santa Cruz apartment listing."""
        score = 0.0
        price = listing.get('price', 0)
        
        # Price scoring
        score += self._calculate_price_score(price)
        
        # Square footage scoring
        sqr_foot = listing.get('sqr_foot', -1)
        score += self._calculate_sqr_foot_score(sqr_foot)
        
        # Distance scoring
        distance = listing.get('distance', -1)
        score += self._calculate_distance_score(distance)
        
        # Attribute scoring
        score += self._calculate_attribute_score(listing.get('attributes', []))
        
        # Description scoring
        score += self._calculate_description_score(listing.get('description', ''))
        
        return score
    
    # HTML formatting methods for Los Gatos apartments
    def _get_table_header(self) -> str:
        """Get apartment-specific table header with relevant columns."""
        return """
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f2f2f2;">
            <th>Title (Link)</th>
            <th>Description</th>
            <th>Score</th>
            <th>Price</th>
            <th>Distance</th>
            <th>Square Footage</th>
        </tr>
        """
    
    def _format_listing_row(self, listing: Dict) -> str:
        """Format apartment listing with apartment-specific fields."""
        title = listing.get('title', 'No Title')
        url = listing.get('url', '#')
        description = listing.get('description', 'No Description')[:200] + "..."
        score = listing.get('score', 0)
        price = listing.get('price', 0)
        distance = listing.get('distance', -1)
        sqr_foot = listing.get('sqr_foot', -1)
        
        # Format distance
        if distance > 0:
            distance_str = f"{round(distance, 1)} mi."
        else:
            distance_str = "N/A"
        
        # Format square footage
        if sqr_foot > 0:
            sqr_foot_str = f"{sqr_foot:,} sq ft"
        else:
            sqr_foot_str = "N/A"
        
        return f"""
        <tr>
            <td><strong><a href="{url}" target="_blank">{title}</a></strong></td>
            <td>{description}</td>
            <td align="center">{round(score, 1)}</td>
            <td align="right">${price:,}</td>
            <td align="right">{distance_str}</td>
            <td align="right">{sqr_foot_str}</td>
        </tr>
        """
    
    def _wrap_in_html_document(self, table_html: str) -> str:
        """Wrap apartment results in HTML document."""
        return f"""
        <html>
        <body>
            <h2>Los Gatos Apartment Listings</h2>
            <p>Here are the top-ranked apartment listings near Los Gatos:</p>
            {table_html}
        </body>
        </html>
        """
    
    def _calculate_price_score(self, price: float) -> float:
        """Calculate Santa Cruz specific price score."""
        if price < 2200 and price > 2000:
            return -2
        elif price <= 2000 and price > 1800:
            return -4
        elif price <= 1800:
            return -10
        
        if price > 3199:
            return -3
        elif price > 3000:
            return -1
        elif price > 2900:
            return 0
        elif price > 2700:
            return 2
        elif price > 2500:
            return 4
        
        return 0
    
    def _calculate_sqr_foot_score(self, sqr_foot: int) -> float:
        """Calculate square footage score."""
        if sqr_foot == -1:
            return 0
        
        if sqr_foot < 500 or sqr_foot > 3000:
            return -5
        
        score = (sqr_foot - 800) / 100
        return min(score, 4)
    
    def _calculate_distance_score(self, distance: float) -> float:
        """Calculate distance score from Santa Cruz boardwalk."""
        if distance == -1:
            return 0
        
        return ((8 - distance) * 0.25) - 2
    
    def _calculate_distance(self, lat: float, lon: float) -> float:
        """Calculate distance using haversine formula."""
        target_lat, target_lon = self.target_location
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [target_lat, target_lon, lat, lon])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Convert to miles
        return c * 6371 * 0.62137273665
    
    def _calculate_attribute_score(self, attributes: List) -> float:
        """Calculate score based on apartment attributes."""
        score = 0.0
        
        attribute_scores = {
            "off-street parking": 1,
            'street parking': -2,
            "attached garage": 3,
            "carport": -1,
            "3br": 4,
            "2br": 3,
            "1br": -5,
            "0br": -6,
            "furnished": -2,
            "w/d in unit": 2,
            "apartment": -1,
            "house": 2,
            'cottage/cabin': 1,
            "townhouse": 1,
            "air conditioning": 2,
            "laundry on site": 1,
            'laundry in bldg': 2,
        }
        
        for attr in attributes:
            attr_lower = str(attr).lower()
            for key, points in attribute_scores.items():
                if key in attr_lower:
                    score += points
        
        return score
    
    # HTML formatting methods for Los Gatos apartments
    def _get_table_header(self) -> str:
        """Get apartment-specific table header with relevant columns."""
        return """
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f2f2f2;">
            <th>Title (Link)</th>
            <th>Description</th>
            <th>Score</th>
            <th>Price</th>
            <th>Distance</th>
            <th>Square Footage</th>
        </tr>
        """
    
    def _format_listing_row(self, listing: Dict) -> str:
        """Format apartment listing with apartment-specific fields."""
        title = listing.get('title', 'No Title')
        url = listing.get('url', '#')
        description = listing.get('description', 'No Description')[:200] + "..."
        score = listing.get('score', 0)
        price = listing.get('price', 0)
        distance = listing.get('distance', -1)
        sqr_foot = listing.get('sqr_foot', -1)
        
        # Format distance
        if distance > 0:
            distance_str = f"{round(distance, 1)} mi."
        else:
            distance_str = "N/A"
        
        # Format square footage
        if sqr_foot > 0:
            sqr_foot_str = f"{sqr_foot:,} sq ft"
        else:
            sqr_foot_str = "N/A"
        
        return f"""
        <tr>
            <td><strong><a href="{url}" target="_blank">{title}</a></strong></td>
            <td>{description}</td>
            <td align="center">{round(score, 1)}</td>
            <td align="right">${price:,}</td>
            <td align="right">{distance_str}</td>
            <td align="right">{sqr_foot_str}</td>
        </tr>
        """
    
    def _wrap_in_html_document(self, table_html: str) -> str:
        """Wrap apartment results in HTML document."""
        return f"""
        <html>
        <body>
            <h2>Los Gatos Apartment Listings</h2>
            <p>Here are the top-ranked apartment listings near Los Gatos:</p>
            {table_html}
        </body>
        </html>
        """
    
    def _calculate_description_score(self, description: str) -> float:
        """Calculate score based on description keywords."""
        desc_lower = description.lower()
        
        description_scores = {
            "converted garage": -10,
            "no garage": -10,
            "garage space is not included": -10,
            "parking garage": -6,
            "garage": 5,
            'lots of light': 2,
            "Occupancy Limit: 1 People": -5,
            "Utilities are not included": -2,
            'All utilities are included': 2,
            'All utilities included': 2,
            'Water and Garbage Included': 1,
            'Coin-op laundry': -1,
            'street parking only': -3,
            'In-Home Washer/Dryer': 2,
            'in-unit washer/dryer': 2,
            'Dual Pane Windows': 1,
            'A/C': 1,
            'Air Conditioning': 1,
            'Air Conditioner': 1,
            'Central HVAC': 1,
            '1 car garage': 3,
            '1-car garage': 3,
            'one-car garage': 3,
            'one car garage': 3,
            'two-car garage': 5,
            'two car garage': 5,
            '2 car garage': 5,
            '2-car garage': 5,
            'One-Car Carport': -2,
            'garage space used as an extra room': -2,
            'underground parking garage': -2,
            'garage log': -2,
            'coin operated laundry': -1,
            'coin-operated laundry': -1,
            '1 person max': -5,
            '1-person max': -5
        }
        
        score = 0.0
        for keyword, points in description_scores.items():
            if keyword.lower() in desc_lower:
                score += points
        
        return score
    
    # HTML formatting methods for Los Gatos apartments
    def _get_table_header(self) -> str:
        """Get apartment-specific table header with relevant columns."""
        return """
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f2f2f2;">
            <th>Title (Link)</th>
            <th>Description</th>
            <th>Score</th>
            <th>Price</th>
            <th>Distance</th>
            <th>Square Footage</th>
        </tr>
        """
    
    def _format_listing_row(self, listing: Dict) -> str:
        """Format apartment listing with apartment-specific fields."""
        title = listing.get('title', 'No Title')
        url = listing.get('url', '#')
        description = listing.get('description', 'No Description')[:200] + "..."
        score = listing.get('score', 0)
        price = listing.get('price', 0)
        distance = listing.get('distance', -1)
        sqr_foot = listing.get('sqr_foot', -1)
        
        # Format distance
        if distance > 0:
            distance_str = f"{round(distance, 1)} mi."
        else:
            distance_str = "N/A"
        
        # Format square footage
        if sqr_foot > 0:
            sqr_foot_str = f"{sqr_foot:,} sq ft"
        else:
            sqr_foot_str = "N/A"
        
        return f"""
        <tr>
            <td><strong><a href="{url}" target="_blank">{title}</a></strong></td>
            <td>{description}</td>
            <td align="center">{round(score, 1)}</td>
            <td align="right">${price:,}</td>
            <td align="right">{distance_str}</td>
            <td align="right">{sqr_foot_str}</td>
        </tr>
        """
    
    def _wrap_in_html_document(self, table_html: str) -> str:
        """Wrap apartment results in HTML document."""
        return f"""
        <html>
        <body>
            <h2>Los Gatos Apartment Listings</h2>
            <p>Here are the top-ranked apartment listings near Los Gatos:</p>
            {table_html}
        </body>
        </html>
        """
    
    def _get_table_header(self) -> str:
        """Get apartment-specific table header with relevant columns."""
        return """
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f2f2f2;">
            <th>Title (Link)</th>
            <th>Description</th>
            <th>Score</th>
            <th>Price</th>
            <th>Distance</th>
            <th>Square Footage</th>
        </tr>
        """
    
    def _format_listing_row(self, listing: Dict) -> str:
        """Format apartment listing with apartment-specific fields."""
        title = listing.get('title', 'No Title')
        url = listing.get('url', '#')
        description = listing.get('description', 'No Description')[:200] + "..."
        score = listing.get('score', 0)
        price = listing.get('price', 0)
        distance = listing.get('distance', -1)
        sqr_foot = listing.get('sqr_foot', -1)
        
        # Format distance
        if distance > 0:
            distance_str = f"{round(distance, 1)} mi."
        else:
            distance_str = "N/A"
        
        # Format square footage
        if sqr_foot > 0:
            sqr_foot_str = f"{sqr_foot:,} sq ft"
        else:
            sqr_foot_str = "N/A"
        
        return f"""
        <tr>
            <td><strong><a href="{url}" target="_blank">{title}</a></strong></td>
            <td>{description}</td>
            <td align="center">{round(score, 1)}</td>
            <td align="right">${price:,}</td>
            <td align="right">{distance_str}</td>
            <td align="right">{sqr_foot_str}</td>
        </tr>
        """
    
    def _wrap_in_html_document(self, table_html: str) -> str:
        """Wrap apartment results in HTML document."""
        return f"""
        <html>
        <body>
            <h2>Santa Cruz Apartment Listings</h2>
            <p>Here are the top-ranked apartment listings near Santa Cruz:</p>
            {table_html}
        </body>
        </html>
        """


class LosGatosApartmentRanking(BaseRankingAlgorithm):
    """Ranking algorithm for Los Gatos apartment searches."""
    
    def __init__(self):
        super().__init__("LG")
        self.target_location = (37.2609611, -121.9611325)  # SA Photonics work location
        self.max_price = 4000
    
    def get_target_location(self) -> Tuple[float, float]:
        return self.target_location
    
    def get_search_categories(self) -> List[str]:
        return ["apa"]  # apartments/housing
    
    def get_minimum_score_threshold(self) -> float:
        return 0.0
    
    def get_spam_filters(self) -> Dict[str, List[str]]:
        return {
            "description": [
                "🆃🅴🆇🆃 ME NUMBER!!!!",
                "TEXT YOUR CONTACT NOW",
                "TEXT ME NUMBER!!!!",
                "Luxury lobby and reception area fully attended",
                "💫Pre-installed intrusion alarm"
            ],
            "attributes": [
                "CENTURY 21 VERDESCHI AND WALSH REALTY.;".lower(),
                "CENTURY 21 VERDESCHI AND WALSH REALTY".lower(),
                "BRAZEN MANAGEMENT CORP".lower(),
            ],
            "title": ["Rooms for rent"]
        }
    
    def calculate_scores(self, listings: List[Dict]) -> RankingResult:
        """Calculate scores for Los Gatos apartment listings."""
        scored_listings = []
        unwanted_listings = []
        
        for listing in listings:
            # Preprocess the listing
            processed_listing = self.preprocess_listing(listing)
            
            # Check for spam
            if ScoreCalculator.is_spam_listing(processed_listing, self.get_spam_filters()):
                unwanted_listings.append(processed_listing)
                continue
            
            # Calculate score
            score = self._calculate_listing_score(processed_listing)
            processed_listing['score'] = score
            
            if score > self.get_minimum_score_threshold():
                scored_listings.append(processed_listing)
            else:
                unwanted_listings.append(processed_listing)
        
        # Sort by score (highest first)
        scored_listings.sort(key=lambda x: x['score'], reverse=True)
        
        return RankingResult(
            sorted_listings=scored_listings,
            unwanted_listings=unwanted_listings,
            total_processed=len(listings)
        )
    
    def preprocess_listing(self, listing: Dict) -> Dict:
        """Extract square footage and other apartment-specific data."""
        processed = listing.copy()
        processed['sqr_foot'] = -1
        
        # Extract square footage from attributes
        for attr in listing.get('attributes', []):
            attr_lower = str(attr).lower()
            if "ft2" in attr_lower:
                try:
                    sqr_foot = int(attr_lower.split("ft2")[0])
                    processed['sqr_foot'] = sqr_foot
                    break
                except (ValueError, IndexError):
                    continue
        
        # Calculate distance if coordinates available
        if 'coord' in listing and listing['coord']:
            try:
                lat, lon = map(float, listing['coord'].split(';'))
                distance = self._calculate_distance(lat, lon)
                processed['distance'] = distance
            except (ValueError, AttributeError):
                processed['distance'] = -1
        else:
            processed['distance'] = -1
        
        return processed
    
    def _calculate_listing_score(self, listing: Dict) -> float:
        """Calculate the total score for a Los Gatos apartment listing."""
        score = 0.0
        price = listing.get('price', 0)
        
        # Price scoring
        score += self._calculate_price_score(price)
        
        # Square footage scoring
        sqr_foot = listing.get('sqr_foot', -1)
        score += self._calculate_sqr_foot_score(sqr_foot)
        
        # Distance scoring
        distance = listing.get('distance', -1)
        score += self._calculate_distance_score(distance)
        
        # Attribute scoring
        score += self._calculate_attribute_score(listing.get('attributes', []))
        
        # Description scoring
        score += self._calculate_description_score(listing.get('description', ''))
        
        return score
    
    # HTML formatting methods for Los Gatos apartments
    def _get_table_header(self) -> str:
        """Get apartment-specific table header with relevant columns."""
        return """
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f2f2f2;">
            <th>Title (Link)</th>
            <th>Description</th>
            <th>Score</th>
            <th>Price</th>
            <th>Distance</th>
            <th>Square Footage</th>
        </tr>
        """
    
    def _format_listing_row(self, listing: Dict) -> str:
        """Format apartment listing with apartment-specific fields."""
        title = listing.get('title', 'No Title')
        url = listing.get('url', '#')
        description = listing.get('description', 'No Description')[:200] + "..."
        score = listing.get('score', 0)
        price = listing.get('price', 0)
        distance = listing.get('distance', -1)
        sqr_foot = listing.get('sqr_foot', -1)
        
        # Format distance
        if distance > 0:
            distance_str = f"{round(distance, 1)} mi."
        else:
            distance_str = "N/A"
        
        # Format square footage
        if sqr_foot > 0:
            sqr_foot_str = f"{sqr_foot:,} sq ft"
        else:
            sqr_foot_str = "N/A"
        
        return f"""
        <tr>
            <td><strong><a href="{url}" target="_blank">{title}</a></strong></td>
            <td>{description}</td>
            <td align="center">{round(score, 1)}</td>
            <td align="right">${price:,}</td>
            <td align="right">{distance_str}</td>
            <td align="right">{sqr_foot_str}</td>
        </tr>
        """
    
    def _wrap_in_html_document(self, table_html: str) -> str:
        """Wrap apartment results in HTML document."""
        return f"""
        <html>
        <body>
            <h2>Los Gatos Apartment Listings</h2>
            <p>Here are the top-ranked apartment listings near Los Gatos:</p>
            {table_html}
        </body>
        </html>
        """
    
    def _calculate_price_score(self, price: float) -> float:
        """Calculate Los Gatos specific price score."""
        if price < 2000:
            return -2
        
        return (3200 - price) / 200
    
    def _calculate_sqr_foot_score(self, sqr_foot: int) -> float:
        """Calculate square footage score."""
        if sqr_foot == -1:
            return 0
        
        if sqr_foot < 500 or sqr_foot > 3000:
            return -5
        
        score = (sqr_foot - 800) / 100
        return min(score, 4)
    
    def _calculate_distance_score(self, distance: float) -> float:
        """Calculate distance score from work location."""
        if distance == -1:
            return 0
        
        return ((4 - distance) * 0.25) - 1
    
    def _calculate_distance(self, lat: float, lon: float) -> float:
        """Calculate distance using haversine formula."""
        target_lat, target_lon = self.target_location
        
        # Convert to radians
        lat1, lon1, lat2, lon2 = map(math.radians, [target_lat, target_lon, lat, lon])
        
        # Haversine formula
        dlon = lon2 - lon1
        dlat = lat2 - lat1
        a = math.sin(dlat/2)**2 + math.cos(lat1) * math.cos(lat2) * math.sin(dlon/2)**2
        c = 2 * math.asin(math.sqrt(a))
        
        # Convert to miles
        return c * 6371 * 0.62137273665
    
    def _calculate_attribute_score(self, attributes: List) -> float:
        """Calculate score based on apartment attributes."""
        score = 0.0
        
        attribute_scores = {
            "off-street parking": 1,
            'street parking': -2,
            "attached garage": 3,
            "carport": -1,
            "3br": 10,  # Higher preference for 3br in LG
            "2br": -4,
            "1br": -8,
            "0br": -12,
            "furnished": -2,
            "w/d in unit": 2,
            "apartment": -1,
            "house": 2,
            'cottage/cabin': 1,
            "townhouse": 1,
            "air conditioning": 2,
            "laundry on site": 1,
            'laundry in bldg': 2,
        }
        
        for attr in attributes:
            attr_lower = str(attr).lower()
            for key, points in attribute_scores.items():
                if key in attr_lower:
                    score += points
        
        return score
    
    # HTML formatting methods for Los Gatos apartments
    def _get_table_header(self) -> str:
        """Get apartment-specific table header with relevant columns."""
        return """
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f2f2f2;">
            <th>Title (Link)</th>
            <th>Description</th>
            <th>Score</th>
            <th>Price</th>
            <th>Distance</th>
            <th>Square Footage</th>
        </tr>
        """
    
    def _format_listing_row(self, listing: Dict) -> str:
        """Format apartment listing with apartment-specific fields."""
        title = listing.get('title', 'No Title')
        url = listing.get('url', '#')
        description = listing.get('description', 'No Description')[:200] + "..."
        score = listing.get('score', 0)
        price = listing.get('price', 0)
        distance = listing.get('distance', -1)
        sqr_foot = listing.get('sqr_foot', -1)
        
        # Format distance
        if distance > 0:
            distance_str = f"{round(distance, 1)} mi."
        else:
            distance_str = "N/A"
        
        # Format square footage
        if sqr_foot > 0:
            sqr_foot_str = f"{sqr_foot:,} sq ft"
        else:
            sqr_foot_str = "N/A"
        
        return f"""
        <tr>
            <td><strong><a href="{url}" target="_blank">{title}</a></strong></td>
            <td>{description}</td>
            <td align="center">{round(score, 1)}</td>
            <td align="right">${price:,}</td>
            <td align="right">{distance_str}</td>
            <td align="right">{sqr_foot_str}</td>
        </tr>
        """
    
    def _wrap_in_html_document(self, table_html: str) -> str:
        """Wrap apartment results in HTML document."""
        return f"""
        <html>
        <body>
            <h2>Los Gatos Apartment Listings</h2>
            <p>Here are the top-ranked apartment listings near Los Gatos:</p>
            {table_html}
        </body>
        </html>
        """
    
    def _calculate_description_score(self, description: str) -> float:
        """Calculate score based on description keywords."""
        # Same scoring as Santa Cruz for now
        desc_lower = description.lower()
        
        description_scores = {
            "converted garage": -10,
            "no garage": -10,
            "garage space is not included": -10,
            "parking garage": -6,
            "garage": 5,
            'lots of light': 2,
            "Occupancy Limit: 1 People": -5,
            "Utilities are not included": -2,
            'All utilities are included': 2,
            'All utilities included': 2,
            'Water and Garbage Included': 1,
            'Coin-op laundry': -1,
            'street parking only': -3,
            'In-Home Washer/Dryer': 2,
            'in-unit washer/dryer': 2,
            'Dual Pane Windows': 1,
            'A/C': 1,
            'Air Conditioning': 1,
            'Air Conditioner': 1,
            'Central HVAC': 1,
            '1 car garage': 3,
            '1-car garage': 3,
            'one-car garage': 3,
            'one car garage': 3,
            'two-car garage': 5,
            'two car garage': 5,
            '2 car garage': 5,
            '2-car garage': 5,
            'One-Car Carport': -2,
            'garage space used as an extra room': -2,
            'underground parking garage': -2,
            'garage log': -2,
            'coin operated laundry': -1,
            'coin-operated laundry': -1,
            '1 person max': -5,
            '1-person max': -5
        }
        
        score = 0.0
        for keyword, points in description_scores.items():
            if keyword.lower() in desc_lower:
                score += points
        
        return score
    
    # HTML formatting methods for Los Gatos apartments
    def _get_table_header(self) -> str:
        """Get apartment-specific table header with relevant columns."""
        return """
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f2f2f2;">
            <th>Title (Link)</th>
            <th>Description</th>
            <th>Score</th>
            <th>Price</th>
            <th>Distance</th>
            <th>Square Footage</th>
        </tr>
        """
    
    def _format_listing_row(self, listing: Dict) -> str:
        """Format apartment listing with apartment-specific fields."""
        title = listing.get('title', 'No Title')
        url = listing.get('url', '#')
        description = listing.get('description', 'No Description')[:200] + "..."
        score = listing.get('score', 0)
        price = listing.get('price', 0)
        distance = listing.get('distance', -1)
        sqr_foot = listing.get('sqr_foot', -1)
        
        # Format distance
        if distance > 0:
            distance_str = f"{round(distance, 1)} mi."
        else:
            distance_str = "N/A"
        
        # Format square footage
        if sqr_foot > 0:
            sqr_foot_str = f"{sqr_foot:,} sq ft"
        else:
            sqr_foot_str = "N/A"
        
        return f"""
        <tr>
            <td><strong><a href="{url}" target="_blank">{title}</a></strong></td>
            <td>{description}</td>
            <td align="center">{round(score, 1)}</td>
            <td align="right">${price:,}</td>
            <td align="right">{distance_str}</td>
            <td align="right">{sqr_foot_str}</td>
        </tr>
        """
    
    def _wrap_in_html_document(self, table_html: str) -> str:
        """Wrap apartment results in HTML document."""
        return f"""
        <html>
        <body>
            <h2>Los Gatos Apartment Listings</h2>
            <p>Here are the top-ranked apartment listings near Los Gatos:</p>
            {table_html}
        </body>
        </html>
        """