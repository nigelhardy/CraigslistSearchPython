#!/usr/bin/env python3
"""
Craigslist Scraper
Usage: python main.py --config <config-file> [--fetch] [--display] [--parse-raw] [--save-raw] [--clear] [--email]
"""

import sys
import argparse
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from storage import ListingStorage
from fetcher import create_fetcher, FetcherConfig
from engine import SearchEngine
from ranking import rank_listings, DuplicateFilter
from display import display_listings
from parsers import CraigslistListingParser
from models import Listing
from notifications import notify_matches


def parse_args():
    parser = argparse.ArgumentParser(description='Craigslist Scraper')
    parser.add_argument('--config', required=True,
                       help='Config file path (e.g., config/subaru_forester.yaml)')
    parser.add_argument('--no-dedup', action='store_true',
                       help='Skip duplicate filtering')
    parser.add_argument('--fetch', type=int, nargs='?', const=-1, default=None,
                       help='Fetch listings: N (specific number) or omit (unlimited)')
    parser.add_argument('--display', action='store_true',
                       help='Display existing listings from storage (no fetch)')
    parser.add_argument('--parse-raw', action='store_true',
                       help='Parse raw HTML files from data/raw_data/ into storage')
    parser.add_argument('--save-raw', action='store_true',
                       help='Save raw HTML files when fetching')
    parser.add_argument('--clear', action='store_true',
                       help='Clear storage before operation')
    parser.add_argument('--output', type=str, default='',
                       help='Output HTML filename')
    parser.add_argument('--email', action='store_true',
                       help='Send email notification for high-scoring listings')
    return parser.parse_args()


def do_fetch(config, storage, args, fetcher):
    print(f"🔎 Fetch mode: {'unlimited' if args.fetch is None or args.fetch < 0 else args.fetch} new listings\n")

    engine = SearchEngine(fetcher)
    search_results = engine.fetch_search_pages(config)

    urls_to_process = []

    if args.fetch is not None and args.fetch > 0:
        per_combo_limit = max(1, args.fetch // max(1, search_results.get_combo_count()))
        print(f"📋 Fetching up to {per_combo_limit} listings per city/category combination")

        for (city, category) in search_results.listings_by_combo.keys():
            combo_listings = search_results.get_listings(city, category)
            combo_new_urls = [l.url for l in combo_listings if not storage.is_seen(l.url)]
            combo_urls_to_process = combo_new_urls[:per_combo_limit]
            urls_to_process.extend(combo_urls_to_process)
            print(f"🔍 {city}/{category}: {len(combo_urls_to_process)} new URLs from {len(combo_new_urls)} available")
    else:
        all_new_urls = [l.url for l in search_results.get_all_listings() if not storage.is_seen(l.url)]
        urls_to_process = all_new_urls
        print(f"🔍 Unlimited: {len(urls_to_process)} new URLs from {search_results.get_total_count()} total")

    if urls_to_process:
        print(f"📋 Fetching details for {len(urls_to_process)} listings")
        from fetcher import fetch_listings as fetch_listing_details
        parser = CraigslistListingParser()
        fetch_listing_details(urls_to_process, search_results.get_all_listings(), config, fetcher, storage, parser)


def do_parse_raw(config, storage, args, fetcher):
    print("📂 Parse mode: reading raw HTML files\n")

    config_name = Path(args.config).stem
    raw_data_dir = Path(__file__).parent / "data" / "raw_data" / config_name

    if not raw_data_dir.exists():
        print(f"❌ Raw data directory not found: {raw_data_dir}")
        print("💡 Run --fetch --save-raw first to collect raw HTML files")
        return

    parser = CraigslistListingParser()
    parsed_count = 0
    skipped_count = 0

    for html_file in raw_data_dir.glob("*.html"):
        if storage.is_seen(f"file://{html_file.name}"):
            continue

        try:
            with open(html_file, 'r', encoding='utf-8') as f:
                html_content = f.read()

            soup = fetcher.parse_html(html_content)
            
            if not parser.can_parse(soup):
                print(f"  ⏭️  Skipping search result page: {html_file.name}")
                skipped_count += 1
                continue
            
            # Extract original Craigslist URL from meta tag
            from bs4 import BeautifulSoup
            meta_url = soup.find('meta', property='og:url')
            original_url = meta_url.get('content') if meta_url else None
            
            base_listing = Listing(
                url=f"file://{html_file.absolute()}",
                title=html_file.stem.replace('_', ' '),
                price=None,
                location='',
                city=html_file.stem.split('_')[0] if '_' in html_file.stem else 'unknown',
                category='raw'
            )
            
            listing = parser.parse(soup, base_listing)

            if listing:
                # Use real Craigslist URL as primary URL
                if original_url:
                    listing.url = original_url
                
                storage.add_listing(listing)
                storage.save()
                parsed_count += 1
                print(f"  ✅ Parsed: {listing.title[:60]}")
        except Exception as e:
            print(f"  ❌ Failed: {html_file.name} - {e}")

    print(f"\n📊 Parsed {parsed_count} listing pages ({skipped_count} search pages skipped)")


def do_display(config, storage, ranked_listings, args):
    if args.output:
        output_path = Path(args.output)
    else:
        config_stem = Path(args.config).stem
        output_path = Path(f"outputs/results/{config_stem}.html")
        output_path.parent.mkdir(parents=True, exist_ok=True)
    saved_path = display_listings(ranked_listings, config.query, output_path)

    print(f"\n🏆 TOP 5:")
    for i, listing in enumerate(ranked_listings[:5], 1):
        price_str = f"${listing.price:,}" if listing.price else "N/A"
        print(f"  {i}. Score: {listing.score:5.1f} | Price: {price_str:>10} | {listing.title[:50]}")

    print(f"\n🎉 Results: {saved_path}")


def do_notify(config, ranked_listings, args):
    if not args.email:
        return

    notify_config = config.notification_config
    if not notify_config.enabled:
        print("📧 Email notifications disabled in config")
        return

    threshold = notify_config.min_score
    high_score_listings = [l for l in ranked_listings if l.score >= threshold]
    high_score_listings = high_score_listings[:notify_config.max_listings]

    if not high_score_listings:
        print("📧 No listings above score threshold for notification")
        return

    search_name = Path(args.config).stem
    success = notify_matches(high_score_listings, search_name, score_threshold=threshold)
    
    if success:
        print(f"📧 Email sent with {len(high_score_listings)} listings (score >= {threshold})")


def rank_and_filter(storage, config, args):
    processed_listings = storage.get_processed_listings()
    all_listings = storage.get_all_listings()

    if not processed_listings:
        print("❌ No processed listings found.")
        return []

    unprocessed = storage.get_unprocessed_listings()
    print(f"📊 {len(processed_listings)} of {len(all_listings)} listings processed")

    # Skip dedup if --no-dedup flag
    if getattr(args, 'no_dedup', False):
        print("   Skipping duplicate filtering (--no-dedup)")
        return rank_listings(processed_listings, config.scoring_rules, config.price_rules)

    dedup = config.dedup_config
    dup_filter = DuplicateFilter(
        similarity_threshold=dedup.similarity_threshold,
        min_title_length=dedup.min_title_length
    )

    # existing_titles feeds the cross-session duplicate check — it must NOT include
    # the titles of the listings we are about to score, or every listing would look
    # like a duplicate of itself and get filtered out.
    processed_urls = {l.url for l in processed_listings}
    existing_titles = [l.title for l in all_listings
                       if l.title and l.url not in processed_urls]
    sample = [l.title for l in processed_listings[:3]]
    print(f"   Titles sample: {sample}")
    
    before_count = len(processed_listings)
    filtered, all_titles = dup_filter.filter_duplicates(processed_listings, existing_titles)
    dup_count = before_count - len(filtered)

    if dup_count > 0:
        print(f"🔄 Filtered {dup_count} duplicates")

    if dedup.max_age_days:
        before = len(filtered)
        filtered = dup_filter.filter_age_decay(filtered, max_age_days=dedup.max_age_days)
        if len(filtered) < before:
            print(f"🗑️  Removed {before - len(filtered)} listings older than {dedup.max_age_days} days")

    return rank_listings(filtered, config.scoring_rules, config.price_rules)


def main():
    args = parse_args()

    config_path = Path(__file__).parent / args.config
    config = load_config(config_path)

    print(f"⚙️  Config: {args.config}")
    print(f"   Query: {config.query}")
    print(f"   Cities: {', '.join(config.cities)}\n")

    storage_path = Path(__file__).parent / "data" / config.storage_filename
    storage = ListingStorage(storage_path)

    if args.clear:
        print("🗑️  Clearing storage...")
        storage.clear()

    fetcher_config = FetcherConfig(delay_ms=5000, max_retries=3)
    raw_data_dir = None

    if args.save_raw:
        config_name = Path(args.config).stem
        raw_data_dir = Path(__file__).parent / "data" / "raw_data" / config_name
        print(f"💾 Raw HTML: {raw_data_dir}\n")

    fetcher = create_fetcher(fetcher_config, mode="live", raw_data_dir=raw_data_dir)

    if args.parse_raw:
        do_parse_raw(config, storage, args, fetcher)

    if args.fetch is not None:
        do_fetch(config, storage, args, fetcher)

    if args.display or args.fetch is not None or args.parse_raw:
        ranked_listings = rank_and_filter(storage, config, args)
        if ranked_listings:
            do_display(config, storage, ranked_listings, args)
            do_notify(config, ranked_listings, args)
    else:
        print("📂 Display mode (use --fetch or --parse-raw to collect data)")
        ranked_listings = rank_and_filter(storage, config, args)
        if ranked_listings:
            do_display(config, storage, ranked_listings, args)
            do_notify(config, ranked_listings, args)


if __name__ == "__main__":
    main()