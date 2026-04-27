"""Display module for HTML output generation."""
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from models import Listing, VehicleListing


def generate_html(listings: List[Listing], query: str) -> str:
    """Generate HTML for ranked listings."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Craigslist Search - {query}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1200px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        .meta {{ color: #666; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #4CAF50; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; }}
        tr:hover {{ background: #f9f9f9; }}
        .score {{ font-weight: bold; font-size: 1.2em; }}
        .score-high {{ color: #4CAF50; }}
        .score-medium {{ color: #FF9800; }}
        .score-low {{ color: #f44336; }}
        .price {{ color: #4CAF50; font-weight: bold; }}
        .reasons {{ font-size: 0.9em; color: #666; }}
        .details {{ font-size: 0.85em; color: #888; }}
        .region {{ font-size: 0.85em; color: #2196F3; font-weight: 500; }}
    </style>
</head>
<body>
    <div class="container">
        <h1>🔍 {query}</h1>
        <div class="meta">
            Generated: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 
            Total Listings: {len(listings)}
        </div>
        <table>
            <thead>
                <tr>
                    <th>Rank</th>
                    <th>Score</th>
                    <th>Region</th>
                    <th>Title</th>
                    <th>Price</th>
                    <th>Details</th>
                    <th>Reasons</th>
                </tr>
            </thead>
            <tbody>"""
    
    for i, listing in enumerate(listings, 1):
        if listing.score >= 20:
            score_class = "score-high"
        elif listing.score >= 0:
            score_class = "score-medium"
        else:
            score_class = "score-low"
        
        price_str = f"${listing.price:,}" if listing.price else "N/A"
        
        details = []
        if isinstance(listing, VehicleListing):
            if listing.mileage:
                details.append(f"{listing.mileage:,} mi")
            if listing.transmission:
                details.append(listing.transmission)
            if listing.year:
                details.append(str(listing.year))
        else:
            if listing.location:
                details.append(listing.location)
        
        details_str = " | ".join(details) if details else "N/A"
        
        # Add region information
        region = listing.city if listing.city else "Unknown"
        if listing.category:
            region += f" ({listing.category})"
        
        html += f"""
                <tr>
                    <td>#{i}</td>
                    <td class="score {score_class}">{listing.score:.1f}</td>
                    <td class="region">{region}</td>
                    <td><a href="{listing.url}" target="_blank">{listing.title}</a></td>
                    <td class="price">{price_str}</td>
                    <td class="details">{details_str}</td>
                    <td class="reasons">{'; '.join(listing.score_reasons)}</td>
                </tr>"""
    
    html += """
            </tbody>
        </table>
    </div>
</body>
</html>"""
    
    return html


def display_listings(listings: List[Listing], query: str, output_path: Optional[Path] = None) -> Path:
    """Display listings based on rank in HTML output."""
    html = generate_html(listings, query)
    
    if output_path is None:
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        output_path = Path(f"outputs/results/search_results_{timestamp}.html")
        output_path.parent.mkdir(parents=True, exist_ok=True)
    
    with open(output_path, 'w', encoding='utf-8') as f:
        f.write(html)
    
    print(f"💾 HTML saved to: {output_path}")
    return output_path
