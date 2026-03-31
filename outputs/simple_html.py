from typing import List, Dict, Any
from datetime import datetime

from craigslist_scraper_v2.scrapers.craigslist_scraper import CraigslistListing
from craigslist_scraper_v2.algorithms.subaru_forester import SimpleScorer, ScoreResult


def generate_simple_html(listings: List[CraigslistListing], 
                        score_results: List[ScoreResult],
                        search_query: str = "") -> str:
    """Generate a simple HTML report."""
    
    # Combine and sort by score
    scored_listings = sorted(zip(listings, score_results), 
                            key=lambda x: x[1].total_score, reverse=True)
    
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Craigslist Search Results - {search_query}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; }}
        table {{ border-collapse: collapse; width: 100%; }}
        th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
        th {{ background-color: #f2f2f2; }}
        .score-positive {{ color: green; font-weight: bold; }}
        .score-negative {{ color: red; }}
        .score-neutral {{ color: orange; }}
    </style>
</head>
<body>
    <h1>🔍 Craigslist Search Results</h1>
    <p><strong>Query:</strong> {search_query}</p>
    <p><strong>Generated:</strong> {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}</p>
    
    <table>
        <thead>
            <tr>
                <th>Score</th>
                <th>Title</th>
                <th>Price</th>
                <th>Location</th>
                <th>Mileage</th>
                <th>Transmission</th>
                <th>URL</th>
                <th>Score Breakdown</th>
            </tr>
        </thead>
        <tbody>"""
    
    for listing, score_result in scored_listings:
        # Score coloring
        if score_result.total_score >= 20:
            score_class = "score-positive"
        elif score_result.total_score >= 0:
            score_class = "score-neutral"
        else:
            score_class = "score-negative"
        
        # Format price
        price_str = f"${listing.price:,}" if listing.price else "N/A"
        
        # Format mileage
        mileage_str = f"{listing.mileage:,}" if listing.mileage else "N/A"
        
        # Format transmission
        trans_str = listing.transmission or "N/A"
        
        # Score breakdown
        breakdown_str = "; ".join(score_result.reasons)
        
        html += f"""
            <tr>
                <td class="{score_class}">{score_result.total_score:.1f}</td>
                <td>{listing.title}</td>
                <td>{price_str}</td>
                <td>{listing.location}</td>
                <td>{mileage_str}</td>
                <td>{trans_str}</td>
                <td><a href="{listing.url}" target="_blank">View</a></td>
                <td><small>{breakdown_str}</small></td>
            </tr>"""
    
    html += """
        </tbody>
    </table>
</body>
</html>"""
    
    return html


def save_html_file(html_content: str, filename: str = None) -> str:
    """Save HTML to file."""
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"search_results_{timestamp}.html"
    
    if filename is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        filename = f"search_results_{timestamp}.html"
    
    with open(filename, 'w', encoding='utf-8') as f:
        f.write(html_content)
    
    return filename