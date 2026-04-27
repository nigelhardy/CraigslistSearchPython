#!/usr/bin/env python3
"""
Multi-config runner for periodic scraping.
Usage: python runner.py [--configs config1.yaml config2.yaml] [--configs-file config_list.yaml]

Designed to be run via cron every 15 minutes.
"""

import sys
import argparse
from pathlib import Path
from datetime import datetime
import json
import os

sys.path.insert(0, str(Path(__file__).parent))

from config import load_config
from storage import ListingStorage
from fetcher import create_fetcher, FetcherConfig
from engine import SearchEngine
from ranking import rank_listings, DuplicateFilter
from notifications import notify_matches
from models import Listing


class RunnerState:
    """Tracks state between runs for the runner."""
    
    def __init__(self, state_file: Path):
        self.state_file = state_file
        self.state_file.parent.mkdir(parents=True, exist_ok=True)
        self._load()
    
    def _load(self):
        if self.state_file.exists():
            with open(self.state_file, 'r') as f:
                self.data = json.load(f)
        else:
            self.data = {"last_run": None, "notified_urls": []}
    
    def save(self):
        with open(self.state_file, 'w') as f:
            json.dump(self.data, f, indent=2)
    
    @property
    def last_run(self):
        return self.data.get("last_run")
    
    @last_run.setter
    def last_run(self, value):
        self.data["last_run"] = value
    
    @property
    def notified_urls(self):
        return set(self.data.get("notified_urls", []))
    
    def mark_notified(self, url: str):
        if url not in self.data["notified_urls"]:
            self.data["notified_urls"].append(url)
    
    def clear_notified_for_config(self, config_name: str):
        self.data["notified_urls"] = [
            url for url in self.data.get("notified_urls", [])
            if not url.startswith(f"[{config_name}]")
        ]


def load_configs_list(configs_file: Path) -> list:
    """Load list of config paths from a YAML file."""
    import yaml
    with open(configs_file, 'r') as f:
        data = yaml.safe_load(f)
    return data.get("configs", [])


def run_config(config_path: Path, state: RunnerState, args, fetcher, runner_args) -> tuple:
    """Run a single config and return results."""
    config_name = config_path.stem
    print(f"\n{'='*60}")
    print(f"Processing: {config_name}")
    print('='*60)
    
    config = load_config(config_path)
    
    storage_path = Path(__file__).parent / "data" / config.storage_filename
    storage = ListingStorage(storage_path)
    
    # Track URLs that are already in storage BEFORE we fetch
    urls_before_fetch = storage.get_seen_urls()
    
    engine = SearchEngine(fetcher)
    search_results = engine.fetch_search_pages(config)
    
    all_new_urls = [l.url for l in search_results.get_all_listings() if not storage.is_seen(l.url)]
    
    if not all_new_urls:
        print("No new URLs found")
        return 0, 0
    
    print(f"Found {len(all_new_urls)} new URLs")
    
    if args.fetch is not None and args.fetch > 0:
        all_new_urls = all_new_urls[:args.fetch]
    
    if all_new_urls:
        from fetcher import fetch_listings as fetch_listing_details
        from parsers import CraigslistListingParser
        parser = CraigslistListingParser()
        fetch_listing_details(all_new_urls, search_results.get_all_listings(), config, fetcher, storage, parser)
    
    new_count = len(all_new_urls)
    notified_count = 0
    
    # Track newly fetched URLs (URLs in storage now that weren't before)
    # We need to reload storage to get the new listings
    storage = ListingStorage(storage_path)
    new_listings = [l for l in storage.get_all_listings() if l.url not in urls_before_fetch]
    new_urls_this_run = {l.url for l in new_listings}
    
    if args.email and config.notification_config.enabled:
        notified_count = send_notifications(new_urls_this_run, storage, config, state, config_name, runner_args)
    
    return new_count, notified_count


def send_notifications(new_urls_this_run, storage: ListingStorage, config, state: RunnerState, config_name: str, runner_args) -> int:
    """Send notifications only for new listings above threshold."""
    from models import ListingState
    
    # Only look at newly fetched listings
    new_listings = [l for l in storage.get_all_listings() if l.url in new_urls_this_run]
    
    if not new_listings:
        print("No new listings to notify about")
        return 0
    
    notify_config = config.notification_config
    threshold = notify_config.min_score
    
    existing_notified = state.notified_urls
    
    # Apply similarity dedup to new listings only
    if runner_args.skip_dedup:
        filtered = new_listings
    else:
        dedup = config.dedup_config
        dup_filter = DuplicateFilter(
            similarity_threshold=dedup.similarity_threshold,
            min_title_length=dedup.min_title_length
        )
        filtered, _ = dup_filter.filter_duplicates(new_listings, [])
    
    ranked = rank_listings(filtered, config.scoring_rules, config.price_rules)
    
    # Filter: above threshold AND not previously notified
    new_above_threshold = [
        l for l in ranked
        if l.score >= threshold and l.url not in existing_notified
    ][:notify_config.max_listings]
    
    if not new_above_threshold:
        print("No new listings above threshold to notify")
        return 0
    
    subject = f"New {config_name} Listings! ({len(new_above_threshold)} found) - {datetime.now().strftime('%Y-%m-%d %H:%M')}"
    
    from notifications import listings_to_html
    html_content = listings_to_html(new_above_threshold, f"New {config_name} Listings")
    
    from notifications import send_email
    success = send_email(subject, html_content)
    
    if success:
        for listing in new_above_threshold:
            state.mark_notified(listing.url)
        print(f"Email sent with {len(new_above_threshold)} new listings (score >= {threshold})")
        return len(new_above_threshold)
    
    return 0


def parse_args():
    parser = argparse.ArgumentParser(description='Multi-config Craigslist Runner')
    parser.add_argument('--configs', nargs='+',
                       help='Config files to process')
    parser.add_argument('--configs-file',
                       help='YAML file containing list of configs (with "configs" key)')
    parser.add_argument('--fetch', type=int, nargs='?', const=-1, default=None,
                       help='Max new listings per config (default: unlimited)')
    parser.add_argument('--email', action='store_true',
                       help='Send email notifications for new high-scoring listings')
    parser.add_argument('--clear-notified', action='store_true',
                       help='Clear notified state before running')
    parser.add_argument('--skip-dedup', action='store_true',
                       help='Skip duplicate filtering')
    return parser.parse_args()


def main():
    args = parse_args()
    
    if not args.configs and not args.configs_file:
        print("Error: Must specify --configs or --configs-file")
        return 1
    
    config_paths = []
    if args.configs:
        for c in args.configs:
            config_paths.append(Path(__file__).parent / c)
    elif args.configs_file:
        configs_file = Path(__file__).parent / args.configs_file
        config_paths = [Path(__file__).parent / c for c in load_configs_list(configs_file)]
    
    state = RunnerState(Path(__file__).parent / "data" / "runner_state.json")
    
    if args.clear_notified:
        print("Clearing notified state...")
        state.data["notified_urls"] = []
        state.save()
    
    fetcher_config = FetcherConfig(delay_ms=5000, max_retries=3)
    fetcher = create_fetcher(fetcher_config, mode="live")
    
    total_new = 0
    total_notified = 0
    
    start_time = datetime.now()
    
    for config_path in config_paths:
        try:
            new_count, notified_count = run_config(config_path, state, args, fetcher, args)
            total_new += new_count
            total_notified += notified_count
        except Exception as e:
            print(f"Error processing {config_path}: {e}")
            import traceback
            traceback.print_exc()
    
    state.last_run = datetime.now().isoformat()
    state.save()
    
    print(f"\n{'='*60}")
    print(f"Runner complete: {total_new} new listings, {total_notified} emailed")
    print(f"Next run: cron or manual restart")
    print('='*60)
    
    return 0


if __name__ == "__main__":
    sys.exit(main())