import os
import smtplib
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from datetime import datetime
from typing import List, Dict, Any
from dotenv import load_dotenv

load_dotenv()


def get_email_config() -> Dict[str, str]:
    return {
        "sender": os.getenv("EMAIL_SENDER_ADDRESS", ""),
        "receiver": os.getenv("EMAIL_RECEIVER_ADDRESS", ""),
        "password": os.getenv("EMAIL_PASSWORD", ""),
    }


def send_email(
    subject: str,
    html_content: str,
    sender: str = None,
    receiver: str = None,
    password: str = None,
) -> bool:
    if sender is None or receiver is None or password is None:
        config = get_email_config()
        sender = sender or config["sender"]
        receiver = receiver or config["receiver"]
        password = password or config["password"]

    if not sender or not receiver or not password:
        raise ValueError("Missing email credentials. Set EMAIL_SENDER_ADDRESS, EMAIL_RECEIVER_ADDRESS, and EMAIL_PASSWORD in .env")

    msg = MIMEMultipart()
    msg["From"] = sender
    msg["To"] = receiver
    msg["Subject"] = subject
    msg.attach(MIMEText(html_content, "html"))

    try:
        with smtplib.SMTP("smtp.gmail.com", 587) as server:
            server.starttls()
            server.login(sender, password)
            server.sendmail(sender, receiver, msg.as_string())
        print("Email sent successfully!")
        return True
    except Exception as e:
        print(f"Failed to send email: {e}")
        return False


def listing_to_dict(listing) -> Dict[str, Any]:
    if isinstance(listing, dict):
        return listing
    return {
        "url": getattr(listing, "url", ""),
        "title": getattr(listing, "title", ""),
        "price": getattr(listing, "price", None),
        "location": getattr(listing, "location", ""),
        "city": getattr(listing, "city", ""),
        "description": getattr(listing, "description", ""),
        "score": getattr(listing, "score", 0),
    }


def listings_to_html(listings: List[Any], title: str = "Craigslist Listings") -> str:
    if not listings:
        return "<html><body><p>No new listings found.</p></body></html>"

    rows = []
    for listing in listings:
        data = listing_to_dict(listing)
        price = data.get("price")
        price_str = f"${price:,}" if price else "N/A"

        score = data.get("score", 0)
        location = data.get("location", "")
        city = data.get("city", "")

        desc = data.get("description", "")[:200]
        if len(data.get("description", "")) > 200:
            desc += "..."

        rows.append(f"""
        <tr>
            <td><a href="{data.get('url', '')}" target="_blank">{data.get('title', 'N/A')}</a></td>
            <td>{desc}</td>
            <td align="center">{score:.1f}</td>
            <td align="right">{price_str}</td>
            <td>{city}, {location}</td>
        </tr>
        """)

    table = f"""
    <table border="1" cellpadding="5" cellspacing="0" style="border-collapse: collapse;">
        <tr style="background-color: #f2f2f2;">
            <th>Title</th>
            <th>Description</th>
            <th>Score</th>
            <th>Price</th>
            <th>Location</th>
        </tr>
        {''.join(rows)}
    </table>
    """

    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    return f"""
    <html>
    <body>
        <h2>{title}</h2>
        <p>Found {len(listings)} new listings above threshold. Generated: {timestamp}</p>
        {table}
    </body>
    </html>
    """


def notify_matches(
    listings: List[Any],
    search_name: str,
    score_threshold: float = 0,
) -> bool:
    if not listings:
        print("No listings above threshold to notify about.")
        return False

    html_content = listings_to_html(listings, f"New {search_name} Listings")
    subject = f"New {search_name} Listings! ({len(listings)} found) - {datetime.now().strftime('%Y-%m-%d')}"

    return send_email(subject, html_content)