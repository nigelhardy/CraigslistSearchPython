# AGENTS.md - Craigslist Scraper

A Craigslist scraper that searches multiple categories, scores/ranks listings, removes duplicates, and outputs formatted results.

## Workflows

### Develop Workflow (iterate on parser/ranker without fetching)

```bash
# 1. Fetch fresh data and save raw HTML (do this once to get sample data)
python main.py --config config/subaru_forester.yaml --fetch --save-raw --clear

# 2. Parse saved HTML files into storage (extracts real URLs from meta tags)
python main.py --config config/subaru_forester.yaml --parse-raw

# 3. Display current ranking
python main.py --config config/subaru_forester.yaml --display

# 4. Edit config/scoring rules, then re-display
python main.py --config config/subaru_forester.yaml --display
```

**Note:** The saved raw HTML contains `og:url` meta tags with the original Craigslist URLs. When parsing with `--parse-raw`, these real URLs are extracted and used as the primary link, so results show actual Craigslist links even when using saved data.

### Production Workflow (fetch live data)

```bash
# Fetch new listings (unlimited)
python main.py --config config/subaru_forester.yaml --fetch

# Fetch specific number per city/category
python main.py --config config/subaru_forester.yaml --fetch 5

# Fetch and save raw HTML for later analysis
python main.py --config config/subaru_forester.yaml --fetch --save-raw

# Clear storage and re-fetch
python main.py --config config/subaru_forester.yaml --fetch --clear
```

### Parse-Only Workflow

```bash
# Re-parse existing raw HTML files (after fixing parser)
python main.py --config config/subaru_forester.yaml --parse-raw --clear
```

## Commands

| Command | Description |
|---------|-------------|
| `--config <file>` | **Required.** Config file path |
| `--fetch [N]` | Fetch listings. N = specific count, omit = unlimited |
| `--display` | Display ranked results from existing storage |
| `--parse-raw` | Parse raw HTML files from `data/raw_data/` into storage |
| `--save-raw` | Save raw HTML when fetching |
| `--clear` | Clear storage before operation |
| `--no-dedup` | Skip duplicate filtering (useful for re-parsing same data) |
| `--output <file>` | Output HTML filename |

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
└── raw_data/        # Raw HTML cache (gitignored)
    └── <config>/    # One subdir per config
        └── *.html

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

## Key Files

| File | Purpose |
|------|---------|
| `parsers/craigslist_parser.py` | Extracts data from Craigslist HTML |
| `ranking.py` | Scores listings, filters duplicates |
| `config/*.yaml` | Defines search params and scoring rules |