"""Configuration loading."""
import yaml
from pathlib import Path
from dataclasses import dataclass
from typing import List, Dict, Any


@dataclass
class ScoringRule:
    keywords: List[str]
    points: int


@dataclass
class SearchConfig:
    query: str
    categories: List[str]
    cities: List[str]
    max_pages: int
    storage_filename: str
    listing_type: str
    scoring_rules: List[ScoringRule]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchConfig':
        storage = data.get('storage', {})
        scoring_data = data.get('scoring', [])
        
        scoring_rules = []
        for rule in scoring_data:
            scoring_rules.append(ScoringRule(
                keywords=rule.get('keywords', []),
                points=rule.get('points', 0)
            ))
        
        return cls(
            query=data.get('query', ''),
            categories=data.get('categories', []),
            cities=data.get('cities', []),
            max_pages=data.get('max_pages', 3),
            storage_filename=storage.get('filename', 'listings.json'),
            listing_type=data.get('listing_type', 'base'),
            scoring_rules=scoring_rules
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
