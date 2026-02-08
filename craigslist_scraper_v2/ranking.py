"""Ranking module for scoring listings."""
from typing import List
from datetime import datetime

from models import Listing, VehicleListing, ListingState
from config import ScoringRule


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
        text_parts = []
        if listing.title:
            text_parts.append(listing.title)
        if listing.description:
            text_parts.append(listing.description)
        
        if isinstance(listing, VehicleListing):
            if listing.transmission:
                text_parts.append(listing.transmission)
            if listing.title_status:
                text_parts.append(listing.title_status)
            if listing.condition:
                text_parts.append(listing.condition)
        
        searchable_text = ' '.join(text_parts).lower()
        
        score = 0.0
        breakdown = {}
        reasons = []
        
        for rule in self.scoring_rules:
            for keyword in rule.keywords:
                if keyword.lower() in searchable_text:
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
