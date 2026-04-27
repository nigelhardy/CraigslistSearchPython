#!/bin/bash
# Cron runner for Craigslist scraper
# Add to crontab: */15 * * * * /path/to/run.sh >> /path/to/logs/scraper.log 2>&1

DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$DIR"

# Create logs directory if needed
mkdir -p "$DIR/logs"

# Run the runner with email notifications
python runner.py --configs-file config/configs.yaml --email --fetch 20