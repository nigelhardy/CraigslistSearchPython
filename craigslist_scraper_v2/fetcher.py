"""Fetcher module for Craigslist data retrieval."""
import requests
import time
import json
import re
from typing import Optional, Protocol
from dataclasses import dataclass
from pathlib import Path
from bs4 import BeautifulSoup

from models import Listing
from config import SearchConfig
from storage import ListingStorage
from parsers import CraigslistListingParser


@dataclass
class FetcherConfig:
    delay_ms: int = 5000
    max_retries: int = 3


class Fetcher(Protocol):
    """Protocol for fetchers that retrieve HTML from various sources."""
    
    def fetch_search_page(self, url: str) -> Optional[BeautifulSoup]: ...
    def fetch_listing_detail(self, url: str) -> Optional[BeautifulSoup]: ...


class CraigslistFetcher:
    """Fetches listings from live Craigslist website via HTTP."""
    
    def __init__(self, config: FetcherConfig):
        self.config = config
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36'
        })
        self._last_request_time = 0.0
    
    def _rate_limit(self) -> None:
        current_time = time.time() * 1000
        time_since_last = current_time - self._last_request_time
        
        if time_since_last < self.config.delay_ms:
            wait_time = (self.config.delay_ms - time_since_last) / 1000
            print(f"⏱️  Rate limiting: waiting {wait_time:.2f}s")
            time.sleep(wait_time)
        
        self._last_request_time = time.time() * 1000
    
    def _fetch_with_retry(self, url: str) -> Optional[BeautifulSoup]:
        for attempt in range(self.config.max_retries):
            try:
                self._rate_limit()
                print(f"🌐 Fetching: {url}")
                
                response = self.session.get(url, timeout=30)
                response.raise_for_status()
                
                soup = BeautifulSoup(response.content, 'html.parser')
                
                if 'loading' in soup.get_text().lower():
                    time.sleep(3)
                    self._rate_limit()
                    response = self.session.get(url, timeout=30)
                    soup = BeautifulSoup(response.content, 'html.parser')
                
                return soup
                
            except Exception as e:
                print(f"❌ Attempt {attempt + 1}/{self.config.max_retries} failed: {e}")
                if attempt < self.config.max_retries - 1:
                    time.sleep(2 ** attempt)
                else:
                    return None
        
        return None
    
    def fetch_search_page(self, url: str) -> Optional[BeautifulSoup]:
        return self._fetch_with_retry(url)
    
    def fetch_listing_detail(self, url: str) -> Optional[BeautifulSoup]:
        return self._fetch_with_retry(url)


class FileFetcher:
    """Fetches listings from local HTML files for testing."""
    
    def __init__(self, data_dir: Path):
        self.data_dir = Path(data_dir)
        self._url_to_file_map = {}
        self._load_manifest()
        print(f"📁 FileFetcher initialized with data dir: {data_dir}")
    
    def _load_manifest(self) -> None:
        """Load the manifest file that maps URLs to local files."""
        manifest_path = self.data_dir / "manifest.json"
        if manifest_path.exists():
            with open(manifest_path, 'r') as f:
                self._url_to_file_map = json.load(f)
    
    def _url_to_filename(self, url: str) -> Optional[str]:
        """Convert a URL to a local filename.
        
        First checks the manifest, then tries to match by URL pattern.
        """
        # Check manifest first
        if url in self._url_to_file_map:
            return self._url_to_file_map[url]
        
        # Try to find by URL pattern in filename
        for filename in self.data_dir.glob("*.html"):
            # Extract URL hash or ID from filename
            match = re.search(r'_(\w+)\.html$', filename.name)
            if match:
                url_id = match.group(1)
                if url_id in url:
                    return filename.name
        
        return None
    
    def fetch_search_page(self, url: str) -> Optional[BeautifulSoup]:
        """Load a search page from file.
        
        Note: Search pages are not typically saved, so this returns None.
        For testing, we usually only save individual listing pages.
        """
        print(f"📁 [TEST MODE] Search pages not available in file mode: {url}")
        return None
    
    def fetch_listing_detail(self, url: str) -> Optional[BeautifulSoup]:
        """Load a listing detail page from local HTML file."""
        filename = self._url_to_filename(url)
        
        if not filename:
            print(f"❌ [TEST MODE] No local file found for URL: {url}")
            return None
        
        filepath = self.data_dir / filename
        
        if not filepath.exists():
            print(f"❌ [TEST MODE] File not found: {filepath}")
            return None
        
        try:
            print(f"📁 [TEST MODE] Loading: {filename}")
            with open(filepath, 'r', encoding='utf-8') as f:
                html_content = f.read()
            
            soup = BeautifulSoup(html_content, 'html.parser')
            return soup
            
        except Exception as e:
            print(f"❌ [TEST MODE] Error reading file {filepath}: {e}")
            return None
    
    def get_available_urls(self) -> list:
        """Get list of URLs that have local files available."""
        return list(self._url_to_file_map.keys())


def create_fetcher(config: FetcherConfig, mode: str = "live", data_dir: Optional[Path] = None) -> Fetcher:
    """Factory function to create the appropriate fetcher.
    
    Args:
        config: Fetcher configuration (delays, retries, etc.)
        mode: "live" for HTTP fetching from Craigslist, "test" for file-based fetching
        data_dir: Required for test mode, directory containing saved HTML files
        
    Returns:
        Fetcher instance (CraigslistFetcher or FileFetcher)
    """
    if mode == "test":
        if data_dir is None:
            raise ValueError("data_dir required for test mode")
        return FileFetcher(data_dir)
    else:
        return CraigslistFetcher(config)


def fetch_listings(
    urls: list,
    search_listings: list,
    config: SearchConfig,
    fetcher: Fetcher,
    storage: ListingStorage,
    parser: Optional[CraigslistListingParser] = None
) -> list:
    """Fetch individual listing details using the provided fetcher and parser.
    
    This function orchestrates fetching HTML and parsing it into Listing objects.
    The parser handles all Craigslist-specific extraction logic.
    
    Args:
        urls: List of listing URLs to fetch
        search_listings: List of Listing objects from search results (for base info)
        config: Search configuration
        fetcher: Fetcher instance (CraigslistFetcher or FileFetcher)
        storage: Storage instance for saving listings
        parser: Optional parser instance (defaults to CraigslistListingParser)
        
    Returns:
        List of successfully fetched and parsed Listing objects
    """
    new_listings = []
    search_lookup = {l.url: l for l in search_listings}
    
    # Create parser if not provided
    if parser is None:
        parser = CraigslistListingParser()
    
    for i, url in enumerate(urls, 1):
        print(f"  [{i}/{len(urls)}] Fetching details...")
        
        base_listing = search_lookup.get(url)
        if not base_listing:
            continue
        
        # Fetch the HTML
        soup = fetcher.fetch_listing_detail(url)
        if not soup:
            continue
        
        # Parse the HTML into a Listing
        try:
            listing = parser.parse(soup, base_listing)
            
            if listing:
                new_listings.append(listing)
                storage.add_listing(listing)
                storage.save()
            else:
                print(f"⚠️  Failed to parse listing: {url}")
                
        except Exception as e:
            print(f"❌ Error parsing details: {e}")
            continue
    
    print(f"✅ Fetched {len(new_listings)} new listings")
    return new_listings
