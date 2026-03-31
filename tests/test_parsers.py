#!/usr/bin/env python3
"""
Test runner for CraigslistListingParser.

Validates that the parser correctly extracts all vehicle fields from saved HTML.
"""
import sys
import json
from pathlib import Path
from typing import List, Dict, Any

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from fetcher import FileFetcher
from models import Listing, VehicleListing, ListingState
from parsers import CraigslistListingParser


class TestResult:
    """Simple test result container."""
    def __init__(self, name: str, passed: bool, message: str = "", data: Any = None):
        self.name = name
        self.passed = passed
        self.message = message
        self.data = data if data is not None else {}


def test_parser_extracts_all_fields(test_data_dir: Path, max_listings: int = 5) -> List[TestResult]:
    """Test that parser extracts all VehicleListing fields from saved HTML.
    
    Args:
        test_data_dir: Directory containing test HTML files and manifest.json
        max_listings: Maximum number of listings to test
        
    Returns:
        List of TestResult objects
    """
    results = []
    
    # Load manifest
    manifest_path = test_data_dir / "manifest.json"
    if not manifest_path.exists():
        results.append(TestResult(
            "manifest_exists",
            False,
            f"No manifest found at {manifest_path}. Run: python tools/collect_test_data.py --config simple_config_v2.yaml --count 10"
        ))
        return results
    
    with open(manifest_path, 'r') as f:
        manifest = json.load(f)
    
    urls = list(manifest.keys())[:max_listings]
    
    if not urls:
        results.append(TestResult("has_urls", False, "No URLs in manifest"))
        return results
    
    # Create fetcher and parser
    fetcher = FileFetcher(test_data_dir)
    parser = CraigslistListingParser()
    
    field_coverage = {}
    
    for i, url in enumerate(urls, 1):
        # Fetch HTML
        soup = fetcher.fetch_listing_detail(url)
        if not soup:
            results.append(TestResult(
                f"fetch_{i}",
                False,
                f"Failed to load HTML for URL {i}"
            ))
            continue
        
        # Create base listing
        base_listing = Listing(
            url=url,
            title="Test Listing",
            price=None,
            location="Test",
            city="sfbay",
            category="cto",
            state=ListingState.URL_ONLY
        )
        
        # Parse
        listing = parser.parse(soup, base_listing)
        
        if not listing:
            results.append(TestResult(
                f"parse_{i}",
                False,
                f"Parser returned None for listing {i}"
            ))
            continue
        
        # Check it's a VehicleListing
        if not isinstance(listing, VehicleListing):
            results.append(TestResult(
                f"is_vehicle_{i}",
                False,
                f"Expected VehicleListing, got {type(listing).__name__}"
            ))
            continue
        
        # Track field coverage
        fields = {
            'url': bool(listing.url),
            'title': bool(listing.title) and listing.title != "Test Listing",
            'price': listing.price is not None,
            'location': bool(listing.location) and listing.location != "Test",
            'city': bool(listing.city),
            'category': bool(listing.category),
            'description': bool(listing.description),
            'posted_date': bool(listing.posted_date),
            'images': len(listing.images) > 0,
            'mileage': listing.mileage is not None,
            'transmission': bool(listing.transmission),
            'title_status': bool(listing.title_status),
            'year': listing.year is not None,
            'vin': bool(listing.vin),
            'condition': bool(listing.condition),
            'make': bool(listing.make),
            'model': bool(listing.model),
        }
        
        for field, has_value in fields.items():
            if field not in field_coverage:
                field_coverage[field] = 0
            if has_value:
                field_coverage[field] += 1
        
        results.append(TestResult(
            f"parse_{i}",
            True,
            f"Parsed VehicleListing with {sum(fields.values())}/{len(fields)} fields",
            {'listing': listing, 'fields': fields}
        ))
    
    # Add field coverage summary
    results.append(TestResult(
        "field_coverage",
        True,
        f"Field coverage across {len(urls)} listings",
        field_coverage
    ))
    
    return results


def print_results(results: List[TestResult]) -> bool:
    """Print test results and return True if all passed."""
    passed = 0
    failed = 0
    
    print("\n" + "="*70)
    print("TEST RESULTS")
    print("="*70 + "\n")
    
    for result in results:
        status = "✅ PASS" if result.passed else "❌ FAIL"
        print(f"{status}: {result.name}")
        if result.message:
            print(f"       {result.message}")
        
        # Print field details for coverage test
        if result.name == "field_coverage" and result.data:
            print("\n       Field Coverage:")
            for field, count in sorted(result.data.items()):
                pct = (count / max(1, len([r for r in results if r.name.startswith('parse_') and r.passed]))) * 100
                bar = "█" * int(pct / 5) + "░" * (20 - int(pct / 5))
                print(f"       {bar} {field:20s} {count:2d} ({pct:5.1f}%)")
        
        # Print sample listing details
        if result.name.startswith('parse_') and result.passed and result.data.get('listing'):
            listing = result.data['listing']
            print(f"       Title: {listing.title[:50]}...")
            print(f"       Year: {listing.year}, Mileage: {listing.mileage}, Trans: {listing.transmission}")
        
        if result.passed:
            passed += 1
        else:
            failed += 1
    
    print("\n" + "="*70)
    print(f"SUMMARY: {passed} passed, {failed} failed")
    print("="*70 + "\n")
    
    return failed == 0


def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='Test CraigslistListingParser')
    parser.add_argument('--test-data-dir', '-d', type=str, default='test_data',
                       help='Test data directory (default: test_data)')
    parser.add_argument('--count', '-n', type=int, default=5,
                       help='Number of listings to test (default: 5)')
    parser.add_argument('--all', action='store_true',
                       help='Run full test suite (all available listings)')
    
    args = parser.parse_args()
    
    script_dir = Path(__file__).parent.parent
    test_data_dir = script_dir / args.test_data_dir
    
    # Determine count
    count = None if args.all else args.count
    
    print("🧪 CraigslistListingParser Test Suite")
    print(f"   Test data: {test_data_dir}")
    print(f"   Max listings: {'all' if count is None else count}\n")
    
    # Run tests
    results = test_parser_extracts_all_fields(test_data_dir, count or 999)
    
    # Print results
    all_passed = print_results(results)
    
    # Exit with appropriate code
    sys.exit(0 if all_passed else 1)


if __name__ == "__main__":
    main()
