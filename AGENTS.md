# AGENTS.md - Craigslist Scraper

A Craigslist scraper that searches multiple categories, scores/ranks listings, removes duplicates, and outputs formatted results.

## Running the Application

```bash
# Default search (subaru_forester)
python main.py --fetch

# Use different config
python main.py --config config/forester_parts.yaml --fetch

# Display existing listings without fetching new
python main.py

# Clear storage and fetch fresh
python main.py --fetch --clear

# Save raw HTML for debugging
python main.py --fetch --save-raw
```

## Project Structure

```
.                     # Root: Entry point + core modules
├── main.py           # Main entry point
├── config.py         # Configuration loading (YAML parsing)
├── engine.py         # Search engine (fetches search pages)
├── fetcher.py        # HTTP client with caching
├── ranking.py        # Scoring + duplicate filtering
├── display.py        # HTML output generation
├── storage.py        # JSON persistence
├── models.py         # Data classes

config/               # Configuration files
├── subaru_forester.yaml
├── forester_parts.yaml
└── test_config.yaml

data/                 # State (JSON - gitignored)
├── *.json           # Listing data
└── raw_data/        # Raw HTML cache

outputs/
├── simple_html.py
└── results/         # Generated HTML reports

algorithms/          # Ranking algorithms
├── base_algorithm.py
└── subaru_forester.py

scrapers/            # HTTP clients
└── craigslist_scraper.py

parsers/             # HTML parsers
├── base_parser.py
└── craigslist_parser.py

core/                # Shared utilities
└── config_loader.py

tests/               # Test suite
test_data/           # HTML fixtures for tests
tools/               # One-off scripts
```

## Configuration (YAML)

Config files in `config/` define:
- `query`: Search term
- `categories`: Craigslist categories (cta, pta, etc.)
- `cities`: Cities to search (sfbay, losangeles, etc.)
- `max_pages`: Pages per city
- `storage.filename`: Output JSON file
- `scoring`: List of keyword scoring rules (see existing configs for examples)
- `deduplication`: similarity threshold, max_age_days

## Data Flow

1. `main.py` loads YAML config
2. `engine.py` fetches search result pages from Craigslist
3. `fetcher.py` fetches individual listing details (with caching)
4. `parser.py` extracts data from HTML
5. `ranking.py` applies scoring rules + deduplication
6. `display.py` generates HTML output
7. `storage.py` persists to JSON