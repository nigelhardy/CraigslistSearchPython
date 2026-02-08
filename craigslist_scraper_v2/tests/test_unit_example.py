#!/usr/bin/env python3
"""
Simple unit test example for CraigslistListingParser.

This shows the basic pattern:
1. Load HTML file
2. Send to CraigslistListingParser
3. Get VehicleListing object
4. Check desired attributes
"""
import sys
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from fetcher import FileFetcher
from models import Listing, VehicleListing, ListingState
from parsers import CraigslistListingParser


def test_single_listing():
    """Test parsing a single HTML file."""
    
    # 1. Load HTML file
    test_data_dir = Path("test_data")
    fetcher = FileFetcher(test_data_dir)
    
    # Use first URL from manifest
    import json
    with open(test_data_dir / "manifest.json", 'r') as f:
        manifest = json.load(f)
    
    url = list(manifest.keys())[0]
    print(f"🧪 Testing: {url}")
    
    # Load HTML
    soup = fetcher.fetch_listing_detail(url)
    assert soup, "Failed to load HTML"
    
    # 2. Send to CraigslistListingParser
    parser = CraigslistListingParser()
    base_listing = Listing(
        url=url,
        title="Test",  # Will be updated by parser
        price=None,
        location="Test",
        city="sfbay",
        category="cto",
        state=ListingState.URL_ONLY
    )
    
    listing = parser.parse(soup, base_listing)
    
    # 3. Get VehicleListing object
    assert listing, "Parser returned None"
    assert isinstance(listing, VehicleListing), f"Expected VehicleListing, got {type(listing)}"
    
    # 4. Check desired attributes
    print("✅ VehicleListing created successfully")
    print(f"   Title: {listing.title}")
    print(f"   Year: {listing.year}")
    print(f"   Make: {listing.make}")
    print(f"   Model: {listing.model}")
    print(f"   Price: ${listing.price:,}")
    print(f"   Mileage: {listing.mileage:,}")
    print(f"   Transmission: {listing.transmission}")
    print(f"   Title Status: {listing.title_status}")
    
    # Assertions for key vehicle fields
    assert listing.title and listing.title != "Test", "Title not extracted"
    assert listing.year, "Year not extracted"
    assert listing.make, "Make not extracted"
    assert listing.model, "Model not extracted"
    assert listing.price is not None, "Price not extracted"
    assert listing.mileage is not None, "Mileage not extracted"
    assert listing.transmission, "Transmission not extracted"
    assert listing.title_status, "Title status not extracted"
    
    print("✅ All vehicle attributes extracted correctly!")
    return listing


if __name__ == "__main__":
    test_single_listing()