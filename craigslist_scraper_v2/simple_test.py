#!/usr/bin/env python3
"""
Simple Craigslist Scraper - Test Version
"""

import requests
import time
import logging
from bs4 import BeautifulSoup
from typing import List, Dict, Any, Optional
from dataclasses import dataclass
import re
from datetime import datetime
import yaml


@dataclass
class CraigslistListing:
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


@dataclass
class ScoreResult:
    total_score: float
    breakdown: Dict[str, float]
    reasons: List[str]


class SimpleSearchEngine:
    def __init__(self, delay_ms: int = 5000):
        self.delay_ms = delay_ms
        self.session = requests.Session()
        self.last_request_time = 0
    
    def _wait_for_rate_limit(self):
        current_time = time.time() * 1000
        time_since_last_request = current_time - self.last_request_time
        
        if time_since_last_request < self.delay_ms:
            wait_time = (self.delay_ms - time_since_last_request) / 1000
            print(f"Rate limiting: waiting {wait_time:.2f} seconds")
            time.sleep(wait_time)
        
        self.last_request_time = time.time() * 1000
    
    def _make_request(self, url: str) -> Optional[BeautifulSoup]:
        try:
            self._wait_for_rate_limit()
            print(f"Fetching: {url}")
            
            # Add headers to make it look like a real browser
            headers = {
                'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36',
                'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,*/*;q=0.8',
                'Accept-Language': 'en-US,en;q=0.5',
                'Accept-Encoding': 'gzip, deflate',
                'Connection': 'keep-alive',
                'Upgrade-Insecure-Requests': '1',
            }
            
            response = self.session.get(url, timeout=30, headers=headers)
            response.raise_for_status()
            
            # Add some delay to let content load
            time.sleep(2)
            
            soup = BeautifulSoup(response.content, 'html.parser')
            
            # Wait for results to load if needed
            if 'loading' in soup.get_text().lower():
                print("Page still loading, waiting...")
                time.sleep(3)
                # Make second request
                response = self.session.get(url, timeout=30, headers=headers)
                soup = BeautifulSoup(response.content, 'html.parser')
            
            return soup
        except Exception as e:
            print(f"Error fetching {url}: {e}")
            return None
    
    def search_city(self, city: str, category: str, query: str, max_pages: int = 2) -> List[CraigslistListing]:
        listings = []
        base_url = f"https://{city}.craigslist.org/search/{category}"
        
        for page in range(max_pages):
            params = {
                'query': query,
                's': page * 120
            }
            
            search_url = f"{base_url}?" + "&".join([f"{k}={v}" for k, v in params.items()])
            soup = self._make_request(search_url)
            
            if not soup:
                continue
            
            listing_elements = soup.find_all('li', class_='cl-static-search-result')
            print(f"Found {len(listing_elements)} cl-static-search-result elements")
            
            # Debug: check if page structure is what we expect
            if not listing_elements:
                # Try other selectors
                all_links = soup.find_all('a', class_='result-title')
                print(f"Found {len(all_links)} result links")
                
                # Print first few links as debug
                for i, link in enumerate(all_links[:3]):
                    print(f"  Link {i+1}: {link.get_text(strip=True)} -> {link.get('href')}")
            
            for element in listing_elements[:10]:  # Get 10 results
                listing = self._extract_listing(element, city, category)
                if listing:
                    detailed = self._fetch_details(listing)
                    listings.append(detailed)
                    print(f"  Found: {listing.title}")
        
        return listings
    
    def _extract_listing(self, element, city: str, category: str) -> Optional[CraigslistListing]:
        try:
            # Use the same structure as working code
            url_elem = element.find("a")
            if not url_elem:
                return None
            
            url = url_elem["href"]
            title_elem = element.find(class_ = "title")
            if not title_elem:
                return None
            
            title = title_elem.text
            
            price_elem = element.find(class_ = "price")
            price = None
            if price_elem and price_elem.text:
                price_text = price_elem.text.replace('$', '').replace(',', '')
                try:
                    price = int(price_text)
                except ValueError:
                    price = None
            
            return CraigslistListing(
                url=url,
                title=title,
                price=price,
                location=city,
                city=city,
                category=category
            )
        except Exception as e:
            print(f"Error extracting listing: {e}")
            return None
    
    def _fetch_details(self, listing: CraigslistListing) -> CraigslistListing:
        soup = self._make_request(listing.url)
        if not soup:
            return listing
        
        try:
            desc_elem = soup.find('section', {'id': 'postingbody'})
            if desc_elem:
                listing.description = desc_elem.get_text(strip=True)
            
            attr_groups = soup.find_all('p', class_='attrgroup')
            for group in attr_groups:
                spans = group.find_all('span')
                for span in spans:
                    text = span.get_text(strip=True)
                    if ':' in text:
                        key, value = text.split(':', 1)
                        key = key.strip().lower()
                        value = value.strip()
                        
                        if key in ['odometer', 'mileage']:
                            try:
                                listing.mileage = int(value.replace(',', ''))
                            except ValueError:
                                pass
                        elif key in ['transmission']:
                            listing.transmission = value.lower()
                        elif key in ['title status']:
                            listing.title_status = value.lower()
                        
                        listing.attributes[key] = value
        except Exception as e:
            print(f"Error fetching details: {e}")
        
        return listing


class SimpleScorer:
    def __init__(self, config: Dict[str, Any]):
        self.scoring_config = config.get('scoring', {}).get('subaru_forester', {})
    
    def score_listings(self, listings: List[CraigslistListing]) -> List[ScoreResult]:
        results = []
        for listing in listings:
            score_result = self.score_listing(listing)
            results.append(score_result)
        return results
    
    def score_listing(self, listing: CraigslistListing) -> ScoreResult:
        score = 0.0
        breakdown = {}
        reasons = []
        
        title_lower = listing.title.lower()
        desc_lower = (listing.description or '').lower()
        
        # Manual transmission bonus
        if (listing.transmission and 'manual' in listing.transmission.lower()) or \
           'manual' in title_lower or 'manual' in desc_lower:
            points = self.scoring_config.get('manual_transmission', 25)
            score += points
            breakdown['manual_transmission'] = points
            reasons.append(f"Manual transmission (+{points})")
        
        # Mileage scoring
        if listing.mileage:
            if listing.mileage < 100000:
                points = self.scoring_config.get('low_mileage_under_100k', 15)
                score += points
                breakdown['low_mileage'] = points
                reasons.append(f"Low mileage ({listing.mileage:,}) (+{points})")
        
        # Year generation scoring
        year_match = re.search(r'\b(19|20)\d{2}\b', listing.title)
        if year_match:
            year = int(year_match.group())
            if 1997 <= year <= 2004:
                points = self.scoring_config.get('first_gen_1997_2004', 20)
                score += points
                breakdown['first_gen'] = points
                reasons.append(f"First generation {year} (+{points})")
        
        return ScoreResult(
            total_score=score,
            breakdown=breakdown,
            reasons=reasons
        )


def generate_html(listings, score_results, query):
    scored_listings = sorted(zip(listings, score_results), 
                            key=lambda x: x[1].total_score, reverse=True)
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Craigslist Search Results - {query}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .score-positive {{ color: green; font-weight: bold; }}
        .score-negative {{ color: red; }}
    </style>
</head>
<body>
    <h1>🔍 Craigslist Search Results</h1>
    <p><strong>Query:</strong> {query}</p>
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <table>
        <thead>
            <tr>
                <th>Score</th>
                <th>Title</th>
                <th>Price</th>
                <th>Mileage</th>
                <th>Transmission</th>
                <th>Reasons</th>
            </tr>
        </thead>
        <tbody>"""
    
    for listing, score_result in scored_listings:
        score_class = "score-positive" if score_result.total_score > 0 else "score-negative"
        price_str = f"${listing.price:,}" if listing.price else "N/A"
        mileage_str = f"{listing.mileage:,}" if listing.mileage else "N/A"
        
        html += f"""
            <tr>
                <td class="{score_class}">{score_result.total_score:.1f}</td>
                <td><a href="{listing.url}" target="_blank">{listing.title}</a></td>
                <td>{price_str}</td>
                <td>{mileage_str}</td>
                <td>{listing.transmission or 'N/A'}</td>
                <td><small>{'; '.join(score_result.reasons)}</small></td>
            </tr>"""
    
    html += """
        </tbody>
    </table>
</body>
</html>"""
    
    return html


def main():
    print("🚀 Starting Simple Craigslist Scraper")
    
    # Simple config
    config = {
        'scoring': {
            'subaru_forester': {
                'manual_transmission': 25,
                'low_mileage_under_100k': 15,
                'first_gen_1997_2004': 20
            }
        }
    }
    
    # Search settings
    query = "subaru"
    city = "sfbay"
    category = "cto"
    
    print(f"🔍 Searching for: {query}")
    print(f"📍 City: {city}")
    
    # Search
    search_engine = SimpleSearchEngine(delay_ms=5000)
    listings = search_engine.search_city(city, category, query, max_pages=1)
    
    print(f"✅ Found {len(listings)} listings")
    
    if not listings:
        print("❌ No listings found!")
        return
    
    # Score
    scorer = SimpleScorer(config)
    score_results = scorer.score_listings(listings)
    
    # Show results
    print("\n🏆 RESULTS:")
    scored_listings = sorted(zip(listings, score_results), 
                            key=lambda x: x[1].total_score, reverse=True)
    
    for i, (listing, score_result) in enumerate(scored_listings):
        price_str = f"${listing.price:,}" if listing.price else "N/A"
        mileage_str = f"{listing.mileage:,}" if listing.mileage else "N/A"
        
        print(f"{i+1}. Score: {score_result.total_score:.1f} | "
              f"Price: {price_str} | "
              f"Mileage: {mileage_str} | "
              f"Title: {listing.title}")
        
        for reason in score_result.reasons:
            print(f"   • {reason}")
    
    # Generate HTML
    print("\n📄 Generating HTML report...")
    html_content = generate_html(listings, score_results, query)
    
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    filename = f"search_results_{timestamp}.html"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    print(f"💾 HTML report saved to: {filename}")
    print("🎉 Done!")


if __name__ == "__main__":
    main()