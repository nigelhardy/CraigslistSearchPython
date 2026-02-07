from dataclasses import dataclass
from typing import List, Dict, Any, Optional
import yaml
from pathlib import Path


@dataclass
class SearchConfig:
    name: str
    description: str
    query: str
    categories: List[str]
    cities: Dict[str, Any]
    max_fetches: int
    max_pages_per_city: int
    wait_ms: int
    price_range: Optional[List[int]] = None


@dataclass
class ScoringConfig:
    manual_transmission: int = 20
    low_mileage_under_80k: int = 20
    low_mileage_under_120k: int = 15
    one_owner: int = 15
    first_gen_1997_2004: int = 25
    clean_title: int = 12
    non_turbo: int = 15
    affordable_price_under_7k: int = 20
    affordable_price_under_10k: int = 15
    good_photos: int = 8
    turbo_engine: int = -15
    automatic_transmission: int = -10
    multiple_owners: int = -5
    salvage_title: int = -25
    dealer_listing: int = -20
    wrong_generation_2003_plus: int = -15
    high_mileage_over_150k: int = -10


@dataclass
class OutputConfig:
    console_max_title_length: int = 40
    console_show_score_breakdown: bool = True
    console_highlight_negative_scores: bool = True
    html_template_style: str = "modern"
    html_include_images: bool = True
    html_max_results_per_page: int = 50
    file_save_all_results: bool = True
    file_primary_format: str = "json"
    file_backup_formats: List[str] = None  # type: ignore
    file_rotation: bool = True
    file_max_file_size_mb: int = 5
    
    def __post_init__(self):
        if self.file_backup_formats is None:
            self.file_backup_formats = ["yaml"]


@dataclass
class AppConfig:
    minimum_score_threshold: float = 5.0
    local_bonus_points: float = 5.0
    duplicate_similarity_threshold: float = 0.8
    default_delay_ms: int = 5000
    max_retries: int = 3
    backoff_multiplier: int = 2


@dataclass
class Configuration:
    searches: Dict[str, SearchConfig]
    scoring: Dict[str, ScoringConfig]
    output: OutputConfig
    app: AppConfig
    
    @classmethod
    def from_yaml(cls, config_path: Path) -> 'Configuration':
        """Load configuration from YAML file."""
        with open(config_path, 'r') as file:
            data = yaml.safe_load(file)
        
        # Parse search configurations
        searches = {}
        for search_id, search_data in data.get('searches', {}).items():
            searches[search_id] = SearchConfig(**search_data)
        
        # Parse scoring configurations
        scoring = {}
        scoring_defaults = data.get('scoring', {}).get('defaults', {})
        for algorithm_id, scoring_data in data.get('scoring', {}).items():
            if algorithm_id != 'defaults':
                # Merge defaults with specific algorithm config
                merged_config = {**scoring_defaults, **scoring_data}
                scoring[algorithm_id] = ScoringConfig(**merged_config)
        
        # Parse output configuration
        output_data = data.get('output', {})
        console_config = output_data.get('console', {})
        html_config = output_data.get('html', {})
        file_config = output_data.get('file_management', {})
        
        output_config = OutputConfig(
            console_max_title_length=console_config.get('max_title_length', 40),
            console_show_score_breakdown=console_config.get('show_score_breakdown', True),
            console_highlight_negative_scores=console_config.get('highlight_negative_scores', True),
            html_template_style=html_config.get('template_style', 'modern'),
            html_include_images=html_config.get('include_images', True),
            html_max_results_per_page=html_config.get('max_results_per_page', 50),
            file_save_all_results=file_config.get('save_all_results', True),
            file_primary_format=file_config.get('primary_format', 'json'),
            file_backup_formats=file_config.get('backup_formats', ["yaml"]),
            file_rotation=file_config.get('rotation', True),
            file_max_file_size_mb=file_config.get('max_file_size_mb', 5)
        )
        
        # Parse app configuration
        defaults = data.get('scoring', {}).get('defaults', {})
        rate_limiting = data.get('rate_limiting', {})
        
        app_config = AppConfig(
            minimum_score_threshold=defaults.get('minimum_score_threshold', 5.0),
            local_bonus_points=defaults.get('local_bonus_points', 5.0),
            duplicate_similarity_threshold=defaults.get('duplicate_similarity_threshold', 0.8),
            default_delay_ms=rate_limiting.get('default_delay_ms', 5000),
            max_retries=rate_limiting.get('max_retries', 3),
            backoff_multiplier=rate_limiting.get('backoff_multiplier', 2)
        )
        
        return cls(
            searches=searches,
            scoring=scoring,
            output=output_config,
            app=app_config
        )