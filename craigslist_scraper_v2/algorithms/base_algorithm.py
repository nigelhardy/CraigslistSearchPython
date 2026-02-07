from abc import ABC, abstractmethod
from typing import Dict, Any, List
from dataclasses import dataclass

from ..scrapers.craigslist_scraper import CraigslistListing


@dataclass
class ScoreResult:
    """Result of scoring a listing with detailed breakdown."""
    total_score: float
    score_breakdown: Dict[str, float]
    reasons: List[str]
    should_include: bool
    
    def add_score(self, category: str, points: float, reason: str):
        """Add a score component with reason."""
        self.score_breakdown[category] = points
        self.reasons.append(reason)
        self.total_score += points
    
    def get_positive_scores(self) -> Dict[str, float]:
        """Get only positive scoring components."""
        return {k: v for k, v in self.score_breakdown.items() if v > 0}
    
    def get_negative_scores(self) -> Dict[str, float]:
        """Get only negative scoring components."""
        return {k: v for k, v in self.score_breakdown.items() if v < 0}


class BaseScoringAlgorithm(ABC):
    """Abstract base class for scoring algorithms."""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.name = self.__class__.__name__
    
    @abstractmethod
    def calculate_score(self, listing: CraigslistListing) -> ScoreResult:
        """Calculate score for a single listing."""
        pass
    
    @abstractmethod
    def get_algorithm_name(self) -> str:
        """Get the name of this scoring algorithm."""
        pass
    
    def is_spam(self, listing: CraigslistListing) -> bool:
        """Check if listing is likely spam. Override as needed."""
        return False