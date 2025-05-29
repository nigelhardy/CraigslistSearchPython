# Overview

This is a generic Craigslist scraper and ranking system designed to automatically find and rank listings based on custom criteria. The system uses a plugin-based architecture that supports multiple search types:

    Apartment searches: Santa Cruz (SC) and Los Gatos (LG) rental listings
    Auto parts searches: BMW E39 parts (E39_PARTS) as an example
    Extensible: Easy to add new search types and ranking algorithms

The application searches multiple Craigslist categories simultaneously, scores listings using configurable algorithms, removes duplicates, and can email the best results.
Commands
Running the Application

# List available search types
python craigslist_ranker.py --list-types

# Fetch new data for Santa Cruz apartments
python craigslist_ranker.py --fetch --type SC

# Fetch new data for Los Gatos apartments  
python craigslist_ranker.py --fetch --type LG

# Fetch BMW E39 parts listings
python craigslist_ranker.py --fetch --type E39_PARTS

# Send email with results (requires .env file with email credentials)
python craigslist_ranker.py --fetch --email --type SC

# Display results in browser
python craigslist_ranker.py --display --type SC

# Display results in console (great for debugging)
python craigslist_ranker.py --console --type SC

# Fetch and immediately show in console
python craigslist_ranker.py --fetch --console --type E39_PARTS

# Test a specific listing URL
python craigslist_ranker.py --test-url "https://sfbay.craigslist.org/scz/apa/d/..."

Dependencies

pip install -r requirements.txt

Architecture
Core Components

craigslist_ranker.py: Main entry point that orchestrates the entire workflow - fetching, scoring, deduplication, email generation, and data persistence using pickle files.

craigslistscraper/: Custom scraping library

    search.py: Handles Craigslist search queries and returns lists of ads
    ad.py: Represents individual listings with lazy loading of detailed information
    utils.py: Utility functions for URL building and price formatting

ranking_system.py: Plugin-based ranking architecture

    BaseRankingAlgorithm: Abstract base class for all ranking algorithms
    ScoreCalculator: Helper utilities for common scoring operations
    RankingAlgorithmRegistry: Manages and registers ranking algorithms

ranking_algorithms/: Individual ranking algorithm implementations

    apartment_ranking.py: Santa Cruz and Los Gatos apartment ranking algorithms
    bmw_e39_parts.py: BMW E39 parts ranking algorithm (example)

config.py: Centralized configuration with support for multiple categories per search type

plugin_manager.py: Initializes and registers all ranking algorithms

results_to_html.py: Generates HTML email content with formatted tables
Data Flow

    Search configuration defines multiple categories, filters, and target criteria
    Scraper fetches listing summaries from multiple Craigslist categories simultaneously
    Individual ad details are fetched (with rate limiting and error handling)
    Plugin-based ranking algorithm evaluates each listing using category-specific criteria
    Duplicate detection using Levenshtein distance on titles/descriptions
    Results sorted by score and formatted into HTML
    Email sent with new listings above score threshold
    Data persistence using pickle files to avoid re-processing old listings

Configuration

The application supports multiple search types with different categories:

    SC (Santa Cruz): Apartment search near Santa Cruz boardwalk, category: apa
    LG (Los Gatos): Apartment search near work location, category: apa
    E39_PARTS (BMW E39): Auto parts search, categories: pts, wto

Environment variables required for email functionality:

    EMAIL_SENDER_ADDRESS
    EMAIL_RECEIVER_ADDRESS
    EMAIL_PASSWORD

Adding New Search Types

    Create a new ranking algorithm class inheriting from BaseRankingAlgorithm
    Implement required methods: calculate_scores(), get_search_categories(), etc.
    Add search configuration to Config.SEARCH_CONFIGS in config.py
    Register the algorithm in plugin_manager.py

Spam Filtering
Each ranking algorithm can define its own spam filters for titles, descriptions, and attributes. The system automatically filters out unwanted listings before scoring.
