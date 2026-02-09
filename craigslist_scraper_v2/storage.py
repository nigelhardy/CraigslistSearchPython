"""Storage module for listing persistence."""
import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Set, Type, Any

from models import Listing, VehicleListing, ListingState


LISTING_TYPE_MAP: Dict[str, Type[Listing]] = {
    "base": Listing,
    "vehicle": VehicleListing,
}


def create_listing_from_dict(data: Dict[str, Any]) -> Listing:
    """Factory function to create correct listing type from dictionary."""
    listing_type = data.get('listing_type', 'base')
    listing_class = LISTING_TYPE_MAP.get(listing_type, Listing)
    
    state_name = data.get('state', 'URL_ONLY')
    if isinstance(state_name, str):
        data['state'] = ListingState[state_name]
    
    valid_fields = set(listing_class.__dataclass_fields__.keys())
    filtered_data = {k: v for k, v in data.items() if k in valid_fields}
    
    return listing_class(**filtered_data)


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
                listing = create_listing_from_dict(listing_data)
                self._listings[listing.url] = listing
            
            print(f"📂 Loaded {len(self._listings)} listings from storage")
        except Exception as e:
            print(f"⚠️  Error loading storage: {e}")
            self._listings = {}
    
    def save(self) -> None:
        """Save listings to storage file."""
        try:
            data = {
                'listings': [listing.to_dict() for listing in self._listings.values()],
                'last_updated': datetime.now().isoformat(),
                'total_count': len(self._listings)
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
        if listing.url in self._listings:
            return False
        
        if listing.first_seen is None:
            listing.first_seen = datetime.now().isoformat()
        
        listing.last_updated = datetime.now().isoformat()
        self._listings[listing.url] = listing
        return True
    
    def get_all_listings(self) -> List[Listing]:
        return list(self._listings.values())
    
    def clear(self) -> None:
        self._listings = {}
        if self.storage_path.exists():
            self.storage_path.unlink()
        print("🗑️  Storage cleared")
