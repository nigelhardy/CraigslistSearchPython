"""Storage module for persistent listing data management."""
import json
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Any, Set

from models import Listing


class ListingStorage:
    """Manages persistent storage of listings."""
    
    def __init__(self, storage_path: Path):
        self.storage_path = storage_path
        self._listings: Dict[str, Listing] = {}
        self._load()
    
    def _load(self) -> None:
        """Load existing listings from storage file."""
        if not self.storage_path.exists():
            print(f"📂 No existing storage found at {self.storage_path}")
            return
        
        try:
            with open(self.storage_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            for listing_data in data.get('listings', []):
                listing = Listing.from_dict(listing_data)
                
                # Only load listings that have actual data (HTML_PARSED state)
                from models import ListingState
                if listing.state == ListingState.HTML_PARSED:
                    self._listings[listing.url] = listing
                else:
                    # Skip unprocessed listings
                    skipped_count = getattr(self, '_skipped_count', 0) + 1
                    self._skipped_count = skipped_count
            
            loaded_count = len(self._listings)
            skipped_count = getattr(self, '_skipped_count', 0)
            
            if skipped_count > 0:
                print(f"📂 Loaded {loaded_count} processed listings from storage (skipped {skipped_count} unprocessed)")
            else:
                print(f"📂 Loaded {loaded_count} listings from storage")
        except Exception as e:
            print(f"⚠️  Error loading storage: {e}")
            self._listings = {}
    
    def save(self) -> None:
        """Save listings to storage file."""
        try:
            data = {
                'listings': [listing.to_dict() for listing in self._listings.values()],
                'updated_at': datetime.now().isoformat()
            }
            
            self.storage_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.storage_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2, default=str)
            
            print(f"💾 Saved {len(self._listings)} listings to {self.storage_path}")
        except Exception as e:
            print(f"❌ Error saving storage: {e}")
    
    def is_seen(self, url: str) -> bool:
        return url in self._listings
    
    def get_seen_urls(self) -> Set[str]:
        return set(self._listings.keys())
    
    def add_listing(self, listing: Listing) -> bool:
        """Add a listing to storage if not already present and is fully processed."""
        from models import ListingState
        
        # Only save listings that have actual data
        if listing.state != ListingState.HTML_PARSED:
            return False
        
        if listing.url in self._listings:
            return False
        
        if listing.first_seen is None:
            listing.first_seen = datetime.now().isoformat()
        
        listing.last_updated = datetime.now().isoformat()
        self._listings[listing.url] = listing
        return True
    
    def get_all_listings(self) -> List[Listing]:
        return list(self._listings.values())
    
    def get_processed_listings(self) -> List[Listing]:
        """Get only listings that have been fully processed (HTML_PARSED state)."""
        from models import ListingState
        return [listing for listing in self._listings.values() 
                if listing.state == ListingState.HTML_PARSED]
    
    def get_unprocessed_listings(self) -> List[Listing]:
        """Get only listings that haven't been processed (URL_ONLY state)."""
        from models import ListingState
        return [listing for listing in self._listings.values() 
                if listing.state == ListingState.URL_ONLY]
    
    def clear(self) -> None:
        self._listings = {}
        if self.storage_path.exists():
            self.storage_path.unlink()
        print("🗑️  Storage cleared")