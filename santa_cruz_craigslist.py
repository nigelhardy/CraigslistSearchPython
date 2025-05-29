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

from calc_scores import calculate_scores
from config import Config, get_search_config, get_data_file_path, get_unwanted_file_path
from logger_config import setup_logger
from results_to_html import results_to_html


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
    
    def save_results(self, search_type: str, results: List[Dict]) -> bool:
        """
        Save listing results to file.
        
        Args:
            search_type: Type of search (SC or LG)
            results: List of listing dictionaries to save
            
        Returns:
            True if saved successfully, False otherwise
        """
        file_path = get_data_file_path(search_type)
        try:
            with open(file_path, 'wb') as file:
                pickle.dump(results, file)
            self.logger.info(f"Saved {len(results)} results to {file_path}")
            return True
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
        Fetch new listings from Craigslist.
        
        Args:
            search_type: Type of search (SC or LG)
            max_fetches: Maximum number of listings to fetch (-1 for no limit)
            existing_urls: URLs to skip (already processed)
            wait_ms: Milliseconds to wait between requests
            
        Returns:
            List of new listing dictionaries
        """
        config = get_search_config(search_type)
        self.logger.info(f"Starting {config.name} search with filters: {config.filters}")
        
        # Create and execute search
        search = cs.Search(
            query=config.query,
            city=config.city,
            category=config.category
        )
        
        status = search.fetch(params=config.filters)
        if status != 200:
            raise Exception(f"Unable to fetch search with status {status}")
        
        self.logger.info(f"Found {len(search.ads)} listings from search")
        
        return self._process_search_results(
            search.ads, max_fetches, existing_urls, wait_ms
        )
    
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


class CraigslistRentalScraper:
    """Main application class for the Craigslist rental scraper."""
    
    def __init__(self):
        """Initialize the main application."""
        self.logger = setup_logger(__name__)
        self.scraper = ListingScraper()
        self.data_manager = DataManager()
        self.email_service = self._setup_email_service()
    
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
            
            # Score and filter listings
            sorted_listings, unwanted_listings = calculate_scores(new_listings, args.type) # type: ignore
            
            # Remove duplicates
            unique_listings, duplicate_urls = self.scraper.remove_duplicates(sorted_listings)
            
            # Update unwanted URLs
            new_unwanted_urls = (
                unwanted_urls + 
                [listing['url'] for listing in unwanted_listings] + 
                duplicate_urls
            )
            
            # Generate output
            html_content = results_to_html(unique_listings)
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            
            # Save data if fetching new results
            if args.fetch:
                combined_results = unique_listings + previous_results
                self.data_manager.save_results(args.type, combined_results)
                self.data_manager.save_unwanted_urls(args.type, new_unwanted_urls)
            
            # Handle output options
            self._handle_output(args, html_content, timestamp, len(unique_listings))
            
            self.logger.info(f"Processing complete at {timestamp}")
            
        except Exception as e:
            self.logger.error(f"Application error: {e}")
            raise
    
    def _handle_output(self, args: argparse.Namespace, html_content: str, 
                      timestamp: str, num_new_listings: int) -> None:
        """Handle email and display output options."""
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
    
    def _display_results_in_browser(self, html_content: str) -> None:
        """Display results in the default web browser."""
        try:
            with open(Config.HTML_PREVIEW_FILE, 'w', encoding='utf-8') as file:
                file.write(html_content)
            webbrowser.open(Config.HTML_PREVIEW_FILE)
            self.logger.info("Results opened in browser")
        except Exception as e:
            self.logger.error(f"Error displaying results in browser: {e}")


def create_argument_parser() -> argparse.ArgumentParser:
    """Create and configure the command line argument parser."""
    parser = argparse.ArgumentParser(
        description='Professional Craigslist rental scraper with scoring and notifications',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s --fetch --type SC                    # Fetch new Santa Cruz listings
  %(prog)s --fetch --email --type LG           # Fetch Los Gatos listings and email
  %(prog)s --display --type SC                 # Display cached results in browser  
  %(prog)s --test-url "https://..."            # Test scoring for specific URL
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
        '--type', 
        type=str, 
        choices=['SC', 'LG'], 
        default=Config.DEFAULT_SEARCH_TYPE, 
        help='Search area type: SC (Santa Cruz) or LG (Los Gatos)'
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
    
    return parser


def main() -> None:
    """Main entry point for the application."""
    parser = create_argument_parser()
    args = parser.parse_args()
    
    # Setup logging
    logger = setup_logger(__name__, args.log_level)
    logger.info(f"Starting {Config.APP_NAME} v{Config.VERSION}")
    
    try:
        app = CraigslistRentalScraper()
        app.run(args)
    except KeyboardInterrupt:
        logger.info("Application interrupted by user")
    except Exception as e:
        logger.error(f"Unhandled exception: {e}")
        raise


if __name__ == "__main__":
    main()