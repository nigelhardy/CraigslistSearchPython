"""
BMW E39 parts ranking algorithm.

This module provides ranking for BMW 540i E39 chassis parts searches
as an example of extending the tool for non-apartment searches.
"""

from typing import Dict, List, Tuple, Optional

from ranking_system import BaseRankingAlgorithm, RankingResult, ScoreCalculator


class BMWE39PartsRanking(BaseRankingAlgorithm):
    """Ranking algorithm for BMW E39 (540i) parts searches."""
    
    def __init__(self):
        super().__init__("E39_PARTS")
        # You could set a target location if you want distance-based scoring
        self.target_location = None
    
    def get_target_location(self) -> Optional[Tuple[float, float]]:
        return self.target_location
    
    def get_search_categories(self) -> List[str]:
        return ["pts", "wto"]  # auto parts and wheels/tires
    
    def get_minimum_score_threshold(self) -> float:
        return 0.0
    
    def get_spam_filters(self) -> Dict[str, List[str]]:
        return {
            "title": [
                "PARTING OUT",  # Usually overpriced or junk
                "CASH FOR CARS",
                "WE BUY CARS",
                "SCRAP",
                "SALVAGE TITLE"
            ],
            "description": [
                "As-is condition",
                "Sold as scrap",
                "For parts only - not working",
                "Does not work",
                "Broken beyond repair"
            ],
            "attributes": []
        }
    
    def calculate_scores(self, listings: List[Dict]) -> RankingResult:
        """Calculate scores for BMW E39 parts listings."""
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
        """Extract E39-specific information from the listing."""
        processed = listing.copy()
        
        # Extract year if mentioned
        processed['year'] = self._extract_year(listing)
        processed['is_oem'] = self._check_if_oem(listing)
        processed['condition_score'] = self._assess_condition(listing)
        
        return processed
    
    def _calculate_listing_score(self, listing: Dict) -> float:
        """Calculate the total score for a BMW E39 parts listing."""
        score = 0.0
        
        # E39 relevance scoring
        score += self._calculate_e39_relevance_score(listing)
        
        # 540i specific parts bonus
        score += self._calculate_540i_specific_score(listing)
        
        # Price scoring
        score += self._calculate_price_score(listing)
        
        # Condition scoring
        score += self._calculate_condition_score(listing)
        
        # OEM vs aftermarket scoring
        score += self._calculate_oem_score(listing)
        
        # High-value parts scoring
        score += self._calculate_high_value_parts_score(listing)
        
        return score
    
    def _calculate_e39_relevance_score(self, listing: Dict) -> float:
        """Score based on E39 chassis relevance."""
        title = listing.get('title', '').lower()
        description = listing.get('description', '').lower()
        combined_text = f"{title} {description}"
        
        e39_keywords = {
            'e39': 10,     # Direct chassis match
            '540i': 8,     # Specific model
            '528i': 6,     # Compatible model
            '525i': 6,     # Compatible model
            '530i': 6,     # Compatible model
            'bmw': 3,      # Brand match
            '1997': 4,     # E39 years
            '1998': 4,
            '1999': 4,
            '2000': 4,
            '2001': 4,
            '2002': 4,
            '2003': 4,
            '5-series': 5,
            '5 series': 5
        }
        
        score = 0.0
        for keyword, points in e39_keywords.items():
            if keyword in combined_text:
                score += points
        
        # Negative scoring for incompatible models
        incompatible_keywords = {
            'e60': -5,     # Different generation
            'e34': -3,     # Previous generation (some parts compatible)
            'f10': -5,     # Newer generation
            'x5': -2,      # Different model line
            '3-series': -3,
            '7-series': -2
        }
        
        for keyword, penalty in incompatible_keywords.items():
            if keyword in combined_text:
                score += penalty
        
        return score
    
    def _calculate_540i_specific_score(self, listing: Dict) -> float:
        """Score for 540i-specific parts."""
        title = listing.get('title', '').lower()
        description = listing.get('description', '').lower()
        combined_text = f"{title} {description}"
        
        # Parts specific to 540i or M62 engine
        specific_parts = {
            'm62': 5,          # Engine code
            'v8': 4,           # Engine type
            '4.4l': 4,         # Engine displacement
            '540': 3,          # Model number
            'disa': 8,         # DISA valve (common failure)
            'vanos': 6,        # VANOS system
            'timing chain': 7,  # Common maintenance item
            'valley pan': 8,   # Common leak point
            'throttle body': 5,
            'maf sensor': 4,
            'oxygen sensor': 3
        }
        
        score = 0.0
        for part, points in specific_parts.items():
            if part in combined_text:
                score += points
        
        return score
    
    def _calculate_price_score(self, listing: Dict) -> float:
        """Score based on price reasonableness."""
        price = listing.get('price', 0)
        
        if price <= 0:
            return -2  # No price listed is suspicious
        
        # Different scoring ranges for different price brackets
        if price < 25:
            return 1   # Cheap parts, likely small items
        elif price <= 100:
            return 3   # Good price range for many parts
        elif price <= 300:
            return 2   # Reasonable for larger parts
        elif price <= 1000:
            return 0   # Expensive but could be worth it
        else:
            return -3  # Very expensive, needs to be very good
    
    def _calculate_condition_score(self, listing: Dict) -> float:
        """Score based on described condition."""
        condition_score = listing.get('condition_score', 0)
        return condition_score
    
    def _calculate_oem_score(self, listing: Dict) -> float:
        """Score for OEM vs aftermarket parts."""
        is_oem = listing.get('is_oem', False)
        
        title = listing.get('title', '').lower()
        description = listing.get('description', '').lower()
        combined_text = f"{title} {description}"
        
        if is_oem:
            return 3
        
        # Check for quality aftermarket brands
        good_brands = {
            'bosch': 2,
            'continental': 2,
            'febi': 2,
            'lemforder': 2,
            'sachs': 2,
            'bilstein': 3,
            'eibach': 2,
            'h&r': 2
        }
        
        for brand, points in good_brands.items():
            if brand in combined_text:
                return points
        
        # Penalty for known poor quality brands
        poor_brands = ['dorman', 'duralast', 'autozone']
        for brand in poor_brands:
            if brand in combined_text:
                return -2
        
        return 0  # Unknown brand, neutral
    
    def _calculate_high_value_parts_score(self, listing: Dict) -> float:
        """Score for parts that are particularly valuable or hard to find."""
        title = listing.get('title', '').lower()
        description = listing.get('description', '').lower()
        combined_text = f"{title} {description}"
        
        high_value_parts = {
            'angel eyes': 8,       # Popular modification
            'xenon': 6,            # HID headlights
            'navigation': 7,       # Navigation system
            'dsp amplifier': 8,    # Premium audio
            'sport seats': 6,      # Desirable interior
            'style 65': 7,         # Popular wheels
            'style 37': 5,         # OEM wheels
            'zhp': 10,            # Performance package parts
            'dinan': 8,            # Performance tuning brand
            'ac schnitzer': 8,     # Performance brand
            'alpina': 10,         # Rare performance parts
            'm-tech': 6,          # M-technic parts
            'm5': 8,              # M5 parts (some compatible)
            'manual transmission': 9,  # Rare in 540i
            'getrag': 7,          # Manual transmission
            'limited slip': 8,     # LSD differential
            '3.91': 6,            # Performance diff ratio
            'coilovers': 5,       # Suspension upgrade
            'sway bar': 4,        # Handling upgrade
            'strut tower brace': 4,
            'cold air intake': 3,
            'exhaust': 4,
            'headers': 5
        }
        
        score = 0.0
        for part, points in high_value_parts.items():
            if part in combined_text:
                score += points
        
        return score
    
    def _extract_year(self, listing: Dict) -> Optional[int]:
        """Extract year from listing if available."""
        title = listing.get('title', '')
        description = listing.get('description', '')
        combined_text = f"{title} {description}"
        
        # Look for 4-digit years in E39 range
        import re
        year_matches = re.findall(r'\b(199[7-9]|200[0-3])\b', combined_text)
        
        if year_matches:
            return int(year_matches[0])
        
        return None
    
    def _check_if_oem(self, listing: Dict) -> bool:
        """Check if the part is described as OEM."""
        title = listing.get('title', '').lower()
        description = listing.get('description', '').lower()
        combined_text = f"{title} {description}"
        
        oem_indicators = ['oem', 'genuine', 'factory', 'original', 'bmw']
        
        for indicator in oem_indicators:
            if indicator in combined_text:
                return True
        
        return False
    
    def _assess_condition(self, listing: Dict) -> float:
        """Assess the condition of the part based on description."""
        title = listing.get('title', '').lower()
        description = listing.get('description', '').lower()
        combined_text = f"{title} {description}"
        
        # Positive condition indicators
        good_condition = {
            'new': 5,
            'excellent': 4,
            'great': 3,
            'good': 2,
            'working': 2,
            'tested': 2,
            'warranty': 3,
            'low miles': 3,
            'barely used': 3
        }
        
        # Negative condition indicators
        poor_condition = {
            'worn': -2,
            'cracked': -3,
            'damaged': -4,
            'broken': -5,
            'needs repair': -3,
            'as-is': -2,
            'unknown condition': -1,
            'untested': -1,
            'high miles': -1
        }
        
        score = 0.0
        
        for indicator, points in good_condition.items():
            if indicator in combined_text:
                score += points
        
        for indicator, penalty in poor_condition.items():
            if indicator in combined_text:
                score += penalty
        
        return score
    
    # HTML formatting methods for BMW E39 parts
    def _get_table_header(self) -> str:
        """Get parts-specific table header with relevant columns."""
        return """
        <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f2f2f2;">
            <th>Title (Link)</th>
            <th>Description</th>
            <th>Score</th>
            <th>Price</th>
            <th>Year</th>
            <th>Condition</th>
            <th>OEM</th>
        </tr>
        """
    
    def _format_listing_row(self, listing: Dict) -> str:
        """Format BMW E39 parts listing with parts-specific fields."""
        title = listing.get('title', 'No Title')
        url = listing.get('url', '#')
        description = listing.get('description', 'No Description')[:150] + "..."
        score = listing.get('score', 0)
        price = listing.get('price', 0)
        year = listing.get('year')
        is_oem = listing.get('is_oem', False)
        condition_score = listing.get('condition_score', 0)
        
        # Format year
        year_str = str(year) if year else "N/A"
        
        # Format OEM status
        oem_str = "Yes" if is_oem else "Unknown"
        
        # Format condition based on score
        if condition_score >= 3:
            condition_str = "Excellent"
        elif condition_score >= 1:
            condition_str = "Good"
        elif condition_score == 0:
            condition_str = "Unknown"
        else:
            condition_str = "Poor"
        
        return f"""
        <tr>
            <td><strong><a href="{url}" target="_blank">{title}</a></strong></td>
            <td>{description}</td>
            <td align="center">{round(score, 1)}</td>
            <td align="right">${price:,}</td>
            <td align="center">{year_str}</td>
            <td align="center">{condition_str}</td>
            <td align="center">{oem_str}</td>
        </tr>
        """
    
    def _wrap_in_html_document(self, table_html: str) -> str:
        """Wrap BMW E39 parts results in HTML document."""
        return f"""
        <html>
        <body>
            <h2>BMW E39 Parts Listings</h2>
            <p>Here are the top-ranked BMW E39 540i parts listings:</p>
            {table_html}
            <p><small>Scoring considers E39 relevance, part condition, OEM status, and compatibility with 540i M62 engine.</small></p>
        </body>
        </html>
        """
    
    def _get_console_columns(self) -> Dict[str, Dict]:
        """Get BMW E39 parts-specific console columns."""
        return {
            'title': {'header': 'Title', 'width': 30},
            'score': {'header': 'Score', 'align': 'center'},
            'price': {'header': 'Price', 'align': 'right'},
            'year': {'header': 'Year', 'align': 'center'},
            'condition': {'header': 'Condition', 'align': 'center'},
            'oem': {'header': 'OEM', 'align': 'center'},
            'url': {'header': 'URL', 'width': 35}
        }
    
    def _format_console_value(self, listing: Dict, col_key: str, col_info: Dict) -> str:
        """Format BMW E39 parts-specific console values."""
        if col_key == 'year':
            year = listing.get('year')
            return str(year) if year else "N/A"
        
        elif col_key == 'condition':
            condition_score = listing.get('condition_score', 0)
            if condition_score >= 3:
                return "Excellent"
            elif condition_score >= 1:
                return "Good"
            elif condition_score == 0:
                return "Unknown"
            else:
                return "Poor"
        
        elif col_key == 'oem':
            is_oem = listing.get('is_oem', False)
            return "Yes" if is_oem else "Unknown"
        
        # Use parent class for common fields
        return super()._format_console_value(listing, col_key, col_info)