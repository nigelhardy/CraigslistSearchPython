"""Craigslist-specific parser for extracting listing details from HTML."""
import re
from typing import Optional, Tuple
from bs4 import BeautifulSoup
from datetime import datetime

from parsers.base_parser import ListingParser
from models import Listing, VehicleListing, ListingState


class CraigslistListingParser(ListingParser):
    """Parser for Craigslist listing detail pages.
    
    Extracts all available information from Craigslist HTML including:
    - Basic info: description, images, posted_date
    - Vehicle-specific: mileage, transmission, title_status, year, vin, condition, make, model
    """
    
    def can_parse(self, soup: BeautifulSoup) -> bool:
        """Check if this is a Craigslist listing page."""
        # Craigslist listings have specific structure
        return bool(
            soup.find('section', {'id': 'postingbody'}) or
            soup.find('div', class_='body') or
            soup.find('h2', class_='postingtitle')
        )
    
    def parse(self, soup: BeautifulSoup, base_listing: Listing) -> Optional[Listing]:
        """Parse Craigslist HTML into a Listing or VehicleListing."""
        try:
            # First try to extract from JSON-LD (new Craigslist format)
            json_ld_data = self._extract_json_ld_data(soup)
            
            if json_ld_data:
                # Use JSON-LD data as primary source
                title = json_ld_data.get('name') or base_listing.title
                price = self._parse_int(json_ld_data.get('offers', {}).get('price', ''))
                description = json_ld_data.get('description')
                images = json_ld_data.get('image', [])
                
                # Extract location from JSON-LD
                location = None
                address = json_ld_data.get('offers', {}).get('availableAtOrFrom', {}).get('address', {})
                if address:
                    city = address.get('addressLocality')
                    region = address.get('addressRegion')
                    if city and region:
                        location = f"{city}, {region}"
                    elif city:
                        location = city
                
                # For vehicle listings, we still need to extract from HTML attributes
                # since JSON-LD doesn't contain vehicle-specific details
                vehicle_attrs = self._extract_vehicle_attributes(soup)
                
                # Determine if this is a vehicle listing
                is_vehicle = self._is_vehicle_listing(base_listing, vehicle_attrs)
                
                # Extract year from title if not found in attributes
                year = vehicle_attrs.get('year') or self._extract_year_from_title(title)
                
                # Create appropriate listing type
                if is_vehicle:
                    listing = VehicleListing(
                        url=base_listing.url,
                        title=title,
                        price=price,
                        location=location or base_listing.location,
                        city=base_listing.city,
                        category=base_listing.category,
                        state=ListingState.HTML_PARSED,
                        description=description,
                        posted_date=self._extract_posted_date(soup),  # Still extract from HTML
                        images=images,
                        mileage=vehicle_attrs.get('mileage'),
                        transmission=vehicle_attrs.get('transmission'),
                        title_status=vehicle_attrs.get('title_status'),
                        year=year,
                        vin=vehicle_attrs.get('vin'),
                        condition=vehicle_attrs.get('condition'),
                        make=vehicle_attrs.get('make'),
                        model=vehicle_attrs.get('model')
                    )
                else:
                    listing = Listing(
                        url=base_listing.url,
                        title=title,
                        price=price,
                        location=location or base_listing.location,
                        city=base_listing.city,
                        category=base_listing.category,
                        state=ListingState.HTML_PARSED,
                        description=description,
                        posted_date=self._extract_posted_date(soup),  # Still extract from HTML
                        images=images
                    )
            else:
                # Fallback to old HTML parsing method
                title = self._extract_title(soup) or base_listing.title
                price = self._extract_price(soup) or base_listing.price
                location = self._extract_location(soup) or base_listing.location
                description = self._extract_description(soup)
                images = self._extract_images(soup)
                posted_date = self._extract_posted_date(soup)
                
                # Extract vehicle attributes
                vehicle_attrs = self._extract_vehicle_attributes(soup)
                
                # Determine if this is a vehicle listing
                is_vehicle = self._is_vehicle_listing(base_listing, vehicle_attrs)
                
                # Extract year from title if not found in attributes
                year = vehicle_attrs.get('year') or self._extract_year_from_title(title)
                
                # Create appropriate listing type
                if is_vehicle:
                    listing = VehicleListing(
                        url=base_listing.url,
                        title=title,
                        price=price,
                        location=location,
                        city=base_listing.city,
                        category=base_listing.category,
                        state=ListingState.HTML_PARSED,
                        description=description,
                        posted_date=posted_date,
                        images=images,
                        mileage=vehicle_attrs.get('mileage'),
                        transmission=vehicle_attrs.get('transmission'),
                        title_status=vehicle_attrs.get('title_status'),
                        year=year,
                        vin=vehicle_attrs.get('vin'),
                        condition=vehicle_attrs.get('condition'),
                        make=vehicle_attrs.get('make'),
                        model=vehicle_attrs.get('model')
                    )
                else:
                    listing = Listing(
                        url=base_listing.url,
                        title=title,
                        price=price,
                        location=location,
                        city=base_listing.city,
                        category=base_listing.category,
                        state=ListingState.HTML_PARSED,
                        description=description,
                        posted_date=posted_date,
                        images=images
                    )
            
            # Set timestamps
            listing.last_updated = datetime.now().isoformat()
            
            return listing
            
        except Exception as e:
            print(f"❌ Error parsing listing {base_listing.url}: {e}")
            return None
    
    def _extract_title(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the listing title from HTML."""
        # Method 1: Look for span.valu.year + span.valu.makemodel
        year_elem = soup.find('span', class_='year')
        makemodel_elem = soup.find('span', class_='makemodel')
        if year_elem and makemodel_elem:
            year = year_elem.get_text(strip=True)
            makemodel = makemodel_elem.get_text(strip=True)
            return f"{year} {makemodel}"
        
        # Method 2: Look for JSON-LD data
        script = soup.find('script', {'id': 'ld_posting_data', 'type': 'application/ld+json'})
        if script:
            try:
                import json
                data = json.loads(script.string)
                if 'name' in data:
                    return data['name']
            except:
                pass
        
        # Method 3: Use HTML title tag
        title_tag = soup.find('title')
        if title_tag:
            title = title_tag.get_text(strip=True)
            # Clean up "for sale by owner - location - craigslist"
            title = re.sub(r'\s+for sale by owner.*$', '', title)
            title = re.sub(r'\s+-\s+craigslist$', '', title)
            return title
        
        return None
    
    def _extract_price(self, soup: BeautifulSoup) -> Optional[int]:
        """Extract the listing price."""
        # Method 1: Look for span.price
        price_elem = soup.find('span', class_='price')
        if price_elem:
            price_text = price_elem.get_text(strip=True)
            return self._parse_int(price_text)
        
        # Method 2: Look for JSON-LD data
        script = soup.find('script', {'id': 'ld_posting_data', 'type': 'application/ld+json'})
        if script:
            try:
                import json
                data = json.loads(script.string)
                if 'offers' in data and 'price' in data['offers']:
                    return self._parse_int(data['offers']['price'])
            except:
                pass
        
        return None
    
    def _extract_location(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the listing location."""
        # Method 1: Look for span.postingtitletext small
        loc_elem = soup.find('span', class_='postingtitletext')
        if loc_elem:
            small = loc_elem.find('small')
            if small:
                return small.get_text(strip=True).strip('()')
        
        # Method 2: Look for JSON-LD address
        script = soup.find('script', {'id': 'ld_posting_data', 'type': 'application/ld+json'})
        if script:
            try:
                import json
                data = json.loads(script.string)
                if 'offers' in data and 'availableAtOrFrom' in data['offers']:
                    address = data['offers']['availableAtOrFrom'].get('address', {})
                    parts = []
                    if 'addressLocality' in address:
                        parts.append(address['addressLocality'])
                    if 'addressRegion' in address:
                        parts.append(address['addressRegion'])
                    if parts:
                        return ', '.join(parts)
            except:
                pass
        
        # Method 3: Look for meta tags
        meta = soup.find('meta', {'name': 'geo.placename'})
        if meta:
            return meta.get('content')
        
        return None
    
    def _extract_description(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the listing description."""
        # Try multiple selectors for description
        desc_elem = (
            soup.find('section', {'id': 'postingbody'}) or
            soup.find('div', {'id': 'postingbody'})
        )
        
        if desc_elem:
            # Remove any "QR Code Link to This Post" text
            for qr in desc_elem.find_all(['div', 'p']):
                if 'qr' in qr.get_text().lower() or 'link to this post' in qr.get_text().lower():
                    qr.decompose()
            
            text = desc_elem.get_text(strip=True)
            # Clean up the text
            text = re.sub(r'\n+', '\n', text)  # Remove multiple newlines
            text = re.sub(r'\s+', ' ', text)   # Normalize whitespace
            return text.strip() if text else None
        
        return None
    
    def _extract_images(self, soup: BeautifulSoup) -> list:
        """Extract image URLs from the listing."""
        images = []
        
        # Method 1: Look for thumb URLs and convert to full size
        thumbs = soup.find_all('a', class_='thumb')
        for thumb in thumbs:
            href = thumb.get('href')
            if href:
                images.append(href)
        
        # Method 2: Look for img tags with craigslist.org
        if not images:
            for img in soup.find_all('img'):
                src = img.get('src')
                if src and 'craigslist.org' in src:
                    images.append(src)
        
        # Method 3: Look for image gallery
        gallery = soup.find('div', id='thumbs') or soup.find('div', class_='gallery')
        if gallery and not images:
            for img in gallery.find_all('img'):
                src = img.get('src')
                if src:
                    images.append(src)
        
        return images
    
    def _extract_posted_date(self, soup: BeautifulSoup) -> Optional[str]:
        """Extract the posting date."""
        time_elem = soup.find('time', class_='date timeago')
        if time_elem:
            datetime_val = time_elem.get('datetime')
            if datetime_val:
                return str(datetime_val)
        
        # Alternative: look for date in other formats
        date_elem = soup.find('p', class_='postinginfo', string=re.compile(r'posted'))
        if date_elem:
            time_in_date = date_elem.find('time')
            if time_in_date:
                return str(time_in_date.get('datetime', ''))
        
        return None
    
    def _extract_vehicle_attributes(self, soup: BeautifulSoup) -> dict:
        """Extract vehicle-specific attributes from the attribute groups."""
        attrs = {}
        
        # Find all attribute groups (both p.attrgroup and div.attrgroup)
        attr_groups = soup.find_all(['p', 'div'], class_='attrgroup')
        
        for group in attr_groups:
            # Method 1: Handle Craigslist format with div.attr.class_name
            for attr_div in group.find_all('div', class_=re.compile(r'^attr\s')):
                # Get the specific attribute type from class
                classes = attr_div.get('class', [])
                attr_type = None
                for cls in classes:
                    if cls not in ['attr', 'important']:
                        attr_type = cls.replace('auto_', '')  # Remove auto_ prefix
                        break
                
                # Find label and value
                labl = attr_div.find('span', class_='labl')
                valu = attr_div.find('span', class_='valu')
                
                if valu:
                    value = valu.get_text(strip=True)
                    
                    # Determine key from either attr_type or label text
                    if labl:
                        key_from_label = labl.get_text(strip=True).lower().rstrip(':').strip()
                    else:
                        key_from_label = None
                    
                    key = key_from_label or attr_type
                    
                    # Map various key names to standard attribute names
                    if key in ['odometer', 'mileage', 'miles']:
                        attrs['mileage'] = self._parse_int(value)
                    elif key in ['transmission', 'trans']:
                        attrs['transmission'] = value.lower() if value else None
                    elif key in ['title status', 'title_status', 'title']:
                        attrs['title_status'] = value.lower() if value else None
                    elif key == 'vin':
                        attrs['vin'] = value.upper() if value else None
                    elif key in ['condition']:
                        attrs['condition'] = value.lower() if value else None
                    elif key in ['cylinders', 'cyl']:
                        attrs['cylinders'] = value if value else None
                    elif key in ['fuel', 'fuel_type']:
                        attrs['fuel'] = value.lower() if value else None
                    elif key in ['paint color', 'paint_color', 'paint']:
                        attrs['paint_color'] = value.lower() if value else None
                    elif key in ['size']:
                        attrs['size'] = value.lower() if value else None
                    elif key in ['type', 'bodytype', 'body_type']:
                        attrs['vehicle_type'] = value.lower() if value else None
                    elif key in ['drive', 'drivetrain']:
                        attrs['drive'] = value.lower() if value else None
            
            # Method 2: Handle older Craigslist format (direct spans) - ONLY as fallback
            # This format is less reliable and can have incomplete data
            for span in group.find_all('span'):
                text = span.get_text(strip=True)
                
                # Parse key: value pairs
                if ':' in text:
                    key, value = text.split(':', 1)
                    key = key.strip().lower()
                    value = value.strip()
                    
                    # Only set if not already set by Method 1 AND value is not empty
                    if key in ['odometer', 'mileage'] and 'mileage' not in attrs and value:
                        attrs['mileage'] = self._parse_int(value)
                    elif key == 'transmission' and 'transmission' not in attrs and value:
                        attrs['transmission'] = value.lower() if value else None
                    elif key == 'title status' and 'title_status' not in attrs and value:
                        attrs['title_status'] = value.lower() if value else None
                    elif key == 'vin' and 'vin' not in attrs and value:
                        attrs['vin'] = value.upper() if value else None
                    elif key == 'condition' and 'condition' not in attrs and value:
                        attrs['condition'] = value.lower() if value else None
                    elif key == 'year' and 'year' not in attrs and value:
                        attrs['year'] = self._parse_int(value)
                    elif key == 'make' and 'make' not in attrs and value:
                        attrs['make'] = value if value else None
                    elif key == 'model' and 'model' not in attrs and value:
                        attrs['model'] = value if value else None
                    elif key == 'auto_make_model' and 'make' not in attrs and value:
                        make, model = self._parse_auto_make_model(value)
                        if make:
                            attrs['make'] = make
                        if model:
                            attrs['model'] = model
                else:
                    # Handle auto_make_model without colon format
                    text_lower = text.lower()
                    if 'auto_make_model' in text_lower or self._looks_like_make_model(text):
                        if 'make' not in attrs:
                            make, model = self._parse_auto_make_model(text)
                            if make:
                                attrs['make'] = make
                            if model:
                                attrs['model'] = model
        
        return attrs
    
    def _parse_auto_make_model(self, text: str) -> Tuple[Optional[str], Optional[str]]:
        """Parse make and model from auto_make_model field.
        
        Examples:
        - "Subaru Forester" -> ("Subaru", "Forester")
        - "subaru:forester" -> ("subaru", "forester")
        - "honda accord" -> ("honda", "accord")
        """
        text = text.strip()
        
        # Remove any key prefix
        if ':' in text and len(text.split(':')) == 2:
            text = text.split(':', 1)[1].strip()
        
        # Split on common separators
        parts = re.split(r'[\s:]+', text, maxsplit=1)
        
        if len(parts) >= 2:
            make = parts[0].strip().capitalize()
            model = parts[1].strip()
            return make, model
        elif len(parts) == 1:
            # Single word - might be just make
            return parts[0].strip().capitalize(), None
        
        return None, None
    
    def _looks_like_make_model(self, text: str) -> bool:
        """Check if text looks like a make/model specification."""
        # Common vehicle makes
        makes = ['subaru', 'honda', 'toyota', 'bmw', 'ford', 'chevrolet', 'dodge', 
                'jeep', 'nissan', 'mazda', 'volkswagen', 'audi', 'mercedes', 'lexus',
                'acura', 'infiniti', 'hyundai', 'kia', 'volvo']
        
        text_lower = text.lower()
        return any(make in text_lower for make in makes)
    
    def _extract_year_from_title(self, title: str) -> Optional[int]:
        """Extract year from the listing title."""
        # Look for 4-digit years 1900-2025
        year_match = re.search(r'\b(19|20)\d{2}\b', title)
        if year_match:
            try:
                year = int(year_match.group())
                # Sanity check: year should be reasonable
                if 1900 <= year <= 2030:
                    return year
            except (ValueError, AttributeError):
                pass
        return None
    
    def _is_vehicle_listing(self, base_listing: Listing, vehicle_attrs: dict) -> bool:
        """Determine if this is a vehicle listing."""
        # Check category
        if base_listing.category in ['cto', 'pta', 'wta', 'maa']:
            return True
        
        # Check if we found vehicle attributes
        if any(vehicle_attrs.get(k) for k in ['mileage', 'transmission', 'vin']):
            return True
        
        # Check listing type
        if hasattr(base_listing, 'listing_type') and base_listing.listing_type == 'vehicle':
            return True
        
        return False
    
    def _extract_json_ld_data(self, soup: BeautifulSoup) -> Optional[dict]:
        """Extract structured data from JSON-LD script tags."""
        # Look for the main posting data
        script = soup.find('script', {'id': 'ld_posting_data', 'type': 'application/ld+json'})
        if script:
            try:
                import json
                data = json.loads(script.string)
                return data
            except Exception as e:
                print(f"⚠️  Error parsing JSON-LD data: {e}")
                pass
        
        return None
    
    def _parse_int(self, value: str) -> Optional[int]:
        """Safely parse an integer from a string, removing commas."""
        try:
            if isinstance(value, (int, float)):
                return int(value)
            cleaned = str(value).replace(',', '').replace('$', '').strip()
            return int(cleaned) if cleaned else None
        except (ValueError, AttributeError):
            return None
