"""Configuration loading."""
import yaml
from pathlib import Path
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional


@dataclass
class PriceRule:
    """Award or penalise points based on the listing's numeric price.

    Each rule has exactly one condition (above / below) and a points value.
    All matching rules are applied, so you can stack a "great deal" bonus
    on top of an "over budget" penalty independently.

    Examples::

        price_rules:
          - above: 10000   # hard budget ceiling
            points: -60
          - below: 7000    # great deal
            points: 25
          - below: 8500    # decent deal
            points: 10
          - no_price: true # unpriced listings are suspicious
            points: -10
    """
    points: int
    above: Optional[int] = None   # trigger if price > above
    below: Optional[int] = None   # trigger if price < below
    no_price: bool = False        # trigger when price is absent

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'PriceRule':
        return cls(
            points=data.get('points', 0),
            above=data.get('above'),
            below=data.get('below'),
            no_price=data.get('no_price', False),
        )


@dataclass
class ScoringRule:
    keywords: List[str]
    points: int
    match: str = "both"  # "title", "description", or "both"
    match_type: str = "partial"  # "partial" or "whole" (word boundary)
    requires: List[str] = field(default_factory=list)  # keywords that must all be present
    excludes: List[str] = field(default_factory=list)  # keywords that must NOT be present


@dataclass
class DedupConfig:
    enabled: bool = True
    similarity_threshold: float = 0.85
    min_title_length: int = 30
    max_age_days: int = 90
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'DedupConfig':
        return cls(
            enabled=data.get('enabled', True),
            similarity_threshold=data.get('similarity_threshold', 0.85),
            min_title_length=data.get('min_title_length', 30),
            max_age_days=data.get('max_age_days', 90)
        )


@dataclass
class SearchConfig:
    query: str
    categories: List[str]
    cities: List[str]
    max_pages: int
    storage_filename: str
    listing_type: str
    scoring_rules: List[ScoringRule]
    price_rules: List[PriceRule] = field(default_factory=list)
    dedup_config: DedupConfig = field(default_factory=DedupConfig)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchConfig':
        storage = data.get('storage', {})
        scoring_data = data.get('scoring', [])
        
        scoring_rules = []
        for rule in scoring_data:
            scoring_rules.append(ScoringRule(
                keywords=rule.get('keywords', []),
                points=rule.get('points', 0),
                match=rule.get('match', 'both'),
                match_type=rule.get('match_type', 'partial'),
                requires=rule.get('requires', []),
                excludes=rule.get('excludes', [])
            ))
        
        price_rules = [
            PriceRule.from_dict(r) for r in data.get('price_rules', [])
        ]

        dedup_data = data.get('deduplication', {})
        dedup_config = DedupConfig.from_dict(dedup_data) if dedup_data else DedupConfig()

        return cls(
            query=data.get('query', ''),
            categories=data.get('categories', []),
            cities=data.get('cities', []),
            max_pages=data.get('max_pages', 3),
            storage_filename=storage.get('filename', 'listings.json'),
            listing_type=data.get('listing_type', 'base'),
            scoring_rules=scoring_rules,
            price_rules=price_rules,
            dedup_config=dedup_config
        )


def load_config(config_path: Path) -> SearchConfig:
    """Load YAML config for queries, ranking, and storage."""
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    # Get the first search configuration (supports multiple search types)
    searches = data['searches']
    if not searches:
        raise ValueError("No searches found in config")
    
    # Get the first search key (e.g., 'subaru_forester', 'subaru_forester_parts')
    search_name = next(iter(searches))
    search_data = searches[search_name]
    
    return SearchConfig.from_dict(search_data)
