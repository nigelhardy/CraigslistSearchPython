"""Search engine for fetching and parsing Craigslist search results."""
from typing import List, Optional
from bs4 import BeautifulSoup

from models import Listing, VehicleListing, ListingState
from fetcher import Fetcher
from config import SearchConfig


class SearchEngine:
    """Fetches data from Craigslist using any Fetcher implementation."""
    
    def __init__(self, fetcher: Fetcher):
        self.fetcher = fetcher
    
    def fetch_search_pages(self, config: SearchConfig) -> List[Listing]:
        """Fetch search result pages and extract listing summaries."""
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
