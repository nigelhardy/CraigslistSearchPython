#!/usr/bin/env python3
"""
Craigslist Scraper v2 - Refactored with Clean Module Structure
Main orchestration file - thin wrapper that calls other modules.
"""

import sys
import argparse
from pathlib import Path

# Add current directory to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from storage import ListingStorage
from fetcher import create_fetcher, FetcherConfig
from engine import SearchEngine
from ranking import rank_listings
from display import display_listings
from parsers import CraigslistListingParser


def parse_args():
    """Parse command line arguments."""
    parser = argparse.ArgumentParser(description='Craigslist Scraper v2')
    parser.add_argument('--fetch', type=int, nargs='?', const=-1, default=None,
                       help='Fetch N new listings (omit for unlimited)')
    parser.add_argument('--clear', action='store_true', help='Clear storage first')
    parser.add_argument('--output', type=str, default='', help='Output HTML filename')
    parser.add_argument('--config', type=str, default='simple_config_v2.yaml',
                       help='Config file path')
    parser.add_argument('--save-raw', action='store_true', help='Save raw HTML files for debugging')
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
    storage = ListingStorage(storage_path)
    if args.clear:
        storage.clear()
    
    # Create fetcher (always live mode for main.py)
    fetcher_config = FetcherConfig(delay_ms=5000, max_retries=3)
    
    # Set up raw data directory if --save-raw flag is used
    raw_data_dir = None
    if args.save_raw:
        config_name = Path(args.config).stem  # Get filename without extension
        raw_data_dir = Path(__file__).parent / "raw_data" / config_name
        print(f"💾 Raw HTML will be saved to: {raw_data_dir}\n")
    
    fetcher = create_fetcher(fetcher_config, mode="live", raw_data_dir=raw_data_dir)
    
    # Steps 3-5 (only if --fetch specified)
    if args.fetch is not None:
        print(f"🔎 Fetch mode: {'unlimited' if args.fetch <= 0 else args.fetch} new listings\n")
        
        # Step 3: Fetch search pages
        engine = SearchEngine(fetcher)
        search_listings = engine.fetch_search_pages(config)
        
        # Step 4: Filter URLs
        new_urls = [l.url for l in search_listings if not storage.is_seen(l.url)]
        print(f"🔍 Filtered {len(new_urls)} new URLs from {len(search_listings)} total")
        
        # Step 5: Fetch listing details
        if new_urls:
            limit = args.fetch if args.fetch > 0 else None
            if limit:
                new_urls = new_urls[:limit]
                print(f"📋 Fetching {len(new_urls)} listings (limited)")
            
            from fetcher import fetch_listings as fetch_listing_details
            parser = CraigslistListingParser()
            fetch_listing_details(new_urls, search_listings, config, fetcher, storage, parser)
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