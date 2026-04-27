"""Display module for HTML output generation."""
from datetime import datetime
from pathlib import Path
from typing import List, Optional

from models import Listing, VehicleListing


def generate_html(listings: List[Listing], query: str) -> str:
    """Generate HTML for ranked listings with expandable details."""
    html = f"""<!DOCTYPE html>
<html>
<head>
    <title>Craigslist Search - {query}</title>
    <style>
        body {{ font-family: Arial, sans-serif; margin: 20px; background: #f5f5f5; }}
        .container {{ max-width: 1400px; margin: 0 auto; background: white; padding: 20px; border-radius: 8px; }}
        h1 {{ color: #333; border-bottom: 2px solid #4CAF50; padding-bottom: 10px; }}
        .meta {{ color: #666; margin-bottom: 20px; }}
        table {{ width: 100%; border-collapse: collapse; }}
        th {{ background: #4CAF50; color: white; padding: 12px; text-align: left; }}
        td {{ padding: 10px; border-bottom: 1px solid #ddd; vertical-align: top; }}
        tr:hover {{ background: #f9f9f9; }}
        .score {{ font-weight: bold; font-size: 1.2em; }}
        .score-high {{ color: #4CAF50; }}
        .score-medium {{ color: #FF9800; }}
        .score-low {{ color: #f44336; }}
        .price {{ color: #4CAF50; font-weight: bold; }}
        .reasons {{ font-size: 0.9em; color: #666; }}
        .details {{ font-size: 0.85em; color: #888; }}
        .region {{ font-size: 0.85em; color: #2196F3; font-weight: 500; }}
        .show-btn {{ 
            background: #2196F3; color: white; border: none; padding: 5px 10px; 
            border-radius: 4px; cursor: pointer; font-size: 0.8em;
        }}
        .show-btn:hover {{ background: #1976D2; }}
        .show-btn.active {{ background: #f44336; }}
        .listing-details {{
            display: none;
            background: #fafafa;
            border: 1px solid #ddd;
            border-radius: 4px;
            padding: 15px;
            margin-top: 5px;
        }}
        .listing-details.visible {{ display: block; }}
        .listing-details h3 {{ margin: 0 0 10px 0; color: #333; }}
        .listing-details .description {{ 
            background: white; padding: 10px; border-radius: 4px; 
            white-space: pre-wrap; margin-bottom: 10px; max-height: 200px; overflow-y: auto;
        }}
        .listing-details .images {{ display: flex; gap: 5px; flex-wrap: wrap; }}
        .listing-details .images img {{ 
            max-width: 150px; max-height: 150px; object-fit: cover; 
            border-radius: 4px; cursor: pointer;
        }}
        .listing-details .meta-info {{ font-size: 0.85em; color: #666; margin-top: 10px; }}
        .listing-details .close-btn {{
            background: #666; color: white; border: none; padding: 5px 10px;
            border-radius: 4px; cursor: pointer; float: right;
        }}
        .listing-details .close-btn:hover {{ background: #444; }}
    </style>
    <script>
        let openIndex = null;
        
        function toggleDetails(index) {{
            if (openIndex !== null && openIndex !== index) {{
                document.getElementById('details-' + openIndex).classList.remove('visible');
                document.getElementById('btn-' + openIndex).classList.remove('active');
                document.getElementById('btn-' + openIndex).textContent = 'Show';
            }}
            
            const detailsDiv = document.getElementById('details-' + index);
            const btn = document.getElementById('btn-' + index);
            
            if (detailsDiv.classList.contains('visible')) {{
                detailsDiv.classList.remove('visible');
                btn.classList.remove('active');
                btn.textContent = 'Show';
                openIndex = null;
            }} else {{
                detailsDiv.classList.add('visible');
                btn.classList.add('active');
                btn.textContent = 'Hide';
                openIndex = index;
            }}
        }}
    </script>
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
                    <th style="width:50px">Rank</th>
                    <th style="width:70px">Score</th>
                    <th style="width:120px">Region</th>
                    <th>Title</th>
                    <th style="width:100px">Price</th>
                    <th style="width:100px">Details</th>
                    <th style="width:200px">Reasons</th>
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
        
        region = listing.city if listing.city else "Unknown"
        if listing.category:
            region += f" ({listing.category})"
        
        # Escape for HTML
        title_escaped = listing.title.replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;").replace('"', '&quot;')
        desc_escaped = (listing.description or '').replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")
        
        # Format images
        images_html = ''
        if listing.images:
            for img in listing.images[:8]:  # Limit to 8 images
                if img and 'craigslist' in img:
                    images_html += f'<img src="{img}" onclick="window.open(\'{img}\', \'_blank\')">'
        
        # Format posted date
        posted_str = listing.posted_date[:16] if listing.posted_date else 'N/A'
        
        html += f"""
                <tr>
                    <td>#{i}</td>
                    <td class="score {score_class}">{listing.score:.1f}</td>
                    <td class="region">{region}</td>
                    <td><a href="{listing.url}" target="_blank">{title_escaped}</a></td>
                    <td class="price">{price_str}</td>
                    <td>
                        <button class="show-btn" id="btn-{i}" onclick="toggleDetails({i})">Show</button>
                    </td>
                    <td class="reasons">{'; '.join(listing.score_reasons)}</td>
                </tr>
                <tr>
                    <td colspan="7" style="padding: 0; border-bottom: 2px solid #4CAF50;">
                        <div class="listing-details" id="details-{i}">
                            <button class="close-btn" onclick="toggleDetails({i})">Close</button>
                            <h3>{title_escaped}</h3>
                            <div class="description">{desc_escaped}</div>
                            {f'<div class="images">{images_html}</div>' if images_html else ''}
                            <div class="meta-info">
                                <strong>Post ID:</strong> {listing.url.split('/')[-1].replace('.html', '')} | 
                                <strong>Posted:</strong> {posted_str}
                            </div>
                            <div style="margin-top:10px">
                                <a href="{listing.url}" target="_blank" style="color:#2196F3">View on Craigslist &rarr;</a>
                            </div>
                        </div>
                    </td>
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