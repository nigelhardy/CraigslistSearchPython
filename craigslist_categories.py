"""
Craigslist category codes reference.

This file contains the category codes for different sections of Craigslist.
Use these codes when configuring search types in config.py.

Source: https://sfbay.craigslist.org/ (extracted from For Sale section)
"""

# For Sale categories
FOR_SALE_CATEGORIES = {
    # Category Name: Code
    "antiques": "ata",
    "appliances": "ppa", 
    "arts+crafts": "ara",
    "atv/utv/snow": "sna",
    "auto parts": "pta",
    "aviation": "ava",
    "baby+kid": "baa",
    "barter": "bar",
    "beauty+health": "haa",
    "bike parts": "bip",
    "bikes": "bia",
    "boat parts": "bpa",
    "boats": "boo",
    "books": "bka",
    "business": "bfa",
    "cars+trucks": "cta",
    "cds/dvd/vhs": "ema",
    "cell phones": "moa",
    "clothes+accessories": "cla",
    "collectibles": "cba",
    "computer parts": "syp",
    "computers": "sya",
    "electronics": "ela",
    "farm+garden": "gra",
    "free": "zip",
    "furniture": "fua",
    "garage sale": "gms",
    "general": "foa",
    "heavy equipment": "hva",
    "household": "hsa",
    "jewelry": "jwa",
    "materials": "maa",
    "motorcycle parts": "mpa",
    "motorcycles": "mca",
    "music instruments": "msa",
    "photo+video": "pha",
    "rvs+camp": "rva",
    "sporting": "sga",
    "tickets": "tia",
    "tools": "tla",
    "toys+games": "taa",
    "trailers": "tra",
    "video gaming": "vga",
    "wanted": "waa",
    "wheels+tires": "wta",
}

# Housing categories (commonly used)
HOUSING_CATEGORIES = {
    "apartments/housing for rent": "apa",
    "housing swap": "swp",
    "housing wanted": "hsw",
    "office & commercial": "off",
    "parking & storage": "prk",
    "real estate for sale": "rea",
    "rooms & shares": "roo",
    "sublets & temporary": "sub",
    "vacation rentals": "vac",
}

# Jobs categories (for reference)
JOBS_CATEGORIES = {
    "accounting+finance": "acc",
    "admin / office": "ofc", 
    "art / media / design": "med",
    "biotech / science": "sci",
    "business / mgmt": "bus",
    "customer service": "csr",
    "education": "edu",
    "engineering": "eng",
    "food / bev / hosp": "fbh",
    "general labor": "lab",
    "government": "gov",
    "healthcare": "hea",
    "human resources": "hum",
    "internet engineers": "web",
    "legal / paralegal": "leg",
    "manufacturing": "mnu",
    "marketing / pr / ad": "mar",
    "nonprofit sector": "npo",
    "real estate": "rej",
    "retail / wholesale": "ret",
    "sales / biz dev": "sls",
    "salon / spa / fitness": "spa",
    "security": "sec",
    "skilled trade / craft": "trd",
    "software / qa / dba": "sof",
    "systems / network": "sad",
    "technical support": "tch",
    "transport": "trp",
    "tv / film / video": "tfr",
    "writing / editing": "wri",
}

# All categories combined for easy lookup
ALL_CATEGORIES = {
    **FOR_SALE_CATEGORIES,
    **HOUSING_CATEGORIES, 
    **JOBS_CATEGORIES,
}


def get_category_code(category_name: str) -> str:
    """
    Get the category code for a given category name.
    
    Args:
        category_name: Human-readable category name
        
    Returns:
        Category code (e.g., 'pta' for 'auto parts')
        
    Raises:
        KeyError: If category name is not found
    """
    return ALL_CATEGORIES[category_name.lower()]


def get_category_name(category_code: str) -> str:
    """
    Get the category name for a given category code.
    
    Args:
        category_code: Category code (e.g., 'pta')
        
    Returns:
        Human-readable category name
        
    Raises:
        ValueError: If category code is not found
    """
    for name, code in ALL_CATEGORIES.items():
        if code == category_code:
            return name
    raise ValueError(f"Category code '{category_code}' not found")


def list_for_sale_categories() -> dict:
    """Get all For Sale categories."""
    return FOR_SALE_CATEGORIES.copy()


def list_housing_categories() -> dict:
    """Get all Housing categories."""
    return HOUSING_CATEGORIES.copy()


def list_jobs_categories() -> dict:
    """Get all Jobs categories."""
    return JOBS_CATEGORIES.copy()


# Quick reference for commonly used automotive categories
AUTOMOTIVE_CATEGORIES = {
    "cars+trucks": "cta",
    "auto parts": "pta", 
    "motorcycles": "mca",
    "motorcycle parts": "mpa",
    "wheels+tires": "wta",
    "boats": "boo",
    "boat parts": "bpa",
    "rvs+camp": "rva",
    "atv/utv/snow": "sna",
    "trailers": "tra",
    "heavy equipment": "hva",
}

# Quick reference for electronics categories
ELECTRONICS_CATEGORIES = {
    "electronics": "ela",
    "computers": "sya",
    "computer parts": "syp", 
    "cell phones": "moa",
    "photo+video": "pha",
    "video gaming": "vga",
}

# Quick reference for home categories  
HOME_CATEGORIES = {
    "furniture": "fua",
    "appliances": "ppa",
    "household": "hsa",
    "tools": "tla",
    "materials": "maa",
    "farm+garden": "gra",
}