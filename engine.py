"""Search engine for fetching and parsing Craigslist search results."""
from typing import List, Optional
from bs4 import BeautifulSoup

from models import Listing, VehicleListing, ListingState, SearchResults
from fetcher import Fetcher
from config import SearchConfig

# Maximum number of consecutive failures per city/category combination before aborting
FAILURE_TOLERANCE = 5


class SearchEngine:
    """Fetches data from Craigslist using any Fetcher implementation."""
    
    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher
    
    def fetch_search_pages(self, config: SearchConfig) -> SearchResults:
        """Fetch search result pages and extract listing summaries organized by city/category."""
        results = SearchResults()
        
        for city in config.cities:
            for category in config.categories:
                print(f"\n🔍 Processing {city}/{category}")
                
                for page_num in range(config.max_pages):
                    # Check if we should abort this combo due to failures
                    if results.should_abort_combo(city, category, FAILURE_TOLERANCE):
                        print(f"❌ ABORTING {city}/{category} after {FAILURE_TOLERANCE} failures")
                        break
                    
                    # Fetch this page
                    page_listings, success = self._fetch_single_page(city, category, page_num, config)
                    
                    if success:
                        results.add_listings(city, category, page_listings)
                        print(f"📄 {city}/{category} page {page_num + 1}: {len(page_listings)} listings")
                        
                        # If no listings found, this combo is exhausted
                        if not page_listings:
                            results.mark_exhausted(city, category)
                            print(f"📄 {city}/{category}: No more listings found")
                            break
                    else:
                        results.increment_failure(city, category)
                        print(f"❌ {city}/{category} page {page_num + 1}: Failed to fetch page ({results.failure_counts[(city, category)]}/{FAILURE_TOLERANCE})")
                        continue
        
        # Print summary
        print(f"\n{results.get_summary()}")
        return results
    
    def _fetch_single_page(self, city: str, category: str, page_num: int, config: SearchConfig) -> tuple[list[Listing], bool]:
        """Fetch a single page for a specific city/category combination.
        
        Args:
            city: Craigslist city (e.g., 'sfbay')
            category: Craigslist category (e.g., 'cta')
            page_num: Page number (0-based)
            config: Search configuration
            
        Returns:
            Tuple of (listings_found, success)
        """
        try:
            base_url = f"https://{city}.craigslist.org/search/{category}"
            params = {'query': config.query, 's': page_num * 120}
            search_url = f"{base_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
            
            soup = self.fetcher.fetch_search_page(search_url)
            if not soup:
                return [], False
            
            elements = soup.find_all('li', class_='cl-static-search-result')
            if not elements:
                return [], True  # Success but no listings
            
            listings = []
            for element in elements:
                listing = self._parse_search_result(element, city, category, config.listing_type)
                if listing:
                    listings.append(listing)
            
            return listings, True
            
        except Exception as e:
            print(f"❌ Error fetching {city}/{category} page {page_num + 1}: {e}")
            return [], False
    
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
