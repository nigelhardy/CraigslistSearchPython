import re
from typing import List, Dict, Any
from dataclasses import dataclass

from scrapers.craigslist_scraper import CraigslistListing


@dataclass
class ScoreResult:
    total_score: float
    breakdown: Dict[str, float]
    reasons: List[str]


class SimpleScorer:
    """Simple scoring algorithm for Subaru Forester listings."""
    
    def __init__(self, config: Dict[str, Any]):
        self.scoring_config = config.get('scoring', {}).get('subaru_forester', {})
    
    def score_listings(self, listings: List[CraigslistListing]) -> List[ScoreResult]:
        """Score a list of Craigslist listings."""
        results = []
        
        for listing in listings:
            score_result = self.score_listing(listing)
            results.append(score_result)
        
        return results
    
    def score_listing(self, listing: CraigslistListing) -> ScoreResult:
        """Score a single listing."""
        score = 0.0
        breakdown = {}
        reasons = []
        
        # Check transmission
        title_lower = listing.title.lower()
        desc_lower = (listing.description or '').lower()
        
        # Manual transmission bonus
        if (listing.transmission and 'manual' in listing.transmission.lower()) or \
           'manual' in title_lower or 'manual' in desc_lower:
            points = self.scoring_config.get('manual_transmission', 25)
            score += points
            breakdown['manual_transmission'] = points
            reasons.append(f"Manual transmission (+{points})")
        elif (listing.transmission and 'automatic' in listing.transmission.lower()) or \
             'automatic' in title_lower or 'auto' in desc_lower:
            points = self.scoring_config.get('automatic_transmission', -10)
            score += points
            breakdown['automatic_transmission'] = points
            reasons.append(f"Automatic transmission ({points})")
        
        # Mileage scoring
        if listing.mileage:
            if listing.mileage < 100000:
                points = self.scoring_config.get('low_mileage_under_100k', 15)
                score += points
                breakdown['low_mileage'] = points
                reasons.append(f"Low mileage ({listing.mileage:,}) (+{points})")
            elif listing.mileage > 150000:
                points = self.scoring_config.get('high_mileage_over_150k', -5)
                score += points
                breakdown['high_mileage'] = points
                reasons.append(f"High mileage ({listing.mileage:,}) ({points})")
        
        # Year generation scoring
        year_match = re.search(r'\b(19|20)\d{2}\b', listing.title)
        if year_match:
            year = int(year_match.group())
            if 1997 <= year <= 2004:  # First generation
                points = self.scoring_config.get('first_gen_1997_2004', 20)
                score += points
                breakdown['first_gen'] = points
                reasons.append(f"First generation {year} (+{points})")
        
        # Turbo/Engine type
        if 'turbo' in title_lower or 'turbo' in desc_lower or 'xt' in title_lower:
            points = self.scoring_config.get('turbo_engine', -10)
            score += points
            breakdown['turbo_engine'] = points
            reasons.append(f"Turbo engine ({points})")
        
        # Title status
        title_status_lower = (listing.title_status or '').lower()
        if 'clean' in title_status_lower or 'clean' in title_lower or 'clean' in desc_lower:
            points = self.scoring_config.get('clean_title', 10)
            score += points
            breakdown['clean_title'] = points
            reasons.append(f"Clean title (+{points})")
        
        return ScoreResult(
            total_score=score,
            breakdown=breakdown,
            reasons=reasons
        )