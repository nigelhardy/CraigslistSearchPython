#!/usr/bin/env python3
"""
Craigslist Scraper v2 - Fetcher Abstraction
Clean architecture with Protocol-based fetcher for testability.
"""

import requests
import time
import json
import yaml
import argparse
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Set, Type, Protocol
from datetime import datetime
from pathlib import Path
from bs4 import BeautifulSoup
import re


# ============================================================================
# FETCHER PROTOCOL AND CONFIGURATION
# ============================================================================

@dataclass
class FetcherConfig:
    """Configuration for fetcher behavior."""
    delay_ms: int = 5000
    max_retries: int = 3


class Fetcher(Protocol):
    """Abstract protocol for fetching Craigslist data.
    
    Implementations:
    - CraigslistFetcher: Real HTTP with rate limiting
    - FileFetcher: Test fetcher reading from saved HTML files
    """
    
    def fetch_search_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a search result page and return parsed HTML."""
        ...
    
    def fetch_listing_detail(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch an individual listing detail page and return parsed HTML."""
        ...


class CraigslistFetcher:
    """Real HTTP fetcher for Craigslist with built-in rate limiting."""
    
    def __init__(self, config: FetcherConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self._last_request_time = 0.0
    
    def _rate_limit(self) -> None:
        """Enforce rate limiting between requests."""
        current_time = time.time() * 1000
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.config.delay_ms:
            wait_time = (self.config.delay_ms - time_since_last) / 1000
            print(f"⏱️  Rate limiting: waiting {wait_time:.2f}s")
            time.sleep(wait_time)
        
        self._last_request_time = time.time() * 1000
    
    def _fetch_with_retry(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch URL with retry logic."""
        for attempt in range(self.config.max_retries):
            try:
                self._rate_limit()
                print(f"🌐 Fetching: {url}")
                
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                # Handle loading state
                if 'loading' in soup.get_text().lower():
                    time.sleep(3)
                    self._rate_limit()
                    response = self.session.get(url, timeout=30)
                    soup = BeautifulSoup(response.content, 'html.parser')
                
                return soup
                
            except Exception as e:
                print(f"❌ Attempt {attempt + 1}/{self.config.max_retries} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)  # Exponential backoff
                else:
                    return None
        
        return None
    
    def fetch_search_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch a search result page."""
        return self._fetch_with_retry(url)
    
    def fetch_listing_detail(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch an individual listing detail page."""
        return self._fetch_with_retry(url)


class FileFetcher:
    """Test fetcher that reads from saved HTML files instead of making HTTP requests."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = data_dir
        print(f"📁 FileFetcher initialized with data dir: {data_dir}")
    
    def _load_html_file(self, filename: str) -> Optional[BeautifulSoup]:
        """Load HTML from file."""
        file_path = self.data_dir / filename
        
        if not file_path.exists():
            print(f"⚠️  File not found: {file_path}")
            return None
        
        try:
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
            print(f"📄 Loaded from file: {filename}")
            return BeautifulSoup(content, 'html.parser')
        except Exception as e:
            print(f"❌ Error reading file {filename}: {e}")
            return None
    
    def fetch_search_page(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch search page from saved file.
        
        Expected filename format: search_<query>_<page>.html
        """
        # Extract query and page from URL for filename
        # URL format: https://city.craigslist.org/search/cto?query=xxx&s=120
        # Stub implementation - user can customize filename mapping
        print(f"📁 [TEST MODE] Would load search page for: {url}")
        # TODO: Implement filename mapping logic
        return None
    
    def fetch_listing_detail(self, url: str) -> Optional[BeautifulSoup]:
        """Fetch listing detail from saved file.
        
        Expected filename format: listing_<id>.html
        """
        # Extract listing ID from URL
        # URL format: https://city.craigslist.org/xxx/cto/d/title/id.html
        # Stub implementation - user can customize filename mapping
        print(f"📁 [TEST MODE] Would load listing detail for: {url}")
        # TODO: Implement filename mapping logic
        return None


def create_fetcher(config: FetcherConfig, mode: str = "live", data_dir: Optional[Path] = None) -> Fetcher:
    """Factory function to create appropriate fetcher.
    
    Args:
        config: Fetcher configuration
        mode: "live" for real HTTP, "test" for file-based
        data_dir: Required for test mode, directory containing saved HTML files
    
    Returns:
        Fetcher implementation
    """
    if mode == "test":
        if data_dir is None:
            raise ValueError("data_dir required for test mode")
        return FileFetcher(data_dir)
    else:
        return CraigslistFetcher(config)


# ============================================================================
# LISTING STATE ENUM
# ============================================================================

class ListingState(Enum):
    """Tracks the processing state of a listing."""
    URL_ONLY = auto()      # Just have URL from search page
    HTML_PARSED = auto()   # Fetched and parsed HTML details
    RANKED = auto()        # Has been scored


# ============================================================================
# BASE LISTING CLASS
# ============================================================================

@dataclass
class Listing:
    """Pure data container for Craigslist listing information."""
    # Core fields (always present)
    url: str
    title: str
    price: Optional[int]
    location: str
    city: str
    category: str
    
    # State tracking
    state: ListingState = field(default=ListingState.URL_ONLY)
    
    # Fields populated during HTML parsing (optional)
    description: Optional[str] = None
    posted_date: Optional[str] = None
    images: List[str] = field(default_factory=list)
    
    # Fields populated during ranking (optional until ranked)
    score: float = field(default=0.0)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    score_reasons: List[str] = field(default_factory=list)
    
    # Metadata
    first_seen: Optional[str] = None
    last_updated: Optional[str] = None
    
    # Type discriminator for serialization
    listing_type: str = field(default="base")
    
    def to_dict(self) -> Dict[str, Any]:
        """Serialize to dictionary."""
        data = asdict(self)
        # Convert enum to string for JSON serialization
        data['state'] = self.state.name
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Listing':
        """Deserialize from dictionary."""
        # Handle state enum conversion
        state_name = data.get('state', 'URL_ONLY')
        if isinstance(state_name, str):
            data['state'] = ListingState[state_name]
        
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# ============================================================================
# VEHICLE LISTING CLASS
# ============================================================================

@dataclass
class VehicleListing(Listing):
    """Vehicle-specific listing with automotive fields."""
    
    # Vehicle-specific fields
    mileage: Optional[int] = None
    transmission: Optional[str] = None
    title_status: Optional[str] = None
    vin: Optional[str] = None
    condition: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    
    def __post_init__(self):
        """Set type discriminator after initialization."""
        if self.listing_type == "base":
            self.listing_type = "vehicle"


# ============================================================================
# LISTING TYPE REGISTRY
# ============================================================================

LISTING_TYPE_MAP: Dict[str, Type[Listing]] = {
    "base": Listing,
    "vehicle": VehicleListing,
}


def create_listing_from_dict(data: Dict[str, Any]) -> Listing:
    """Factory function to create correct listing type from dictionary."""
    listing_type = data.get('listing_type', 'base')
    listing_class = LISTING_TYPE_MAP.get(listing_type, Listing)
    
    # Handle state enum conversion
    state_name = data.get('state', 'URL_ONLY')
    if isinstance(state_name, str):
        data['state'] = ListingState[state_name]
    
    return listing_class(**{k: v for k, v in data.items() 
                           if k in listing_class.__dataclass_fields__})


# ============================================================================
# CONFIGURATION CLASSES
# ============================================================================

@dataclass
class ScoringRule:
    """Single scoring rule with keywords and points."""
    keywords: List[str]
    points: int


@dataclass
class SearchConfig:
    """Configuration for a single search type."""
    query: str
    categories: List[str]
    cities: List[str]
    max_pages: int
    storage_filename: str
    listing_type: str  # "vehicle", "bicycle", etc.
    scoring_rules: List[ScoringRule]
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SearchConfig':
        """Create SearchConfig from YAML dictionary."""
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


# ============================================================================
# STEP 1: LOAD CONFIG
# ============================================================================

def load_config(config_path: Path) -> SearchConfig:
    """Step 1: Load YAML config for queries, ranking, and storage."""
    with open(config_path, 'r', encoding='utf-8') as f:
        data = yaml.safe_load(f)
    
    search_data = data['searches']['subaru_forester']
    return SearchConfig.from_dict(search_data)


# ============================================================================
# STEP 2: LOAD PREVIOUS RESULTS
# ============================================================================

class ListingStorage:
    """Manages persistent storage of listings."""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self._listings: Dict[str, Listing] = {}
        self._load()
    
    def _load(self) -> None:
        """Load existing listings from storage file."""
        if not self.storage_path.exists():
            print(f"📂 No existing storage found at {self.storage_path}")
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for listing_data in data.get('listings', []):
                listing = create_listing_from_dict(listing_data)
                self._listings[listing.url] = listing
            
            print(f"📂 Loaded {len(self._listings)} listings from storage")
        except Exception as e:
            print(f"⚠️  Error loading storage: {e}")
            self._listings = {}
    
    def save(self) -> None:
        """Save listings to storage file."""
        try:
            data = {
                'listings': [listing.to_dict() for listing in self._listings.values()],
                'last_updated': datetime.now().isoformat(),
                'total_count': len(self._listings)
            }
            
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            print(f"💾 Saved {len(self._listings)} listings to {self.storage_path}")
        except Exception as e:
            print(f"❌ Error saving storage: {e}")
    
    def is_seen(self, url: str) -> bool:
        """Check if a URL has been seen before."""
        return url in self._listings
    
    def get_seen_urls(self) -> Set[str]:
        """Get set of all seen URLs."""
        return set(self._listings.keys())
    
    def add_listing(self, listing: Listing) -> bool:
        """Add a new listing to storage. Returns True if added, False if already exists."""
        if listing.url in self._listings:
            return False
        
        if listing.first_seen is None:
            listing.first_seen = datetime.now().isoformat()
        
        listing.last_updated = datetime.now().isoformat()
        self._listings[listing.url] = listing
        return True
    
    def get_all_listings(self) -> List[Listing]:
        """Get all stored listings."""
        return list(self._listings.values())
    
    def clear(self) -> None:
        """Clear all stored listings."""
        self._listings = {}
        if self.storage_path.exists():
            self.storage_path.unlink()
        print("🗑️  Storage cleared")


def load_previous_results(storage_path: Path, clear: bool = False) -> ListingStorage:
    """Step 2: Load previous listings from disk."""
    storage = ListingStorage(storage_path)
    if clear:
        storage.clear()
    return storage


# ============================================================================
# STEP 3: FETCH QUERY PAGES
# ============================================================================

class SearchEngine:
    """Fetches data from Craigslist using any Fetcher implementation."""
    
    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher
    
    def fetch_search_pages(self, config: SearchConfig) -> List[Listing]:
        """
        Step 3: Fetch search result pages and extract listing summaries.
        Returns list of Listings (basic info only, state=URL_ONLY).
        """
        listings = []
        
        for city in config.cities:
            for category in config.categories:
                base_url = f"https://{city}.craigslist.org/search/{category}"
                
                for page_num in range(config.max_pages):
                    params = {'query': config.query, 's': page_num * 120}
                    search_url = f"{base_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
                    
                    soup = self.fetcher.fetch_search_page(search_url)
                    if not soup:
                        break
                    
                    elements = soup.find_all('li', class_='cl-static-search-result')
                    print(f"📄 Page {page_num + 1} ({city}/{category}): Found {len(elements)} listings")
                    
                    if not elements:
                        break
                    
                    for element in elements:
                        listing = self._parse_search_result(element, city, category, config.listing_type)
                        if listing:
                            listings.append(listing)
        
        print(f"✅ Total search results: {len(listings)}")
        return listings
    
    def _parse_search_result(self, element, city: str, category: str, listing_type: str) -> Optional[Listing]:
        """Parse a single search result element into appropriate Listing type."""
        try:
            url_elem = element.find("a")
            if not url_elem:
                return None
            
            url = url_elem["href"]
            title_elem = element.find(class_="title")
            if not title_elem:
                return None
            
            title = title_elem.text
            
            price = None
            price_elem = element.find(class_="price")
            if price_elem and price_elem.text:
                price_text = price_elem.text.replace('$', '').replace(',', '')
                try:
                    price = int(price_text)
                except ValueError:
                    pass
            
            # Create appropriate listing type
            if listing_type == "vehicle":
                return VehicleListing(
                    url=url,
                    title=title,
                    price=price,
                    location=city,
                    city=city,
                    category=category,
                    state=ListingState.URL_ONLY
                )
            else:
                return Listing(
                    url=url,
                    title=title,
                    price=price,
                    location=city,
                    city=city,
                    category=category,
                    state=ListingState.URL_ONLY
                )
        except Exception as e:
            print(f"⚠️  Error parsing result: {e}")
            return None


def fetch_query_pages(config: SearchConfig, fetcher: Fetcher) -> List[Listing]:
    """Step 3: Fetch search pages, return list of Listings (basic info only)."""
    engine = SearchEngine(fetcher)
    return engine.fetch_search_pages(config)


# ============================================================================
# STEP 4: FILTER NEW URLS
# ============================================================================

def filter_new_urls(listings: List[Listing], storage: ListingStorage) -> List[str]:
    """Step 4: Filter existing URLs (remove duplicates from this run and previous)."""
    seen = storage.get_seen_urls()
    new_urls = [l.url for l in listings if l.url not in seen]
    print(f"🔍 Filtered {len(new_urls)} new URLs from {len(listings)} total")
    return new_urls


# ============================================================================
# STEP 5: FETCH INDIVIDUAL LISTINGS
# ============================================================================

def fetch_listings(
    urls: List[str],
    search_listings: List[Listing],
    config: SearchConfig,
    fetcher: Fetcher,
    storage: ListingStorage,
    limit: Optional[int] = None
) -> List[Listing]:
    """Step 5: Fetch individual listings from URL list, limited by --fetch X."""
    if limit:
        urls = urls[:limit]
        print(f"📋 Fetching {len(urls)} listings (limited)")
    
    new_listings = []
    
    # Create lookup from URL to search listing for basic info
    search_lookup = {l.url: l for l in search_listings}
    
    for i, url in enumerate(urls, 1):
        print(f"  [{i}/{len(urls)}] Fetching details...")
        
        # Get base listing from search results
        base_listing = search_lookup.get(url)
        if not base_listing:
            continue
        
        # Fetch and parse details
        listing = fetch_single_listing(fetcher, base_listing, config.listing_type)
        if listing:
            new_listings.append(listing)
            storage.add_listing(listing)
            storage.save()  # Incremental save
    
    print(f"✅ Fetched {len(new_listings)} new listings")
    return new_listings


def fetch_single_listing(fetcher: Fetcher, base_listing: Listing, listing_type: str) -> Optional[Listing]:
    """Fetch and parse details for a single listing."""
    soup = fetcher.fetch_listing_detail(base_listing.url)
    if not soup:
        return None
    
    try:
        # Parse description
        desc_elem = soup.find('section', {'id': 'postingbody'})
        description = desc_elem.get_text(strip=True) if desc_elem else None
        
        # Parse common fields
        images = []
        posted_date = None
        
        # Parse date
        time_elem = soup.find('time', class_='date timeago')
        if time_elem:
            datetime_val = time_elem.get('datetime')
            posted_date = str(datetime_val) if datetime_val else None
        
        # Parse images
        for img in soup.find_all('img'):
            src = img.get('src')
            if src and 'craigslist.org' in src:
                images.append(src)
        
        # Parse attributes
        mileage = None
        transmission = None
        title_status = None
        vin = None
        condition = None
        year = None
        
        attr_groups = soup.find_all('p', class_='attrgroup')
        for group in attr_groups:
            for span in group.find_all('span'):
                text = span.get_text(strip=True)
                if ':' in text:
                    key, value = text.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    if key in ['odometer', 'mileage']:
                        try:
                            mileage = int(value.replace(',', ''))
                        except (ValueError, AttributeError):
                            mileage = None
                    elif key == 'transmission':
                        transmission = value.lower() if value else None
                    elif key == 'title status':
                        title_status = value.lower() if value else None
                    elif key == 'vin':
                        vin = value
                    elif key == 'condition':
                        condition = value.lower() if value else None
        
        # Extract year from title
        year_match = re.search(r'\b(19|20)\d{2}\b', base_listing.title)
        if year_match:
            try:
                year = int(year_match.group())
            except (ValueError, AttributeError):
                year = None
        
        # Create appropriate listing type with all details
        if listing_type == "vehicle":
            listing = VehicleListing(
                url=base_listing.url,
                title=base_listing.title,
                price=base_listing.price,
                location=base_listing.location,
                city=base_listing.city,
                category=base_listing.category,
                state=ListingState.HTML_PARSED,
                description=description,
                posted_date=posted_date,
                images=images,
                mileage=mileage,
                transmission=transmission,
                title_status=title_status,
                vin=vin,
                condition=condition,
                year=year
            )
        else:
            listing = Listing(
                url=base_listing.url,
                title=base_listing.title,
                price=base_listing.price,
                location=base_listing.location,
                city=base_listing.city,
                category=base_listing.category,
                state=ListingState.HTML_PARSED,
                description=description,
                posted_date=posted_date,
                images=images
            )
        
        listing.last_updated = datetime.now().isoformat()
        return listing
        
    except Exception as e:
        print(f"❌ Error parsing details: {e}")
        return None


# ============================================================================
# STEP 6: RANK LISTINGS
# ============================================================================

class ListingRanker:
    """Ranks listings based on configuration rules."""
    
    def __init__(self, scoring_rules: List[ScoringRule]):
        self.scoring_rules = scoring_rules
    
    def rank(self, listings: List[Listing]) -> List[Listing]:
        """Step 6: Rank listings by calculating scores. Modifies listings in place."""
        for listing in listings:
            try:
                self._calculate_score(listing)
            except Exception as e:
                print(f"⚠️  Error ranking listing {listing.url}: {e}")
                listing.score = 0.0
                listing.score_reasons = ["Error during ranking"]
        
        # Sort by score descending
        return sorted(listings, key=lambda x: x.score, reverse=True)
    
    def _calculate_score(self, listing: Listing) -> None:
        """Calculate score for a single listing safely."""
        # Build searchable text, handling None values
        text_parts = []
        if listing.title:
            text_parts.append(listing.title)
        if listing.description:
            text_parts.append(listing.description)
        
        # Add vehicle-specific fields if available
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
                    break  # Only count first match per rule
        
        # Set on listing object
        listing.score = score
        listing.score_breakdown = breakdown
        listing.score_reasons = reasons
        listing.state = ListingState.RANKED
        listing.last_updated = datetime.now().isoformat()


def rank_listings(listings: List[Listing], scoring_rules: List[ScoringRule]) -> List[Listing]:
    """Step 6: Rank each listing based on scoring rules."""
    ranker = ListingRanker(scoring_rules)
    return ranker.rank(listings)


# ============================================================================
# STEP 7: DISPLAY LISTINGS
# ============================================================================

def display_listings(
    listings: List[Listing],
    query: str,
    output_path: Optional[Path] = None
) -> Path:
    """Step 7: Display listings based on rank in HTML output."""
    html = generate_html(listings, query)
    
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = Path(f"search_results_{timestamp}.html")
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"💾 HTML saved to: {output_path}")
    return output_path


def generate_html(listings: List[Listing], query: str) -> str:
    """Generate HTML for ranked listings."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Craigslist Search - {query}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        .meta {{ color: #666; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #4CAF50; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f9f9f9; }}
        .score {{ font-weight: bold; font-size: 1.2em; }}
        .score-high {{ color: #4CAF50; }}
        .score-medium {{ color: #FF9800; }}
        .score-low {{ color: #f44336; }}
        .price {{ color: #4CAF50; font-weight: bold; }}
        .reasons {{ font-size: 0.9em; color: #666; }}
        .details {{ font-size: 0.85em; color: #888; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 {query}</h1>
        <div class="meta">
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
            Total Listings: {len(listings)}
        </div>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Score</th>
                    <th>Title</th>
                    <th>Price</th>
                    <th>Details</th>
                    <th>Reasons</th>
                </tr>
            </thead>
            <tbody>"""
    
    for i, listing in enumerate(listings, 1):
        # Score styling
        if listing.score >= 20:
            score_class = "score-high"
        elif listing.score >= 0:
            score_class = "score-medium"
        else:
            score_class = "score-low"
        
        price_str = f"${listing.price:,}" if listing.price else "N/A"
        
        # Build details string
        details = []
        if isinstance(listing, VehicleListing):
            if listing.mileage:
                details.append(f"{listing.mileage:,} mi")
            if listing.transmission:
                details.append(listing.transmission)
            if listing.year:
                details.append(str(listing.year))
        else:
            if listing.location:
                details.append(listing.location)
        
        details_str = " | ".join(details) if details else "N/A"
        
        html += f"""
                <tr>
                    <td>#{i}</td>
                    <td class="score {score_class}">{listing.score:.1f}</td>
                    <td><a href="{listing.url}" target="_blank">{listing.title}</a></td>
                    <td class="price">{price_str}</td>
                    <td class="details">{details_str}</td>
                    <td class="reasons">{'; '.join(listing.score_reasons)}</td>
                </tr>"""
    
    html += """
            </tbody>
        </table>
    </div>
</body>
</html>"""
    
    return html


# ============================================================================
# MAIN ORCHESTRATION
# ============================================================================

def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Craigslist Scraper v2')
    parser.add_argument('--fetch', type=int, nargs='?', const=-1, default=None,
                       help='Fetch N new listings (omit for unlimited)')
    parser.add_argument('--clear', action='store_true', help='Clear storage first')
    parser.add_argument('--output', type=str, default='', help='Output HTML filename')
    parser.add_argument('--config', type=str, default='simple_config_v2.yaml', 
                       help='Config file path')
    parser.add_argument('--mode', type=str, default='live', choices=['live', 'test'],
                       help='Run mode: live (real HTTP) or test (read from files)')
    parser.add_argument('--test-data-dir', type=str, default='test_data',
                       help='Directory containing test HTML files (for test mode)')
    return parser.parse_args()


def main():
    """Main orchestration following the 7-step plan."""
    args = parse_args()
    
    print("🚀 Starting Craigslist Scraper v2\n")
    
    # Step 1: Load config
    config_path = Path(__file__).parent / args.config
    config = load_config(config_path)
    print(f"⚙️  Config loaded: {config.query}")
    print(f"   Type: {config.listing_type}")
    print(f"   Storage: {config.storage_filename}")
    print(f"   Cities: {', '.join(config.cities)}\n")
    
    # Step 2: Load previous results
    storage_path = Path(__file__).parent / config.storage_filename
    storage = load_previous_results(storage_path, clear=args.clear)
    
    # Create fetcher based on mode
    fetcher_config = FetcherConfig(delay_ms=5000, max_retries=3)
    
    if args.mode == "test":
        test_data_dir = Path(__file__).parent / args.test_data_dir
        fetcher = create_fetcher(fetcher_config, mode="test", data_dir=test_data_dir)
    else:
        fetcher = create_fetcher(fetcher_config, mode="live")
    
    # Steps 3-5 (only if --fetch specified)
    if args.fetch is not None:
        print(f"🔎 Fetch mode: {'unlimited' if args.fetch <= 0 else args.fetch} new listings\n")
        
        # Step 3: Fetch search pages
        search_listings = fetch_query_pages(config, fetcher)
        
        # Step 4: Filter URLs
        new_urls = filter_new_urls(search_listings, storage)
        
        # Step 5: Fetch listing details
        limit = args.fetch if args.fetch > 0 else None
        fetch_listings(new_urls, search_listings, config, fetcher, storage, limit=limit)
    else:
        print("📂 Display mode: showing existing listings\n")
    
    # Step 6: Rank listings
    all_listings = storage.get_all_listings()
    
    if not all_listings:
        print("❌ No listings found. Use --fetch to search.")
        return
    
    print(f"📊 Ranking {len(all_listings)} listings...\n")
    ranked_listings = rank_listings(all_listings, config.scoring_rules)
    
    # Step 7: Display
    output_path = Path(args.output) if args.output else None
    saved_path = display_listings(ranked_listings, config.query, output_path)
    
    # Summary
    print(f"\n🏆 TOP 5:")
    for i, listing in enumerate(ranked_listings[:5], 1):
        price_str = f"${listing.price:,}" if listing.price else "N/A"
        print(f"  {i}. Score: {listing.score:5.1f} | Price: {price_str:>10} | {listing.title[:50]}")
    
    print(f"\n🎉 Done! Results: {saved_path}")


if __name__ == "__main__":
    main()