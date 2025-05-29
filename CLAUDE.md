# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a Craigslist apartment/rental scraper and scoring system designed to automatically find and rank rental listings based on custom criteria. The main application searches two areas: Santa Cruz (SC) and Los Gatos (LG), scores listings based on location, price, amenities, and other factors, then emails the best results.

## Commands

### Running the Application
```bash
# Fetch new data for Santa Cruz area
python santa-cruz-craigslist.py --fetch --type SC

# Fetch new data for Los Gatos area  
python santa-cruz-craigslist.py --fetch --type LG

# Send email with results (requires .env file with email credentials)
python santa-cruz-craigslist.py --fetch --email --type SC

# Display results in browser
python santa-cruz-craigslist.py --display --type SC

# Test a specific listing URL
python santa-cruz-craigslist.py --test-url "https://sfbay.craigslist.org/scz/apa/d/..."
```

### Dependencies
```bash
pip install -r requirements.txt
```

## Architecture

### Core Components

**santa-cruz-craigslist.py**: Main entry point that orchestrates the entire workflow - fetching, scoring, deduplication, email generation, and data persistence using pickle files.

**craigslistscraper/**: Custom scraping library
- `search.py`: Handles Craigslist search queries and returns lists of ads
- `ad.py`: Represents individual listings with lazy loading of detailed information
- `utils.py`: Utility functions for URL building and price formatting

**calc_scores.py**: Complex scoring algorithm that evaluates listings based on:
- Price ranges with different scoring curves for SC vs LG
- Distance from target locations (Santa Cruz boardwalk vs Los Gatos work location)
- Square footage scoring
- Amenity scoring (garage, parking, laundry, etc.)
- Spam/unwanted listing filtering

**results_to_html.py**: Generates HTML email content with formatted tables

### Data Flow

1. Search configuration defines area, price limits, and coordinates
2. Scraper fetches listing summaries from Craigslist search pages
3. Individual ad details are fetched (with rate limiting and error handling)
4. Scoring algorithm evaluates each listing across multiple criteria
5. Duplicate detection using Levenshtein distance on titles/descriptions
6. Results sorted by score and formatted into HTML
7. Email sent with new listings above score threshold
8. Data persistence using pickle files to avoid re-processing old listings

### Configuration

The application uses two predefined search configurations:
- **SC (Santa Cruz)**: Targets rentals near Santa Cruz boardwalk, max $3300
- **LG (Los Gatos)**: Targets rentals near SA Photonics work location, max $4000

Environment variables required for email functionality:
- `EMAIL_SENDER_ADDRESS`
- `EMAIL_RECEIVER_ADDRESS` 
- `EMAIL_PASSWORD`

### Spam Filtering

Built-in filtering removes listings from specific management companies and those containing spam text patterns in titles, descriptions, or attributes.