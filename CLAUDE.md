# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Overview

This is a generic Craigslist scraper and ranking system designed to automatically find and rank listings based on custom criteria. The system uses a plugin-based architecture that supports multiple search types:

- **Apartment searches**: Santa Cruz (SC) and Los Gatos (LG) rental listings
- **Auto parts searches**: BMW E39 parts (E39_PARTS) as an example
- **Extensible**: Easy to add new search types and ranking algorithms

The application searches multiple Craigslist categories simultaneously, scores listings using configurable algorithms, removes duplicates, and can email the best results.

## Commands

### Running the Application
```bash
# List available search types
python santa-cruz-craigslist.py --list-types

# Fetch new data for Santa Cruz apartments
python santa-cruz-craigslist.py --fetch --type SC

# Fetch new data for Los Gatos apartments  
python santa-cruz-craigslist.py --fetch --type LG

# Fetch BMW E39 parts listings
python santa-cruz-craigslist.py --fetch --type E39_PARTS

# Send email with results (requires .env file with email credentials)
python santa-cruz-craigslist.py --fetch --email --type SC

# Display results in browser
python santa-cruz-craigslist.py --display --type SC

# Display results in console (great for debugging)
python santa-cruz-craigslist.py --console --type SC

# Fetch and immediately show in console
python santa-cruz-craigslist.py --fetch --console --type E39_PARTS

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

**ranking_system.py**: Plugin-based ranking architecture
- `BaseRankingAlgorithm`: Abstract base class for all ranking algorithms
- `ScoreCalculator`: Helper utilities for common scoring operations
- `RankingAlgorithmRegistry`: Manages and registers ranking algorithms

**ranking_algorithms/**: Individual ranking algorithm implementations
- `apartment_ranking.py`: Santa Cruz and Los Gatos apartment ranking algorithms
- `bmw_e39_parts.py`: BMW E39 parts ranking algorithm (example)

**config.py**: Centralized configuration with support for multiple categories per search type

**plugin_manager.py**: Initializes and registers all ranking algorithms

**results_to_html.py**: Generates HTML email content with formatted tables

### Data Flow

1. Search configuration defines multiple categories, filters, and target criteria
2. Scraper fetches listing summaries from multiple Craigslist categories simultaneously 
3. Individual ad details are fetched (with rate limiting and error handling)
4. Plugin-based ranking algorithm evaluates each listing using category-specific criteria
5. Duplicate detection using Levenshtein distance on titles/descriptions
6. Results sorted by score and formatted into HTML
7. Email sent with new listings above score threshold
8. Data persistence using pickle files to avoid re-processing old listings

### Configuration

The application supports multiple search types with different categories:
- **SC (Santa Cruz)**: Apartment search near Santa Cruz boardwalk, category: `apa`
- **LG (Los Gatos)**: Apartment search near work location, category: `apa`
- **E39_PARTS (BMW E39)**: Auto parts search, categories: `pts`, `wto`

Environment variables required for email functionality:
- `EMAIL_SENDER_ADDRESS`
- `EMAIL_RECEIVER_ADDRESS` 
- `EMAIL_PASSWORD`

### Adding New Search Types

1. Create a new ranking algorithm class inheriting from `BaseRankingAlgorithm`
2. Implement required methods: `calculate_scores()`, `get_search_categories()`, etc.
3. Add search configuration to `Config.SEARCH_CONFIGS` in `config.py`
4. Register the algorithm in `plugin_manager.py`

### Spam Filtering

Each ranking algorithm can define its own spam filters for titles, descriptions, and attributes. The system automatically filters out unwanted listings before scoring.