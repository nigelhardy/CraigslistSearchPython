# Craigslist Scraper v2 - Parser Architecture

## New Structure

### Parsers Module (`parsers/`)
- **`base_parser.py`**: Abstract `ListingParser` class that defines the parser interface
- **`craigslist_parser.py`**: `CraigslistListingParser` that extracts all fields from Craigslist HTML
- **`__init__.py`**: Module exports

### Tools (`tools/`)
- **`collect_test_data.py`**: Fetches listings from live Craigslist and saves HTML for testing

### Test Configuration
- **`test_config.yaml`**: Copy of config with `test_subaru_forester_listings.json` as storage

### Tests (`tests/`)
- **`test_parsers.py`**: Tests parser using FileFetcher

## Usage

### 1. Collect Test Data (Run Once)
```bash
cd craigslist_scraper_v2
python tools/collect_test_data.py --config simple_config_v2.yaml --count 10
```

This saves HTML files to `test_data/`:
- `2002-subaru-forester-manual_001.html`
- `manifest.json` (maps URLs to files)

### 2. Test the Parser
```bash
python tests/test_parsers.py
```

### 3. Run in Test Mode
```bash
python main.py --mode test --config test_config.yaml --fetch 5
```

### 4. Run in Live Mode (Production)
```bash
python main.py --mode live --config simple_config_v2.yaml --fetch 10
```

## Architecture Flow

```
main.py
    │
    ├── CraigslistFetcher ──→ HTTP GET ──→ Craigslist
    │                              │
    │                              ▼
    │                       BeautifulSoup
    │                              │
    └── CraigslistListingParser ──┘
                   │
                   ▼
            VehicleListing
```

**Test Mode:**
```
main.py
    │
    ├── FileFetcher ──→ Load HTML from disk
    │           │
    │           ▼
    │    BeautifulSoup
    │           │
    └── CraigslistListingParser
                   │
                   ▼
            VehicleListing
```

## Vehicle Fields Parsed

From Craigslist HTML attributes:
- `mileage` / `odometer`: Mileage
- `transmission`: Transmission type
- `title status`: Title status
- `year`: Year (also extracts from title if not in attrs)
- `vin`: VIN number
- `condition`: Vehicle condition
- `make`: Make (from `auto_make_model` attr)
- `model`: Model (from `auto_make_model` attr)

## Key Design Decisions

1. **Separation of Concerns**: Fetcher gets HTML, Parser converts to Listing
2. **Testable**: FileFetcher allows testing without network
3. **Extensible**: Easy to add FacebookFetcher + FacebookParser later
4. **Complete**: All VehicleListing fields are populated when available in HTML
