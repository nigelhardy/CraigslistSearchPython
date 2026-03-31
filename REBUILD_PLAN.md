# Craigslist Scraper v2 - Rebuild Plan

## 🎯 Project Vision

**Simplified Architecture for Subaru Performance Parts Search with Enhanced Visibility and Tuning**

### Overview
The current system has the right foundation but needs better separation of concerns, configurability, and debugging capabilities. This rebuild will create a clean, modular architecture that allows easy tuning of scoring algorithms while maintaining the powerful multi-area search capabilities.

## 📋 Proposed Architecture

### Core Principles
1. **Separation of Concerns**: Each module has a single responsibility
2. **Configuration-Driven**: All settings in YAML files
3. **Pipeline Architecture**: Data collection → processing → scoring → output
4. **Pluggable Scoring**: Easy to add new ranking algorithms
5. **Debugging First**: Comprehensive logging and step-by-step visibility

### Directory Structure
```
craigslist_scraper_v2/
├── config/
│   ├── search_config.py          # Search configuration classes
│   ├── scoring_config.py         # Scoring weights and rules
│   └── app_config.py           # Application settings
├── core/
│   ├── config_loader.py          # YAML configuration management
│   ├── search_engine.py          # Multi-area search orchestration  
│   └── pipeline.py              # Main data processing pipeline
├── scrapers/
│   ├── craigslist_pages.py       # Page fetching and URL extraction
│   └── craigslist_ads.py        # Ad detail fetching and parsing
├── processors/
│   ├── listing_enricher.py      # Data extraction and enhancement
│   ├── listing_ranker.py         # Scoring algorithm interface
│   └── duplicate_handler.py       # Duplicate detection
├── algorithms/
│   ├── base_algorithm.py          # Abstract base class
│   └── subaru_forester.py      # Concrete scoring implementation
├── outputs/
│   ├── console_formatter.py       # Console table formatting
│   ├── html_formatter.py         # HTML output generation
│   ├── file_manager.py           # File I/O (pickle/JSON/YAML)
│   └── email_sender.py          # Email notifications
├── utils/
│   ├── scoring_utils.py          # Common scoring utilities
│   └── data_utils.py            # Data manipulation helpers
├── main.py                      # Application entry point
├── tests/
│   ├── test_scoring.py            # Unit tests for scoring
│   └── test_data_flow.py         # Integration tests
└── docs/
    ├── user_guide.md              # Usage documentation
    └── developer_guide.md          # Development guide
```

## 🔧 Implementation Phases

### Phase 1: Core Framework (Week 1)
**Goal**: Establish the foundational architecture
- Configuration management system
- Basic data pipeline 
- Abstract scoring framework
- Simple Subaru forester algorithm
- Console and HTML output

### Phase 2: Enhanced Scraping (Week 2) 
**Goal**: Improve data collection capabilities
- Multi-city search orchestration
- Robust error handling and retry logic
- Rate limiting and respectful crawling
- Metadata extraction and enrichment

### Phase 3: Advanced Scoring (Week 3)
**Goal**: Sophisticated ranking algorithms
- Configurable scoring weights
- Rule-based penalty system
- Machine learning readiness (future)
- Performance metrics and analytics

### Phase 4: Production Features (Week 4)
**Goal**: Production-ready system
- Email notifications with HTML templates
- Automated scheduling and cron support
- Data persistence and backup strategies
- Monitoring and alerting

## 📊 Configuration System

### Search Configuration
```yaml
searches:
  subaru_performance:
    name: "Subaru Performance Parts"
    description: "Wide parts search with multi-city coverage"
    query: "subaru forester impreza wrx sti coilovers rally racing seats brakes tires performance parts"
    categories: ["pts", "wta", "pta"]
    cities:
      primary: "sfbay"      # +5 local bonus
      secondary: ["losangeles", "portland", "seattle"]  # Regional coverage
      tertiary: ["sacramento", "denver", "phoenix"]     # Extended coverage
    max_fetches: 50
    max_pages_per_city: 5
    wait_ms: 5000
    
  subaru_forester:
    name: "Subaru Forester Cars"
    description: "1st gen Forester search with manual transmission preference"
    query: "subaru forester manual low mileage clean title private owner"
    categories: ["cto"]
    cities: ["sfbay", "losangeles", "sacramento"]
    max_fetches: 30
    price_range: [500, 15000]  # Affordable range

scoring:
  defaults:
    minimum_score_threshold: 5.0
    local_bonus_points: 5.0
    duplicate_similarity_threshold: 0.8
    
  subaru_forester:
    # Positive scoring
    manual_transmission: 20
    low_mileage_under_80k: 20
    low_mileage_under_120k: 15
    one_owner: 15
    first_gen_1997_2004: 25
    clean_title: 12
    non_turbo: 15
    affordable_price_under_7k: 20
    affordable_price_under_10k: 15
    good_photos: 8
    
    # Negative scoring  
    turbo_engine: -15
    automatic_transmission: -10
    multiple_owners: -5
    salvage_title: -25
    dealer_listing: -20
    wrong_generation_2003_plus: -15
    high_mileage_over_150k: -10
    
  subaru_performance:
    # Part type scoring
    coilovers: 25
    rally_parts: 20
    racing_seats: 15
    sti_components: 25
    performance_brakes: 18
    performance_tires: 12
    suspension_parts: 15
    
    # Brand scoring
    premium_brands:
      ohlins: 20, kw: 18, bilstein: 15, brembo: 18
      moton: 18, jrz: 16, fortin: 16
    performance_brands:
      sti: 15, tein: 12, h_r: 10, eibach: 10, whiteline: 12
    
    # Compatibility scoring
    year_match_perfect_1997_2004: 20
    year_match_close_1995_2006: 15
    year_match_subaru_compatible: 10

output:
  console:
    max_title_length: 40
    show_score_breakdown: true
    highlight_negative_scores: true
    color_coding:
      positive_scores: "green"
      negative_scores: "red"
      neutral_scores: "yellow"
  
  file_management:
    save_all_results: true      # Save both positive and negative
    primary_format: "json"        # Primary save format
    backup_formats: ["json", "yaml"]  # Backup formats
    rotation: true                  # Rotate files when > 1MB
    max_file_size_mb: 5
```

## 🔍 Algorithm Features

### Advanced Scoring Capabilities
1. **Rule-Based Scoring**: Configurable points for each attribute
2. **Weighted Scoring**: Different importance levels for different criteria
3. **Penalty System**: Negative scoring for undesirable attributes
4. **Composite Metrics**: Multiple scoring factors combined intelligently
5. **Threshold Management**: Dynamic filtering with adjustable thresholds
6. **Score Breakdowns**: Detailed explanation of why each listing scored as it did

### Data Pipeline Features
1. **Multi-City Search**: Parallel searches with geographic prioritization
2. **Duplicate Detection**: Content similarity with configurable thresholds
3. **Incremental Updates**: Only process new listings to avoid rework
4. **Metadata Tracking**: Discovery timestamps, source cities, processing status
5. **Error Recovery**: Robust retry logic with exponential backoff
6. **Rate Limiting**: Respectful crawling with configurable delays

## 🚀 Production Readiness

### Monitoring & Analytics
1. **Performance Metrics**: Search success rates, processing times, scoring distributions
2. **Quality Metrics**: Listing quality trends, algorithm effectiveness
3. **Usage Analytics**: Search patterns, popular queries, geographic distribution
4. **Alerting**: Configurable notifications for high-value findings
5. **Historical Analysis**: Trend analysis over time, price fluctuations

### Automation Features
1. **Scheduled Searches**: Cron-compatible with configurable schedules
2. **Smart Notifications**: Email alerts with priority-based filtering
3. **Auto-Ranking**: Threshold adjustments based on user feedback
4. **Data Archival**: Long-term storage with compression and cleanup
5. **API Integration**: Ready for web service or mobile app integration

## 📈 Migration Strategy

### From Current System
1. **Data Migration**: Convert existing pickle files to new format
2. **Configuration Migration**: Translate current settings to YAML
3. **Algorithm Migration**: Refactor existing scoring to new framework
4. **Gradual Rollout**: Run both systems in parallel for comparison
5. **Fallback Plan**: Quick rollback if issues arise

## 🧪 Development Workflow

### Environment Setup
```bash
# Create new development environment
python -m venv craigslist_scraper_v2
source craigslist_scraper_v2/bin/activate

# Install dependencies
pip install -r requirements_v2.txt
pip install -r requirements_dev.txt

# Setup pre-commit hooks
pre-commit install
```

### Testing Strategy
```bash
# Unit tests
pytest tests/test_scoring.py -v

# Integration tests
python tests/test_data_flow.py --config config/test.yaml --verbose

# Performance tests
python -m pytest tests/test_performance.py --benchmark

# Configuration validation
python utils/config_validator.py config/production.yaml
```

### CI/CD Pipeline
```yaml
# .github/workflows/ci.yml
name: Build and Test
on: [push, pull_request]
jobs:
  test:
    runs: python -m pytest
  build:
    runs: python setup.py sdist bdist_wheel
  deploy:
    runs: python deploy.py
    environment: production
```

## 📚 Documentation Plan

### User Documentation
- **Quick Start Guide**: 5-minute setup and first search
- **Configuration Guide**: YAML editing, scoring customization
- **Algorithm Guide**: How scoring works, how to tune it
- **Troubleshooting**: Common issues and solutions
- **Best Practices**: Optimal settings for different use cases

### Developer Documentation
- **Architecture Overview**: System design and data flow
- **API Documentation**: Class interfaces and method signatures
- **Contributing Guide**: Code standards and submission process
- **Deployment Guide**: Production setup and maintenance

## 🏆 Success Metrics

### Technical Goals
- **Search Speed**: 50% reduction in processing time through parallelization
- **Scoring Accuracy**: 90% user satisfaction with ranked results
- **System Reliability**: 99.9% uptime with automatic error recovery
- **Data Quality**: 95% accurate listing enrichment
- **Performance**: Handle 1000+ listings per search without slowdown

### User Experience Goals
- **Setup Time**: <5 minutes from installation to first search
- **Learning Curve**: <30 minutes to master advanced features
- **Daily Use**: <2 minutes from setup to desired results
- **Customization**: Easy rule modification without coding knowledge

## 🚧 Implementation Timeline

### Week 1-2: Core Framework
- Configuration management system
- Basic data pipeline
- Subaru forester scoring algorithm
- Console output formatter

### Week 3-4: Enhanced Scraping  
- Multi-city search engine
- Robust error handling
- Rate limiting implementation
- Data enrichment features

### Week 5-6: Advanced Scoring
- Configurable scoring weights
- Advanced rule engine
- Machine learning preparation
- Performance analytics

### Week 7-8: Production Features
- Email notifications
- Scheduled searches
- Monitoring dashboard
- API endpoints
- Mobile app support

### Week 9-12: Polish & Migration
- GUI interface
- Advanced visualizations
- Migration tools
- Performance optimization
- Documentation completion

## 🎯 First Steps

1. **Create Project Structure**: Set up directories and basic files
2. **Configuration System**: Implement YAML-based configuration
3. **Search Engine**: Multi-city URL collection with geographic scoring
4. **Data Pipeline**: Process flow with duplicate detection and filtering
5. **Basic Scoring**: Implement configurable Subaru forester algorithm
6. **Output System**: Console and HTML formatters with advanced features
7. **Testing Framework**: Unit tests and integration tests
8. **Documentation**: User and developer guides

This rebuild provides:
- **Enhanced Visibility**: Complete control over search and scoring behavior
- **Easy Tuning**: Configuration-based adjustments without code changes
- **Production Ready**: Scalable, maintainable, and extensible architecture
- **Future-Proof**: Framework ready for machine learning and advanced features

## 🔑 Success Criteria

### MVP (Week 2)
- [ ] Multi-city search with basic Subaru forester scoring
- [ ] YAML configuration system
- [ ] Console output with score breakdown
- [ ] File management with all results saving

### Full System (Week 8)
- [ ] Complete algorithm suite with configurable scoring
- [ ] Email notifications with HTML templates
- [ ] Performance monitoring and analytics
- [ ] Automated scheduling and cron support
- [ ] Migration tools from current system
- [ ] Complete documentation and testing framework

## 💡 Key Innovations

1. **Configurable Scoring**: Rule-based system that's easy to understand and modify
2. **Geographic Intelligence**: Smart city prioritization with local bonuses
3. **Pipeline Architecture**: Clean data flow with processing stages
4. **Format Flexibility**: Multiple output formats and custom styling
5. **Development-Friendly**: Easy testing, debugging, and extension
6. **Production-Ready**: Scalable, maintainable, and monitorable

This architecture transforms the current working system into a professional-grade, extensible platform that's ready for production use while enabling sophisticated tuning and future enhancements.