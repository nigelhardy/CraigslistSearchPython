"""Listing data models."""
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional, Tuple


class ListingState(Enum):
    URL_ONLY = auto()
    HTML_PARSED = auto()
    RANKED = auto()


@dataclass
class Listing:
    url: str
    title: str
    price: Optional[int]
    location: str
    city: str
    category: str
    
    state: ListingState = field(default=ListingState.URL_ONLY)
    description: Optional[str] = None
    posted_date: Optional[str] = None
    images: List[str] = field(default_factory=list)
    
    score: float = field(default=0.0)
    score_breakdown: Dict[str, float] = field(default_factory=dict)
    score_reasons: List[str] = field(default_factory=list)
    
    first_seen: Optional[str] = None
    last_updated: Optional[str] = None
    listing_type: str = field(default="base")
    
    def to_dict(self) -> Dict[str, Any]:
        data = asdict(self)
        data['state'] = self.state.name
        return data
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Listing':
        state_name = data.get('state', 'URL_ONLY')
        if isinstance(state_name, str):
            data['state'] = ListingState[state_name]
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class VehicleListing(Listing):
    mileage: Optional[int] = None
    transmission: Optional[str] = None
    title_status: Optional[str] = None
    vin: Optional[str] = None
    condition: Optional[str] = None
    year: Optional[int] = None
    make: Optional[str] = None
    model: Optional[str] = None
    
    def __post_init__(self):
        if self.listing_type == "base":
            self.listing_type = "vehicle"


@dataclass
class SearchResults:
    """Container for search results organized by city/category combinations."""
    
    # Mapping of (city, category) tuples to lists of listings
    listings_by_combo: Dict[Tuple[str, str], List[Listing]] = field(default_factory=dict)
    
    # Track failures per combination
    failure_counts: Dict[Tuple[str, str], int] = field(default_factory=dict)
    
    # Track which combinations were exhausted (no more pages)
    exhausted_combos: set[Tuple[str, str]] = field(default_factory=set)
    
    def add_listings(self, city: str, category: str, listings: List[Listing]) -> None:
        """Add listings for a specific city/category combination."""
        combo = (city, category)
        if combo not in self.listings_by_combo:
            self.listings_by_combo[combo] = []
        self.listings_by_combo[combo].extend(listings)
    
    def increment_failure(self, city: str, category: str) -> None:
        """Increment failure count for a specific city/category combination."""
        combo = (city, category)
        if combo not in self.failure_counts:
            self.failure_counts[combo] = 0
        self.failure_counts[combo] += 1
    
    def mark_exhausted(self, city: str, category: str) -> None:
        """Mark a city/category combination as exhausted (no more pages)."""
        combo = (city, category)
        self.exhausted_combos.add(combo)
    
    def get_listings(self, city: str, category: str) -> List[Listing]:
        """Get listings for a specific city/category combination."""
        combo = (city, category)
        return self.listings_by_combo.get(combo, [])
    
    def get_all_listings(self) -> List[Listing]:
        """Get all listings flattened into a single list."""
        all_listings = []
        for combo_listings in self.listings_by_combo.values():
            all_listings.extend(combo_listings)
        return all_listings
    
    def get_all_urls(self) -> List[str]:
        """Get all URLs flattened into a single list."""
        return [listing.url for listing in self.get_all_listings()]
    
    def get_combo_count(self) -> int:
        """Get the number of city/category combinations processed."""
        return len(self.listings_by_combo)
    
    def get_total_count(self) -> int:
        """Get the total number of listings across all combinations."""
        return len(self.get_all_listings())
    
    def should_abort_combo(self, city: str, category: str, failure_tolerance: int) -> bool:
        """Check if we should abort a combination due to too many failures."""
        combo = (city, category)
        return self.failure_counts.get(combo, 0) >= failure_tolerance
    
    def get_summary(self) -> str:
        """Get a formatted summary of the search results."""
        lines = ["✅ Search Results Summary:"]
        total_count = 0
        
        for (city, category), listings in self.listings_by_combo.items():
            count = len(listings)
            total_count += count
            failure_count = self.failure_counts.get((city, category), 0)
            exhausted = (city, category) in self.exhausted_combos
            
            status = "✅" if exhausted else "📄"
            failure_info = f" ({failure_count} failures)" if failure_count > 0 else ""
            
            lines.append(f"   {status} {city}/{category}: {count} listings{failure_info}")
        
        lines.append(f"📊 Total: {total_count} listings across {len(self.listings_by_combo)} combinations")
        return "\n".join(lines)
