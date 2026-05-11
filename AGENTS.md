# AGENTS.md - Craigslist Scraper

A Craigslist scraper that searches multiple categories, scores/ranks listings, removes duplicates, and outputs formatted results.

## Workflows

### Develop Workflow (iterate on parser/ranker without fetching)

```bash
# 1. Fetch fresh data and save raw HTML (do this once to get sample data)
python main.py --config config/honda_ridgeline.yaml --fetch --save-raw --clear

# 2. Parse saved HTML files into storage (extracts real URLs from meta tags)
python main.py --config config/honda_ridgeline.yaml --parse-raw

# 3. Display current ranking
python main.py --config config/honda_ridgeline.yaml --display

# 4. Edit config/scoring rules, then re-display
python main.py --config config/honda_ridgeline.yaml --display
```

**Note:** The saved raw HTML contains `og:url` meta tags with the original Craigslist URLs. When parsing with `--parse-raw`, these real URLs are extracted and used as the primary link, so results show actual Craigslist links even when using saved data.

### Production Workflow (fetch live data)

```bash
# Fetch new listings (unlimited)
python main.py --config config/honda_ridgeline.yaml --fetch

# Fetch specific number per city/category
python main.py --config config/honda_ridgeline.yaml --fetch 5

# Fetch and save raw HTML for later analysis
python main.py --config config/honda_ridgeline.yaml --fetch --save-raw

# Clear storage and re-fetch
python main.py --config config/honda_ridgeline.yaml --fetch --clear
```

### Parse-Only Workflow

```bash
# Re-parse existing raw HTML files (after fixing parser)
python main.py --config config/honda_ridgeline.yaml --parse-raw --clear
```

### Multi-config / Cron Runner

`runner.py` fetches all configs listed in `config/configs.yaml` in one pass — designed to run every 15 min via cron.

```bash
# Run all configs defined in config/configs.yaml (with email notifications)
python runner.py --configs-file config/configs.yaml --email --fetch 20

# Run specific configs
python runner.py --configs config/honda_ridgeline.yaml config/subaru_forester.yaml --fetch 20

# Set up cron (every 15 min, logs to logs/)
# */15 * * * * /path/to/run.sh >> /path/to/logs/scraper.log 2>&1
./run.sh
```

Edit `config/configs.yaml` to add/remove configs from the rotation:
```yaml
configs:
  - config/subaru_forester.yaml
  - config/honda_ridgeline.yaml
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
| `--email` | Send email notification for high-scoring listings |

## Project Structure

```
.                     # Root: Entry point + core modules
├── main.py           # Main entry point (single config)
├── runner.py         # Multi-config runner (for cron / batch runs)
├── run.sh            # Cron wrapper (calls runner.py with configs.yaml)
├── config.py         # Configuration loading (YAML parsing)
├── engine.py         # Search engine (fetches search pages)
├── fetcher.py        # HTTP client with caching
├── ranking.py        # Scoring + duplicate filtering
├── display.py        # HTML output generation
├── storage.py        # JSON persistence
├── models.py         # Data classes
├── notifications.py  # Email notification service

config/               # Configuration files
├── configs.yaml          # Master list for multi-config runner
├── honda_ridgeline.yaml
├── subaru_forester.yaml
├── forester_parts.yaml
└── test_config.yaml

data/                 # State (JSON - gitignored)
├── *.json           # Listing data
└── raw_data/        # Raw HTML cache (gitignored)
    └── <config>/    # One subdir per config
        └── *.html

raw_data/             # Legacy raw HTML cache location (root-level)

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
- `listing_type`: `"vehicle"` for cars/trucks; `"base"` for parts/general
- `storage.filename`: Output JSON file
- `scoring`: List of keyword scoring rules (see existing configs for examples)
- `price_rules`: List of price-based scoring rules (`above`, `below`, `no_price` + `points`)
- `deduplication`: similarity threshold, max_age_days
- `notifications`: enabled, min_score, max_listings

## Email Notifications

Configure in `.env` (create if not exists):
```
EMAIL_SENDER_ADDRESS=your@gmail.com
EMAIL_RECEIVER_ADDRESS=recipient@example.com
EMAIL_PASSWORD=your_app_password
```

Then configure in YAML:
```yaml
notifications:
  enabled: true
  min_score: 20   # Only notify for listings scoring >= 20
  max_listings: 20
```

Run with `--email` flag:
```bash
python main.py --config config/subaru_forester.yaml --display --email
```

**Note**: For Gmail, use an [App Password](https://support.google.com/accounts/answer/185833) instead of your regular password.

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
| `runner.py` | Multi-config runner for cron/batch jobs |
| `run.sh` | Cron wrapper — runs all configs in `config/configs.yaml` |
| `config/configs.yaml` | Master config list for runner.py |
| `config/*.yaml` | Defines search params, scoring rules, and price rules |