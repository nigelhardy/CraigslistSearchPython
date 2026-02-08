"""Tool to collect test data from live Craigslist listings.

This script fetches N listings from Craigslist and saves the raw HTML
to the test_data directory for later testing and development.
"""
import sys
import json
import re
from pathlib import Path
from datetime import datetime

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from fetcher import CraigslistFetcher, FetcherConfig
from engine import SearchEngine
from config import load_config


def slugify_title(title: str, max_length: int = 50) -> str:
    """Convert a title to a filesystem-safe slug.
    
    Examples:
    - "2002 Subaru Forester 5-Speed Manual" -> "2002-subaru-forester-5-speed-manual"
    - "!!!Great Deal!!! 2015 Honda Civic" -> "great-deal-2015-honda-civic"
    """
    # Remove non-alphanumeric characters except spaces
    cleaned = re.sub(r'[^\w\s-]', '', title)
    # Replace spaces and underscores with hyphens
    cleaned = re.sub(r'[\s_]+', '-', cleaned)
    # Remove multiple consecutive hyphens
    cleaned = re.sub(r'-+', '-', cleaned)
    # Convert to lowercase and strip
    cleaned = cleaned.lower().strip('-')
    # Truncate if too long
    if len(cleaned) > max_length:
        cleaned = cleaned[:max_length].rsplit('-', 1)[0]
    return cleaned


def collect_test_data(
    config_path: Path,
    output_dir: Path,
    num_listings: int = 10,
    delay_ms: int = 5000
):
    """Collect test data by fetching listings from Craigslist.
    
    Args:
        config_path: Path to the YAML config file
        output_dir: Directory to save the HTML files
        num_listings: Number of listings to fetch (default: 10)
        delay_ms: Delay between requests in milliseconds
    """
    print(f"🚀 Starting test data collection")
    print(f"   Config: {config_path}")
    print(f"   Output: {output_dir}")
    print(f"   Count: {num_listings} listings\n")
    
    # Load config
    config = load_config(config_path)
    print(f"⚙️  Search query: {config.query}")
    print(f"   Categories: {config.categories}")
    print(f"   Cities: {config.cities}\n")
    
    # Create output directory
    output_dir.mkdir(parents=True, exist_ok=True)
    
    # Create fetcher
    fetcher_config = FetcherConfig(delay_ms=delay_ms, max_retries=3)
    fetcher = CraigslistFetcher(fetcher_config)
    
    # Fetch search results
    print("🔎 Fetching search results...")
    engine = SearchEngine(fetcher)
    search_listings = engine.fetch_search_pages(config)
    print(f"✅ Found {len(search_listings)} listings in search\n")
    
    if not search_listings:
        print("❌ No listings found in search")
        return
    
    # Take first N listings
    listings_to_fetch = search_listings[:num_listings]
    print(f"📋 Will fetch details for {len(listings_to_fetch)} listings\n")
    
    # Manifest to track URL -> file mappings
    manifest = {}
    
    # Fetch and save each listing
    for i, listing in enumerate(listings_to_fetch, 1):
        print(f"  [{i}/{len(listings_to_fetch)}] {listing.title[:60]}...")
        
        # Fetch the HTML
        soup = fetcher.fetch_listing_detail(listing.url)
        
        if not soup:
            print(f"      ❌ Failed to fetch")
            continue
        
        # Generate filename from title
        title_slug = slugify_title(listing.title)
        filename = f"{title_slug}_{i:03d}.html"
        filepath = output_dir / filename
        
        # Save HTML to file
        try:
            html_content = str(soup)
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(html_content)
            
            # Add to manifest
            manifest[listing.url] = filename
            
            print(f"      ✅ Saved: {filename}")
            
        except Exception as e:
            print(f"      ❌ Error saving: {e}")
    
    # Save manifest
    manifest_path = output_dir / "manifest.json"
    with open(manifest_path, 'w') as f:
        json.dump(manifest, f, indent=2)
    
    print(f"\n🎉 Done! Saved {len(manifest)} listings to {output_dir}")
    print(f"📄 Manifest saved: {manifest_path}")


def main():
    """CLI entry point for test data collection."""
    import argparse
    
    parser = argparse.ArgumentParser(
        description='Collect test data from Craigslist listings'
    )
    parser.add_argument(
        '--config', '-c',
        type=str,
        default='simple_config_v2.yaml',
        help='Config file path (default: simple_config_v2.yaml)'
    )
    parser.add_argument(
        '--output', '-o',
        type=str,
        default='test_data',
        help='Output directory (default: test_data)'
    )
    parser.add_argument(
        '--count', '-n',
        type=int,
        default=10,
        help='Number of listings to fetch (default: 10)'
    )
    parser.add_argument(
        '--delay',
        type=int,
        default=5000,
        help='Delay between requests in ms (default: 5000)'
    )
    
    args = parser.parse_args()
    
    # Resolve paths
    script_dir = Path(__file__).parent.parent
    config_path = script_dir / args.config
    output_dir = script_dir / args.output
    
    collect_test_data(
        config_path=config_path,
        output_dir=output_dir,
        num_listings=args.count,
        delay_ms=args.delay
    )


if __name__ == "__main__":
    main()
