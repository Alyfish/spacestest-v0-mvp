"""
PSL-based domain normalization and affiliate/shortener detection.
"""

from functools import lru_cache
from typing import Tuple
from urllib.parse import urlparse

import tldextract


# =============================================================================
# Domain Sets and Mappings
# =============================================================================

# Affiliate network domains (resolve further, not final destination)
AFFILIATE_NETWORK_DOMAINS = {
    # Rakuten / Linkshare
    "click.linksynergy.com",
    "linksynergy.com",
    "rakutenadvertising.com",
    # RewardStyle / LTK
    "rstyle.me",
    "liketoknow.it",
    "shopltk.com",
    # ShareASale
    "shareasale.com",
    "shareasale-analytics.com",
    # Commission Junction / CJ
    "commission-junction.com",
    "cj.com",
    "anrdoezrs.net",
    "dpbolvw.net",
    "jdoqocy.com",
    "kqzyfj.com",
    "tkqlhce.com",
    # Pepperjam
    "pntra.com",
    "pjatr.com",
    "pjtra.com",
    "gopjn.com",
    # Skimlinks
    "skimlinks.com",
    "go.skimresources.com",
    "redirectingat.com",
    # Impact
    "impact.com",
    "sjv.io",
    "evyy.net",
    "pxf.io",
    # AvantLink
    "avantlink.com",
    # Awin
    "awin1.com",
    "zenaps.com",
    # Webgains
    "webgains.com",
    "track.webgains.com",
    # Partnerize
    "partnerize.com",
    "prf.hn",
    # FlexOffers
    "flexoffers.com",
    "track.flexlinkspro.com",
    # Other common affiliate redirectors
    "go.redirectingat.com",
    "narrativ.com",
    "shop-links.co",
    "howl.me",
    "bam-x.com",
}

# URL shorteners (always resolve)
SHORTENER_DOMAINS = {
    "bit.ly",
    "t.co",
    "ow.ly",
    "goo.gl",
    "tinyurl.com",
    "is.gd",
    "buff.ly",
    "rebrand.ly",
    "short.io",
    "cutt.ly",
    "tiny.cc",
    "soo.gd",
    "s.id",
    "clck.ru",
    # Amazon shorteners
    "amzn.to",
    "a.co",
    # Social media shorteners
    "fb.me",
    "youtu.be",
    "redd.it",
    "pin.it",
}

# Retailer aliases (map to canonical domain)
RETAILER_ALIASES = {
    "amzn.to": "amazon.com",
    "amzn.com": "amazon.com",
    "a.co": "amazon.com",
    "amazon.co.uk": "amazon.co.uk",
    "amazon.ca": "amazon.ca",
    "amazon.de": "amazon.de",
    "amazon.fr": "amazon.fr",
    "amazon.es": "amazon.es",
    "amazon.it": "amazon.it",
    "amazon.co.jp": "amazon.co.jp",
    "amazon.com.au": "amazon.com.au",
}

# Known retailer display names
RETAILER_DISPLAY_NAMES = {
    "amazon.com": "Amazon",
    "amazon.co.uk": "Amazon UK",
    "amazon.ca": "Amazon Canada",
    "amazon.de": "Amazon Germany",
    "amazon.fr": "Amazon France",
    "amazon.es": "Amazon Spain",
    "amazon.it": "Amazon Italy",
    "amazon.co.jp": "Amazon Japan",
    "amazon.com.au": "Amazon Australia",
    "wayfair.com": "Wayfair",
    "ikea.com": "IKEA",
    "target.com": "Target",
    "walmart.com": "Walmart",
    "homedepot.com": "Home Depot",
    "lowes.com": "Lowe's",
    "westelm.com": "West Elm",
    "potterybarn.com": "Pottery Barn",
    "crateandbarrel.com": "Crate & Barrel",
    "cb2.com": "CB2",
    "overstock.com": "Overstock",
    "bedbathandbeyond.com": "Bed Bath & Beyond",
    "pier1.com": "Pier 1",
    "zgallerie.com": "Z Gallerie",
    "article.com": "Article",
    "allmodern.com": "AllModern",
    "jossandmain.com": "Joss & Main",
    "birchbox.com": "Birchbox",
    "anthropologie.com": "Anthropologie",
    "urbanoutfitters.com": "Urban Outfitters",
    "etsy.com": "Etsy",
    "ebay.com": "eBay",
    "costco.com": "Costco",
    "bestbuy.com": "Best Buy",
    "macys.com": "Macy's",
    "nordstrom.com": "Nordstrom",
    "bloomingdales.com": "Bloomingdale's",
    "sephora.com": "Sephora",
    "ulta.com": "Ulta",
    "kohls.com": "Kohl's",
    "jcpenney.com": "JCPenney",
    "williams-sonoma.com": "Williams Sonoma",
    "restorationhardware.com": "Restoration Hardware",
    "rh.com": "RH",
    "ballarddesigns.com": "Ballard Designs",
    "serenaandlily.com": "Serena & Lily",
    "luluandgeorgia.com": "Lulu and Georgia",
    "onekingslane.com": "One Kings Lane",
    "burrow.com": "Burrow",
    "floyd.com": "Floyd",
    "thuma.co": "Thuma",
}


# =============================================================================
# Domain Functions
# =============================================================================

@lru_cache(maxsize=10000)
def normalize_domain(url: str) -> Tuple[str, str]:
    """
    Extract and normalize domain using Public Suffix List.

    Args:
        url: Full URL or domain string

    Returns:
        Tuple of (normalized_root_domain, display_name)
        e.g., ("amazon.com", "Amazon")
    """
    # Handle cases where url might just be a domain
    if not url.startswith(('http://', 'https://')):
        url = f"https://{url}"

    extracted = tldextract.extract(url)

    # Build registered domain
    if extracted.suffix:
        registered_domain = f"{extracted.domain}.{extracted.suffix}".lower()
    else:
        registered_domain = extracted.domain.lower()

    # Check aliases first
    if registered_domain in RETAILER_ALIASES:
        registered_domain = RETAILER_ALIASES[registered_domain]

    # Get display name
    display_name = get_retailer_display_name(registered_domain)

    return registered_domain, display_name


def get_root_domain(url: str) -> str:
    """
    Get just the root domain without display name.

    Args:
        url: Full URL

    Returns:
        Root domain string
    """
    domain, _ = normalize_domain(url)
    return domain


def is_affiliate_network(url: str) -> bool:
    """
    Check if URL is from a known affiliate network.

    Args:
        url: Full URL to check

    Returns:
        True if URL is from an affiliate network
    """
    try:
        parsed = urlparse(url.lower())
        host = parsed.netloc.replace("www.", "")

        # Check exact match
        if host in AFFILIATE_NETWORK_DOMAINS:
            return True

        # Check if any affiliate domain is a suffix
        for affiliate_domain in AFFILIATE_NETWORK_DOMAINS:
            if host.endswith(affiliate_domain):
                return True

        return False
    except Exception:
        return False


def is_shortener(url: str) -> bool:
    """
    Check if URL is from a known URL shortener.

    Args:
        url: Full URL to check

    Returns:
        True if URL is from a URL shortener
    """
    try:
        parsed = urlparse(url.lower())
        host = parsed.netloc.replace("www.", "")

        return host in SHORTENER_DOMAINS
    except Exception:
        return False


def is_google_domain(url: str) -> bool:
    """
    Check if URL is a Google domain.

    Args:
        url: Full URL to check

    Returns:
        True if URL is from Google
    """
    try:
        extracted = tldextract.extract(url)
        return extracted.domain.lower() == "google"
    except Exception:
        return False


def get_retailer_display_name(domain: str) -> str:
    """
    Get human-readable display name for a domain.

    Args:
        domain: Root domain (e.g., "amazon.com")

    Returns:
        Display name (e.g., "Amazon")
    """
    domain = domain.lower()

    # Check exact match
    if domain in RETAILER_DISPLAY_NAMES:
        return RETAILER_DISPLAY_NAMES[domain]

    # Handle Amazon regional domains
    if domain.startswith("amazon."):
        region = domain.replace("amazon.", "").upper()
        return f"Amazon {region}" if region != "COM" else "Amazon"

    # Default: capitalize first letter of domain
    base_domain = domain.split('.')[0]
    return base_domain.title()


def should_resolve_further(url: str) -> bool:
    """
    Check if a URL should be resolved further (not a final destination).

    Args:
        url: URL to check

    Returns:
        True if URL is from affiliate network, shortener, or Google
    """
    return is_affiliate_network(url) or is_shortener(url) or is_google_domain(url)


def extract_full_domain_info(url: str) -> dict:
    """
    Extract comprehensive domain information from a URL.

    Args:
        url: Full URL

    Returns:
        Dict with subdomain, domain, suffix, root_domain, display_name
    """
    extracted = tldextract.extract(url)
    root_domain, display_name = normalize_domain(url)

    return {
        "subdomain": extracted.subdomain,
        "domain": extracted.domain,
        "suffix": extracted.suffix,
        "root_domain": root_domain,
        "display_name": display_name,
        "is_affiliate_network": is_affiliate_network(url),
        "is_shortener": is_shortener(url),
        "is_google": is_google_domain(url),
    }
