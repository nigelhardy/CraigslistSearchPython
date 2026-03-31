import asyncio
import time
import logging
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
from urllib.parse import urljoin, urlparse
import requests
from bs4 import BeautifulSoup

logger = logging.getLogger(__name__)


@dataclass
class CraigslistListing:
    """Represents a single Craigslist listing."""
    url: str
    title: str
    price: Optional[int]
    location: str
    city: str
    category: str
    description: Optional[str] = None
    image_urls: List[str] = None  # type: ignore
    attributes: Dict[str, Any] = None  # type: ignore
    posted_date: Optional[str] = None
    vin: Optional[str] = None
    mileage: Optional[int] = None
    transmission: Optional[str] = None
    condition: Optional[str] = None
    title_status: Optional[str] = None
    
    def __post_init__(self):
        if self.image_urls is None:
            self.image_urls = []
        if self.attributes is None:
            self.attributes = {}


class CraigslistSearchEngine:
    """Search engine for Craigslist listings with rate limiting and error handling."""
    
    def __init__(self, delay_ms: int = 5000, max_retries: int = 3):
        self.delay_ms = delay_ms
        self.max_retries = max_retries
        self.session = requests.Session()
        self.session.headers.update({
            'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36'
        })
        self.last_request_time = 0
    
    def _wait_for_rate_limit(self):
        """Ensure minimum delay between requests."""
        current_time = time.time() * 1000  # Convert to milliseconds
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.delay_ms:
            wait_time = (self.delay_ms - time_since_last_request) / 1000
            logger.debug(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
        
        self.last_request_time = time.time() * 1000
    
    def _make_request(self, url: str, retries_left: Optional[int] = None) -> Optional[BeautifulSoup]:
        """Make HTTP request with retry logic."""
        if retries_left is None:
            retries_left = self.max_retries
        
        try:
            self._wait_for_rate_limit()
            
            logger.debug(f"Fetching URL: {url}")
            response = self.session.get(url, timeout=30)
            response.raise_for_status()
            
            return BeautifulSoup(response.content, 'html.parser')
            
        except requests.exceptions.RequestException as e:
            logger.warning(f"Request failed for {url}: {e}")
            
            if retries_left > 0:
                wait_time = (self.max_retries - retries_left + 1) * 2
                logger.info(f"Retrying in {wait_time} seconds... ({retries_left} retries left)")
                time.sleep(wait_time)
                return self._make_request(url, retries_left - 1)
            else:
                logger.error(f"Failed to fetch {url} after {self.max_retries} attempts")
                return None
    
    def _extract_listing_from_summary(self, listing_element, city: str, category: str) -> Optional[CraigslistListing]:
        """Extract listing information from search result summary."""
        try:
            # Extract basic information from the listing element
            title_elem = listing_element.find('a', class_='result-title')
            if not title_elem:
                return None
            
            title = title_elem.get_text(strip=True)
            url = title_elem.get('href', '')
            
            # Ensure URL is absolute
            if url.startswith('/'):
                base_url = f"https://{city}.craigslist.org"
                url = urljoin(base_url, url)
            
            # Extract price
            price_elem = listing_element.find('span', class_='result-price')
            price = None
            if price_elem:
                price_text = price_elem.get_text(strip=True).replace('$', '').replace(',', '')
                try:
                    price = int(price_text)
                except ValueError:
                    price = None
            
            # Extract location
            location_elem = listing_element.find('span', class_='result-hood')
            location = location_elem.get_text(strip=True).strip('()') if location_elem else city
            
            return CraigslistListing(
                url=url,
                title=title,
                price=price,
                location=location,
                city=city,
                category=category
            )
            
        except Exception as e:
            logger.warning(f"Error extracting listing from summary: {e}")
            return None
    
    def _fetch_listing_details(self, listing: CraigslistListing) -> CraigslistListing:
        """Fetch detailed information for a specific listing."""
        soup = self._make_request(listing.url)
        if not soup:
            return listing
        
        try:
            # Extract description
            desc_elem = soup.find('section', {'id': 'postingbody'})
            if desc_elem:
                # Remove any "qrCode" div
                for qr_div in desc_elem.find_all('div', class_='print-qrcode'):
                    qr_div.decompose()
                listing.description = desc_elem.get_text(strip=True)
            
            # Extract images
            image_elems = soup.find_all('img')
            for img in image_elems:
                src = img.get('src')
                if src and isinstance(src, str) and 'images.craigslist.org' in src:
                    listing.image_urls.append(src)
            
            # Extract posting attributes
            attr_groups = soup.find_all('p', class_='attrgroup')
            for group in attr_groups:
                spans = group.find_all('span')
                for span in spans:
                    text = span.get_text(strip=True)
                    if ':' in text:
                        key, value = text.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        # Map common attributes
                        if key in ['odometer', 'mileage']:
                            try:
                                listing.mileage = int(value.replace(',', ''))
                            except ValueError:
                                pass
                        elif key in ['transmission']:
                            listing.transmission = value.lower()
                        elif key in ['condition']:
                            listing.condition = value.lower()
                        elif key in ['title status']:
                            listing.title_status = value.lower()
                        elif key in ['vin']:
                            listing.vin = value
                        
                        listing.attributes[key] = value
            
            # Extract posted date
            post_date_elem = soup.find('time', {'class': 'posting date'})
            if post_date_elem:
                datetime_val = post_date_elem.get('datetime')
                if isinstance(datetime_val, str):
                    listing.posted_date = datetime_val
            
        except Exception as e:
            logger.warning(f"Error fetching details for {listing.url}: {e}")
        
        return listing
    
    def search_city(self, city: str, category: str, query: str, max_pages: int = 3) -> List[CraigslistListing]:
        """Search for listings in a specific city."""
        listings = []
        
        base_url = f"https://{city}.craigslist.org/search/{category}"
        
        for page in range(max_pages):
            params = {
                'query': query,
                's': page * 120  # Craigslist shows 120 results per page
            }
            
            search_url = f"{base_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
            
            logger.info(f"Searching {city} page {page + 1}/{max_pages}")
            soup = self._make_request(search_url)
            
            if not soup:
                continue
            
            # Find all listing elements
            listing_elements = soup.find_all('li', class_='result-row')
            
            if not listing_elements:
                logger.info(f"No more listings found on page {page + 1}")
                break
            
            page_listings = []
            for element in listing_elements:
                listing = self._extract_listing_from_summary(element, city, category)
                if listing:
                    page_listings.append(listing)
            
            # Fetch details for each listing
            for listing in page_listings:
                detailed_listing = self._fetch_listing_details(listing)
                listings.append(detailed_listing)
                logger.debug(f"Fetched details for: {listing.title}")
            
            logger.info(f"Found {len(page_listings)} listings on page {page + 1}")
        
        return listings
    
    def search_multiple_cities(self, city_configs: Dict[str, Any], category: str, query: str, 
                             max_pages_per_city: int = 3) -> List[CraigslistListing]:
        """Search across multiple cities with priority handling."""
        all_listings = []
        
        # Process cities in priority order
        for priority, cities in city_configs.items():
            if not isinstance(cities, list):
                cities = [cities]
            
            logger.info(f"Searching {priority} cities: {', '.join(cities)}")
            
            for city in cities:
                try:
                    city_listings = self.search_city(city, category, query, max_pages_per_city)
                    
                    # Add priority bonus
                    priority_bonus = 5 if priority == 'primary' else 2 if priority == 'secondary' else 0
                    for listing in city_listings:
                        listing.attributes['priority_bonus'] = priority_bonus
                    
                    all_listings.extend(city_listings)
                    logger.info(f"Found {len(city_listings)} listings in {city}")
                    
                except Exception as e:
                    logger.error(f"Error searching {city}: {e}")
                    continue
        
        logger.info(f"Total listings found: {len(all_listings)}")
        return all_listings