"""
Professional Craigslist rental scraper with scoring and email notifications.

This application searches for rental listings, scores them based on configurable criteria,
and sends email notifications for new high-scoring listings.
"""

import argparse
import os
import pickle
import smtplib
import time
import webbrowser
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText
from pathlib import Path
from typing import Dict, List, Optional, Tuple

import craigslistscraper as cs
from dotenv import load_dotenv
from Levenshtein import ratio

from config import Config, get_search_config, get_data_file_path, get_unwanted_file_path
from logger_config import setup_logger
from ranking_system import RankingAlgorithmRegistry
from plugin_manager import initialize_ranking_algorithms


class EmailService:
    """Handles email operations for sending listing notifications."""
    
    def __init__(self, sender_email: str, receiver_email: str, app_password: str):
        """
        Initialize email service with credentials.
        
        Args:
            sender_email: Email address to send from
            receiver_email: Email address to send to  
            app_password: Application password for authentication
        """
        self.sender_email = sender_email
        self.receiver_email = receiver_email
        self.app_password = app_password
        self.logger = setup_logger(f"{__name__}.EmailService")
    
    def send_listing_email(self, html_content: str, timestamp: str) -> bool:
        """
        Send email with listing results.
        
        Args:
            html_content: HTML content to send
            timestamp: Timestamp for email subject
            
        Returns:
            True if email sent successfully, False otherwise
        """
        try:
            msg = MIMEMultipart()
            msg['From'] = self.sender_email
            msg['To'] = self.receiver_email
            msg['Subject'] = Config.EMAIL_SUBJECT_TEMPLATE.format(timestamp)
            msg.attach(MIMEText(html_content, 'html'))
            
            with smtplib.SMTP(Config.SMTP_SERVER, Config.SMTP_PORT) as server:
                server.starttls()
                server.login(self.sender_email, self.app_password)
                server.sendmail(self.sender_email, self.receiver_email, msg.as_string())
            
            self.logger.info("Email sent successfully")
            return True
            
        except Exception as e:
            self.logger.error(f"Failed to send email: {e}")
            return False


class DataManager:
    """Manages data persistence and retrieval for listings."""
    
    def __init__(self):
        """Initialize data manager."""
        self.logger = setup_logger(f"{__name__}.DataManager")
    
    def load_previous_results(self, search_type: str) -> List[Dict]:
        """
        Load previously saved listing results.
        
        Args:
            search_type: Type of search (SC or LG)
            
        Returns:
            List of previous listing dictionaries
        """
        file_path = get_data_file_path(search_type)
        if not Path(file_path).exists():
            self.logger.info(f"No previous results found at {file_path}")
            return []
        
        try:
            with open(file_path, 'rb') as file:
                results = pickle.load(file)
            self.logger.info(f"Loaded {len(results)} previous results from {file_path}")
            return results
        except Exception as e:
            self.logger.error(f"Error loading previous results: {e}")
            return []
    
    def load_unwanted_urls(self, search_type: str) -> List[str]:
        """
        Load URLs of unwanted listings to skip.
        
        Args:
            search_type: Type of search (SC or LG)
            
        Returns:
            List of unwanted URLs
        """
        file_path = get_unwanted_file_path(search_type)
        if not Path(file_path).exists():
            self.logger.info(f"No unwanted URLs found at {file_path}")
            return []
        
        try:
            with open(file_path, 'rb') as file:
                urls = pickle.load(file)
            self.logger.info(f"Loaded {len(urls)} unwanted URLs from {file_path}")
            return urls
        except Exception as e:
            self.logger.error(f"Error loading unwanted URLs: {e}")
            return []
    
    def save_results(self, search_type: str, results: List[Dict], save_all: bool = True) -> bool:
        """
        Save listing results to file.
        
        Args:
            search_type: Type of search (SC or LG)
            results: List of listing dictionaries to save
            save_all: Whether to save all results (True) or only positive results (False)
            
        Returns:
            True if saved successfully, False otherwise
        """
        file_path = get_data_file_path(search_type)
        
        # Choose filename based on save_all flag
        if save_all:
            file_path = file_path.replace('.pkl', '_all.pkl')
        
        try:
            with open(file_path, 'wb') as file:
                pickle.dump(results, file)
            
            file_type = "all results" if save_all else "positive results only"
            self.logger.info(f"Saved {len(results)} results ({file_type}) to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
            return False
        except Exception as e:
            self.logger.error(f"Error saving results: {e}")
            return False
    
    def save_unwanted_urls(self, search_type: str, urls: List[str]) -> bool:
        """
        Save unwanted URLs to file.
        
        Args:
            search_type: Type of search (SC or LG)
            urls: List of unwanted URLs to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        file_path = get_unwanted_file_path(search_type)
        try:
            with open(file_path, 'wb') as file:
                pickle.dump(urls, file)
            self.logger.info(f"Saved {len(urls)} unwanted URLs to {file_path}")
            return True
        except Exception as e:
            self.logger.error(f"Error saving unwanted URLs: {e}")
            return False


class ListingScraper:
    """Handles scraping and processing of Craigslist listings."""
    
    def __init__(self):
        """Initialize the scraper."""
        self.logger = setup_logger(f"{__name__}.ListingScraper")
        self.data_manager = DataManager()
    
    def fetch_new_listings(
        self, 
        search_type: str, 
        max_fetches: int, 
        existing_urls: List[str], 
        wait_ms: int
    ) -> List[Dict]:
        """
        Fetch new listings from Craigslist across multiple categories and areas.
        
        Args:
            search_type: Type of search (SC, LG, E39_PARTS, etc.)
            max_fetches: Maximum number of listings to fetch (-1 for no limit)
            existing_urls: URLs to skip (already processed)
            wait_ms: Milliseconds to wait between requests
            
        Returns:
            List of new listing dictionaries
        """
        config = get_search_config(search_type)
        self.logger.info(f"Starting {config.name} search with filters: {config.filters}")
        self.logger.info(f"Searching categories: {config.categories}")
        
        # Define multi-area search strategy for Subaru parts and cars
        if search_type in ["SUBARU_FORESTER_BRAKES", "SUBARU_FORESTER_SUSPENSION", "SUBARU_PERFORMANCE", "SUBARU_FORESTER"]:
            cities = self._get_multi_area_cities(search_type)
        else:
            cities = [config.city]  # Single city for other search types
        
        all_ads = []
        
        for city in cities:
            city_ads = []
            self.logger.info(f"Searching in {city}...")
            
            # Search each category
            for category in config.categories:
                self.logger.info(f"Searching {city} category: {category}")
                
                # Create and execute search for this category and city
                search = cs.Search(
                    query=config.query,
                    city=city,
                    category=category
                )
                
                status = search.fetch(params=config.filters)
                if status != 200:
                    self.logger.warning(f"Unable to fetch {city} category {category} with status {status}")
                    continue
                
                self.logger.info(f"Found {len(search.ads)} listings in {city} category {category}")
                city_ads.extend(search.ads)
            
            # Store city info for later use in scoring
            for ad in city_ads:
                ad.search_city = city
            
            all_ads.extend(city_ads)
            
            # Break early if we hit max_fetches
            if max_fetches != -1 and len(all_ads) >= max_fetches:
                self.logger.info(f"Reached max fetches limit: {max_fetches}")
                break
        
        self.logger.info(f"Total listings found across all areas: {len(all_ads)}")
        
        return self._process_search_results(
            all_ads, max_fetches, existing_urls, wait_ms
        )
    
    def _get_multi_area_cities(self, search_type: str) -> List[str]:
        """
        Get list of cities for multi-area Subaru parts searches.
        
        Args:
            search_type: Type of search
            
        Returns:
            List of Craigslist city codes in priority order
        """
        # Priority order: Local -> Regional -> National
        return [
            "sfbay",        # Primary: SF Bay Area (local preference)
            "losangeles",    # Secondary: SoCal
            "portland",      # Secondary: Pacific Northwest  
            "seattle",       # Secondary: Pacific Northwest
            "sacramento",    # Secondary: Northern California
            "denver",        # Tertiary: Mountain region
            "phoenix",       # Tertiary: Southwest
            "lasvegas"       # Tertiary: Southwest
        ]
    
    def _process_search_results(
        self, 
        ads: List, 
        max_fetches: int, 
        existing_urls: List[str], 
        wait_ms: int
    ) -> List[Dict]:
        """
        Process search results and fetch detailed information.
        
        Args:
            ads: List of ad objects from search
            max_fetches: Maximum number to process
            existing_urls: URLs to skip
            wait_ms: Wait time between requests
            
        Returns:
            List of processed listing dictionaries
        """
        results = []
        fails = 0
        count = 0
        
        for ad in ads:
            # Check stopping conditions
            if self._should_stop_processing(count, fails, max_fetches):
                self.logger.info("Stopping: max fetches or fails reached")
                break
            
            # Skip existing URLs
            if ad.url in existing_urls:
                continue
            
            self.logger.info(f"Processing new URL: {ad.url}")
            count += 1
            
            # Rate limiting
            if wait_ms > 0:
                time.sleep(wait_ms / 1000.0)
            
            # Fetch detailed ad information
            listing_data = self._fetch_ad_details(ad)
            if listing_data:
                # Add city information for geographic preference scoring
                listing_data['search_city'] = getattr(ad, 'search_city', None)
                results.append(listing_data)
            else:
                fails += 1
        
        self.logger.info(f"Successfully processed {len(results)} new listings")
        return results
    
    def _should_stop_processing(self, count: int, fails: int, max_fetches: int) -> bool:
        """Check if processing should stop based on limits."""
        if max_fetches != -1 and count >= max_fetches:
            return True
        if fails > Config.MAX_CONSECUTIVE_FAILS:
            return True
        return False
    
    def _fetch_ad_details(self, ad) -> Optional[Dict]:
        """
        Fetch detailed information for a single ad.
        
        Args:
            ad: Ad object to fetch details for
            
        Returns:
            Dictionary with ad details or None if failed
        """
        try:
            status = ad.fetch()
            if status != 200:
                self.logger.warning(f"Failed to fetch ad '{ad.title}' with status {status}: {ad.url}")
                return None
            
            return ad.to_dict()
            
        except Exception as e:
            self.logger.error(f"Exception fetching ad {ad.url}: {e}")
            return None
    
    def remove_duplicates(self, listings: List[Dict]) -> Tuple[List[Dict], List[str]]:
        """
        Remove duplicate listings based on title and description similarity.
        
        Args:
            listings: List of listing dictionaries
            
        Returns:
            Tuple of (unique_listings, duplicate_urls_to_skip)
        """
        unique_listings = []
        duplicate_urls = []
        
        for listing in listings:
            if self._is_duplicate(listing, unique_listings):
                self.logger.info(f"Skipping duplicate: {listing['title']}")
                duplicate_urls.append(listing['url'])
            else:
                unique_listings.append(listing)
        
        self.logger.info(f"Removed {len(duplicate_urls)} duplicates")
        return unique_listings, duplicate_urls
    
    def _is_duplicate(self, listing: Dict, existing_listings: List[Dict]) -> bool:
        """Check if a listing is a duplicate of existing ones."""
        for existing in existing_listings:
            # Check title similarity
            if (len(listing['title']) > Config.MIN_TITLE_LENGTH_FOR_SIMILARITY and
                ratio(listing['title'], existing['title']) > Config.SIMILARITY_THRESHOLD_TITLE):
                return True
            
            # Check description similarity  
            if (len(listing['description']) > Config.MIN_DESC_LENGTH_FOR_SIMILARITY and
                ratio(listing['description'], existing['description']) > Config.SIMILARITY_THRESHOLD_DESC):
                return True
        
        return False


class CraigslistScraper:
    """Main application class for the Craigslist scraper."""
    
    def __init__(self):
        """Initialize the main application."""
        self.logger = setup_logger(__name__)
        self.scraper = ListingScraper()
        self.data_manager = DataManager()
        self.email_service = self._setup_email_service()
        
        # Initialize ranking algorithms
        initialize_ranking_algorithms()
    
    def _setup_email_service(self) -> Optional[EmailService]:
        """Set up email service if credentials are available."""
        load_dotenv()
        
        sender_email = os.getenv(Config.ENV_SENDER_EMAIL)
        receiver_email = os.getenv(Config.ENV_RECEIVER_EMAIL)
        app_password = os.getenv(Config.ENV_EMAIL_PASSWORD)

        if sender_email is None or receiver_email is None or app_password is None:
            self.logger.warning("Email credentials not found in environment variables")
            return None

        return EmailService(sender_email, receiver_email, app_password)
    
    def test_url(self, url: str) -> None:
        """Test ranking/scoring for a specific URL."""
        self.logger.info(f"Testing URL: {url}")
        try:
            ad = cs.fetch_ad(url)
            self.logger.info(f"Ad attributes: {ad.attributes}")
        except Exception as e:
            self.logger.error(f"Error testing URL: {e}")
    
    def run(self, args: argparse.Namespace) -> None:
        """
        Run the main application logic.
        
        Args:
            args: Command line arguments
        """
        if args.test_url:
            self.test_url(args.test_url)
            return
        
        try:
            # Load existing data
            previous_results = self.data_manager.load_previous_results(args.type)
            unwanted_urls = self.data_manager.load_unwanted_urls(args.type)
            existing_urls = [r['url'] for r in previous_results] + unwanted_urls
            
            # Get new listings or use cached results
            if args.fetch:
                new_listings = self.scraper.fetch_new_listings(
                    args.type, args.max_fetches, existing_urls, args.wait_ms
                )
            else:
                new_listings = previous_results
                self.logger.info("Using cached results (no fetch requested)")
            
            # Score and filter listings using ranking algorithm
            ranking_algorithm = RankingAlgorithmRegistry.get_algorithm(args.type)
            ranking_result = ranking_algorithm.calculate_scores(new_listings)
            sorted_listings = ranking_result.sorted_listings
            unwanted_listings = ranking_result.unwanted_listings
            
            # Remove duplicates
            unique_listings, duplicate_urls = self.scraper.remove_duplicates(sorted_listings)
            
            # Update unwanted URLs
            new_unwanted_urls = (
                unwanted_urls + 
                [listing['url'] for listing in unwanted_listings] + 
                duplicate_urls
            )
            
            # Generate output using algorithm-specific HTML formatting
            # For HTML, always show all results when --show-all flag is used
            if getattr(args, 'show_all', False):
                # Show ALL results (positive + negative)
                display_listings = unique_listings + unwanted_listings
                # Sort all by score (highest to lowest)
                display_listings.sort(key=lambda x: x.get('score', 0), reverse=True)
            else:
                # Default: Show only positive results for clean HTML output
                display_listings = unique_listings
            
            html_content = ranking_algorithm.format_results_to_html(display_listings)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Save data if fetching new results
            if args.fetch:
                combined_results = unique_listings + previous_results
                self.data_manager.save_results(args.type, combined_results, save_all=getattr(args, 'save_all_results', True))
                self.data_manager.save_unwanted_urls(args.type, new_unwanted_urls)
            
            # Handle output options
            self._handle_output(args, html_content, timestamp, len(unique_listings), ranking_algorithm, unique_listings)
            
            self.logger.info(f"Processing complete at {timestamp}")
            
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            raise
    
    def _handle_output(self, args: argparse.Namespace, html_content: str, 
                      timestamp: str, num_new_listings: int, ranking_algorithm, listings: List[Dict]) -> None:
        """Handle email, display, and console output options."""
        # Send email if requested and there are new listings
        if args.email and num_new_listings > 0 and self.email_service:
            self.email_service.send_listing_email(html_content, timestamp)
        elif args.email and not self.email_service:
            self.logger.warning("Email requested but email service not available")
        elif args.email and num_new_listings == 0:
            self.logger.info("No email sent - no new listings found")
        
        # Display in browser if requested
        if args.display:
            self._display_results_in_browser(html_content)
        
        # Display in console if requested
        if args.console:
            self._display_results_in_console(ranking_algorithm, listings, show_all=getattr(args, 'show_all', False))
    
    def _display_results_in_browser(self, html_content: str) -> None:
        """Display results in the default web browser."""
        try:
            with open(Config.HTML_PREVIEW_FILE, 'w', encoding='utf-8') as file:
                file.write(html_content)
            webbrowser.open(Config.HTML_PREVIEW_FILE)
            self.logger.info("Results opened in browser")
        except Exception as e:
            self.logger.error(f"Error displaying results in browser: {e}")
    
    def _display_results_in_console(self, ranking_algorithm, listings: List[Dict], show_all: bool = False) -> None:
        """Display results in console with nicely formatted table."""
        try:
            # Filter listings for console display based on show_all flag
            if show_all:
                display_listings = listings  # Show all
            else:
                # Show only positive scoring listings
                min_threshold = ranking_algorithm.get_minimum_score_threshold()
                display_listings = [l for l in listings if l.get('score', 0) > min_threshold]
            
            console_output = ranking_algorithm.format_results_to_console(display_listings)
            
            print("\n" + "="*80)
            print(f"🔍 {ranking_algorithm.search_type} SEARCH RESULTS")
            if show_all:
                print("="*80)
                print("🔧 Showing ALL results (positive and negative scores)")
                print("📊 Use --show-all flag to see scoring breakdown")
            else:
                print("="*80)
                print("📋 Showing positive results only")
                print("🔧 Use --show-all flag to see negative results and scoring breakdown")
            
            print("="*80)
            print(console_output)
            print("="*80)
        except Exception as e:
            self.logger.error(f"Error displaying results in console: {e}")
            print("Error displaying console results. Check logs for details.")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the command line argument parser."""
    parser = argparse.ArgumentParser(
        description='Professional Craigslist scraper with ranking and notifications',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --fetch --type SC                    # Fetch new Santa Cruz apartment listings
  %(prog)s --fetch --email --type LG           # Fetch Los Gatos listings and email
  %(prog)s --fetch --type E39_PARTS             # Fetch BMW E39 parts listings
  %(prog)s --display --type SC                 # Display cached results in browser  
  %(prog)s --console --type SC                 # Display results in formatted console table
  %(prog)s --fetch --console --type E39_PARTS  # Fetch and show in console (debugging)
  %(prog)s --test-url "https://..."            # Test scoring for specific URL
  %(prog)s --list-types                        # List available search types
        """
    )
    
    parser.add_argument(
        '--fetch', 
        action='store_true', 
        help='Fetch new data from Craigslist'
    )
    parser.add_argument(
        '--email', 
        action='store_true', 
        help='Send email with results (requires .env file with credentials)'
    )
    parser.add_argument(
        '--display', 
        action='store_true', 
        help='Display HTML results in default web browser'
    )
    parser.add_argument(
        '--console',
        action='store_true',
        help='Display formatted results table in console/terminal (great for debugging)'
    )
    parser.add_argument(
        '--type', 
        type=str, 
        choices=Config.AVAILABLE_SEARCH_TYPES, 
        default=Config.DEFAULT_SEARCH_TYPE, 
        help='Search type: SC (Santa Cruz apartments), LG (Los Gatos apartments), E39_PARTS (BMW E39 parts)'
    )
    parser.add_argument(
        '--list-types',
        action='store_true',
        help='List all available search types and exit'
    )
    parser.add_argument(
        '--max_fetches', 
        type=int, 
        default=Config.DEFAULT_MAX_FETCHES, 
        help='Maximum number of new listings to fetch (-1 for no limit)'
    )
    parser.add_argument(
        '--wait_ms', 
        type=int, 
        default=Config.DEFAULT_WAIT_MS, 
        help='Milliseconds to wait between requests (-1 for no wait)'
    )
    parser.add_argument(
        '--test-url', 
        type=str, 
        help='Test ranking/scoring for a specific Craigslist URL'
    )
    parser.add_argument(
        '--log-level',
        type=str,
        choices=['DEBUG', 'INFO', 'WARNING', 'ERROR'],
        default='INFO',
        help='Set logging level'
    )
    parser.add_argument(
        '--save-all-results',
        action='store_true',
        default=True,
        help='Save ALL results to file (default: True). Set to False to save only positive results'
    )
    parser.add_argument(
        '--show-all',
        action='store_true',
        default=False,
        help='Show ALL results in console including negative scores (default: False)'
    )
    
    return parser


def main() -> None:
    """Main entry point for the application."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Handle list-types command
    if getattr(args, 'list_types', False):
        initialize_ranking_algorithms()
        print("Available search types:")
        for search_type, config in Config.SEARCH_CONFIGS.items():
            print(f"  {search_type:12} - {config.description}")
        return
    
    # Setup logging
    logger = setup_logger(__name__, args.log_level)
    logger.info(f"Starting {Config.APP_NAME} v{Config.VERSION}")
    
    try:
        app = CraigslistScraper()
        app.run(args)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        raise


if __name__ == "__main__":
    main()