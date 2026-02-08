"""Listing data models."""
from enum import Enum, auto
from dataclasses import dataclass, field, asdict
from typing import List, Dict, Any, Optional


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
