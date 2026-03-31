"""Ranking module for scoring listings."""
import re
from typing import List, Set, Tuple, Optional
from datetime import datetime, timedelta
from difflib import SequenceMatcher

from models import Listing, VehicleListing, ListingState
from config import ScoringRule


def levenshtein_distance(s1: str, s2: str) -> int:
    """Calculate Levenshtein distance between two strings."""
    if len(s1) < len(s2):
        return levenshtein_distance(s2, s1)
    
    if len(s2) == 0:
        return len(s1)
    
    previous_row = range(len(s2) + 1)
    for i, c1 in enumerate(s1):
        current_row = [i + 1]
        for j, c2 in enumerate(s2):
            insertions = previous_row[j + 1] + 1
            deletions = current_row[j] + 1
            substitutions = previous_row[j] + (c1 != c2)
            current_row.append(min(insertions, deletions, substitutions))
        previous_row = current_row
    
    return previous_row[-1]


def similarity_ratio(s1: str, s2: str) -> float:
    """Calculate similarity ratio between two strings (0.0 to 1.0)."""
    return SequenceMatcher(None, s1.lower(), s2.lower()).ratio()


def is_similar(title1: str, title2: str, threshold: float = 0.85) -> bool:
    """Check if two titles are similar based on threshold."""
    if not title1 or not title2:
        return False
    return similarity_ratio(title1, title2) >= threshold


class DuplicateFilter:
    """Filters out duplicate/similar listings."""
    
    def __init__(self, similarity_threshold: float = 0.85, min_title_length: int = 30):
        self.similarity_threshold = similarity_threshold
        self.min_title_length = min_title_length
    
    def get_significant_words(self, title: str) -> Set[str]:
        """Extract significant words from title (filter common short words)."""
        stop_words = {'a', 'an', 'the', 'and', 'or', 'but', 'in', 'on', 'at', 'to', 'for', 
                      'of', 'with', 'by', 'from', 'is', 'are', 'was', 'were', 'be', 'been',
                      'this', 'that', 'it', 'its', 'for', 'sale', 'free', 'new', 'used', ' Craigslist'}
        words = re.findall(r'\b\w+\b', title.lower())
        return {w for w in words if len(w) > 2 and w not in stop_words}
    
    def filter_duplicates(self, listings: List[Listing], 
                          existing_titles: Optional[List[str]] = None) -> Tuple[List[Listing], List[str]]:
        """Filter out duplicate listings.
        
        Returns:
            Tuple of (filtered_listings, all_titles_for_comparison)
        """
        if existing_titles is None:
            existing_titles = []
        
        filtered = []
        all_titles = list(existing_titles)
        
        for listing in listings:
            # Skip short titles (not enough to compare reliably)
            if len(listing.title) < self.min_title_length:
                filtered.append(listing)
                all_titles.append(listing.title)
                continue
            
            # Check against all existing titles
            is_duplicate = False
            for existing_title in all_titles:
                if len(existing_title) >= self.min_title_length:
                    if is_similar(listing.title, existing_title, self.similarity_threshold):
                        is_duplicate = True
                        break
            
            if not is_duplicate:
                filtered.append(listing)
            
            all_titles.append(listing.title)
        
        return filtered, all_titles
    
    def filter_age_decay(self, listings: List[Listing], max_age_days: Optional[int] = None) -> List[Listing]:
        """Filter listings based on age, applying decay to old listings.
        
        Listings older than max_age_days are removed entirely.
        """
        if max_age_days is None:
            return listings
        
        now = datetime.now()
        filtered = []
        
        for listing in listings:
            if listing.posted_date:
                try:
                    posted = datetime.fromisoformat(listing.posted_date)
                    age = (now - posted).days
                    if age > max_age_days:
                        continue
                except (ValueError, TypeError):
                    pass
            filtered.append(listing)
        
        return filtered


class ListingRanker:
    """Ranks listings based on configuration rules."""
    
    def __init__(self, scoring_rules: List[ScoringRule]):
        self.scoring_rules = scoring_rules
    
    def rank(self, listings: List[Listing]) -> List[Listing]:
        """Rank listings by calculating scores. Modifies listings in place."""
        for listing in listings:
            try:
                self._calculate_score(listing)
            except Exception as e:
                print(f"⚠️  Error ranking listing {listing.url}: {e}")
                listing.score = 0.0
                listing.score_reasons = ["Error during ranking"]
        
        return sorted(listings, key=lambda x: x.score, reverse=True)
    
    def _calculate_score(self, listing: Listing) -> None:
        """Calculate score for a single listing safely."""
        title_text = listing.title.lower() if listing.title else ""
        desc_text = listing.description.lower() if listing.description else ""
        
        combined_text_parts = [title_text, desc_text]
        
        if isinstance(listing, VehicleListing):
            if listing.transmission:
                combined_text_parts.append(listing.transmission.lower())
            if listing.title_status:
                combined_text_parts.append(listing.title_status.lower())
            if listing.condition:
                combined_text_parts.append(listing.condition.lower())
        
        combined_text = ' '.join(combined_text_parts)
        
        score = 0.0
        breakdown = {}
        reasons = []
        
        for rule in self.scoring_rules:
            match_location = getattr(rule, 'match', 'both')
            match_type = getattr(rule, 'match_type', 'partial')
            requires = getattr(rule, 'requires', [])
            excludes = getattr(rule, 'excludes', [])
            
            if match_location == "title":
                search_text = title_text
            elif match_location == "description":
                search_text = desc_text
            else:
                search_text = combined_text
            
            # Check excludes - if any excluded keyword found, skip this rule
            if excludes:
                exclude_found = False
                for excl in excludes:
                    if match_type == "whole":
                        pattern = r'\b' + re.escape(excl.lower()) + r'\b'
                        if re.search(pattern, search_text):
                            exclude_found = True
                            break
                    else:
                        if excl.lower() in search_text:
                            exclude_found = True
                            break
                if exclude_found:
                    continue
            
            # Check requires - all required keywords must be present
            if requires:
                requires_found = True
                for req in requires:
                    if match_type == "whole":
                        pattern = r'\b' + re.escape(req.lower()) + r'\b'
                        if not re.search(pattern, search_text):
                            requires_found = False
                            break
                    else:
                        if req.lower() not in search_text:
                            requires_found = False
                            break
                if not requires_found:
                    continue
            
            # Check main keywords
            for keyword in rule.keywords:
                keyword_lower = keyword.lower()
                matched = False
                
                if match_type == "whole":
                    pattern = r'\b' + re.escape(keyword_lower) + r'\b'
                    matched = bool(re.search(pattern, search_text))
                else:
                    matched = keyword_lower in search_text
                
                if matched:
                    score += rule.points
                    breakdown[keyword] = rule.points
                    
                    if rule.points >= 0:
                        reasons.append(f"'{keyword}' (+{rule.points})")
                    else:
                        reasons.append(f"'{keyword}' ({rule.points})")
                    break
        
        listing.score = score
        listing.score_breakdown = breakdown
        listing.score_reasons = reasons
        listing.state = ListingState.RANKED
        listing.last_updated = datetime.now().isoformat()


def rank_listings(listings: List[Listing], scoring_rules: List[ScoringRule]) -> List[Listing]:
    """Rank each listing based on scoring rules."""
    ranker = ListingRanker(scoring_rules)
    return ranker.rank(listings)
