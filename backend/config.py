"""
Feature Flags and Configuration for Product Matching Pipeline

This module provides centralized configuration for the furniture product matching
system. Feature flags allow gradual rollout and easy rollback of improvements.
"""

import logging
import os
import re


class FeatureFlags:
    """Feature flags for controlling product matching behavior.

    All flags default to values that improve matching quality while maintaining
    backward compatibility. Set environment variables to override defaults.
    """

    # Phase 1: Safe internal improvements (default ON)

    # Use google_shopping_light API for direct retailer URLs instead of Google Shopping redirects
    # This returns 'link' field with actual retailer URLs (wayfair.com, target.com, etc.)
    # instead of broken google.com/shopping/product/... URLs
    USE_SHOPPING_LIGHT_API = os.getenv("USE_SHOPPING_LIGHT_API", "true").lower() == "true"

    # CLIP Model - Use larger, more accurate model
    # +5-8% matching accuracy, ~2.5x slower (acceptable trade-off)
    USE_CLIP_LARGE = os.getenv("USE_CLIP_LARGE", "true").lower() == "true"

    # Vocabulary expansion - More specific furniture/style/material/color terms
    EXPANDED_VOCABULARY = os.getenv("EXPANDED_VOCABULARY", "true").lower() == "true"

    # Enhanced type guard - Better synonym matching and hard negative filtering
    ENHANCED_TYPE_GUARD = os.getenv("ENHANCED_TYPE_GUARD", "true").lower() == "true"

    # Store trust scores - Weight results by retailer quality
    STORE_TRUST_SCORES = os.getenv("STORE_TRUST_SCORES", "true").lower() == "true"

    # Phase 2: May affect result ordering (default OFF for safety)

    # Multi-signal ranking - Continuous scoring instead of binary drop/boost
    MULTI_SIGNAL_RANKING = os.getenv("MULTI_SIGNAL_RANKING", "false").lower() == "true"

    # Search strategy: "images_first_v2" (Google Images primary) or "shopping_first_v1" (old)
    SEARCH_STRATEGY = os.getenv("SEARCH_STRATEGY", "images_first_v2")


# Known retailer domains — prioritize image results from these sources
RETAILER_DOMAINS = {
    "wayfair.com", "amazon.com", "target.com", "walmart.com", "ikea.com",
    "cb2.com", "potterybarn.com", "westelm.com", "overstock.com",
    "homedepot.com", "lowes.com", "etsy.com", "pier1.com",
    "crateandbarrel.com", "allmodern.com", "jossandmain.com",
    "ashleyfurniture.com", "article.com", "burrow.com", "wayfair.ca",
    "structube.com", "roveconcepts.com", "urbanoutfitters.com",
    "anthropologie.com", "zgallerie.com", "roomandboard.com",
}


# Store trust scores for ranking quality retailers higher
# Scores reflect retailer reliability for furniture purchases (0.0-1.0)
STORE_TRUST_SCORES = {
    # Premium furniture retailers (high trust)
    "crate & barrel": 0.92,
    "crate and barrel": 0.92,
    "west elm": 0.90,
    "cb2": 0.90,
    "article": 0.90,
    "pottery barn": 0.88,
    "room & board": 0.90,
    "design within reach": 0.90,
    "rejuvenation": 0.88,
    "serena & lily": 0.88,

    # Mid-tier furniture retailers
    "wayfair": 0.85,
    "allmodern": 0.85,
    "joss & main": 0.83,
    "overstock": 0.80,
    "ikea": 0.80,
    "world market": 0.80,
    "anthropologie": 0.82,
    "urban outfitters": 0.78,

    # Big box retailers (moderate trust for furniture)
    "target": 0.75,
    "amazon": 0.70,
    "walmart": 0.65,
    "home depot": 0.72,
    "lowe's": 0.72,

    # Specialty retailers
    "ethan allen": 0.88,
    "arhaus": 0.87,
    "z gallerie": 0.82,
    "ashley furniture": 0.75,
    "rooms to go": 0.73,
    "living spaces": 0.75,
    "bob's discount furniture": 0.68,

    # Default for unknown stores
    "default": 0.70,
}


# Expanded furniture vocabularies for CLIP analysis
FURNITURE_TYPES_EXPANDED = [
    # Seating - comprehensive
    "sofa", "couch", "sectional", "loveseat", "settee",
    "chair", "armchair", "accent chair", "lounge chair", "club chair",
    "recliner", "rocker", "rocking chair", "glider",
    "dining chair", "desk chair", "office chair", "task chair",
    "stool", "bar stool", "counter stool",
    "bench", "ottoman", "pouf", "footstool",

    # Tables - comprehensive
    "table", "coffee table", "cocktail table",
    "dining table", "kitchen table", "breakfast table",
    "side table", "end table", "accent table",
    "console table", "sofa table", "entry table", "hallway table",
    "nightstand", "bedside table", "night table",
    "desk", "writing desk", "computer desk", "secretary desk",
    "vanity", "vanity table", "dressing table",

    # Storage - comprehensive
    "cabinet", "storage cabinet", "media cabinet", "tv stand",
    "dresser", "chest of drawers", "highboy", "lowboy",
    "sideboard", "buffet", "credenza", "hutch",
    "bookcase", "bookshelf", "shelving", "wall shelf", "floating shelf",
    "armoire", "wardrobe", "closet organizer",
    "filing cabinet", "storage bin",

    # Beds - comprehensive
    "bed", "bed frame", "platform bed", "canopy bed", "four poster bed",
    "headboard", "footboard",
    "daybed", "trundle bed", "bunk bed", "loft bed",
    "murphy bed", "sleeper sofa", "sofa bed",

    # Lighting - comprehensive
    "lamp", "table lamp", "desk lamp", "bedside lamp",
    "floor lamp", "arc lamp", "torchiere",
    "pendant light", "chandelier", "ceiling light",
    "wall sconce", "wall lamp",

    # Rugs and textiles
    "rug", "area rug", "runner", "carpet", "mat",
]

STYLES_EXPANDED = [
    # Core styles
    "modern", "contemporary", "traditional", "transitional",
    "mid-century", "mid-century modern", "mcm",
    "minimalist", "scandinavian", "nordic",

    # Period styles
    "vintage", "retro", "antique",
    "art deco", "art nouveau", "victorian", "georgian",
    "colonial", "french country", "english cottage",

    # Regional/cultural styles
    "bohemian", "boho", "eclectic",
    "coastal", "nautical", "beach house",
    "farmhouse", "rustic", "country", "cottage",
    "industrial", "loft", "urban",
    "japandi", "zen", "asian-inspired", "wabi-sabi",
    "mediterranean", "spanish", "moroccan", "tuscan",
]

MATERIALS_EXPANDED = [
    # Woods - specific types
    "wood", "wooden", "solid wood", "hardwood",
    "oak", "white oak", "red oak",
    "walnut", "black walnut",
    "maple", "cherry", "mahogany", "teak", "acacia",
    "pine", "cedar", "birch", "ash", "elm", "beech",
    "bamboo", "rattan", "wicker", "cane",
    "reclaimed wood", "distressed wood", "weathered wood",

    # Metals
    "metal", "iron", "wrought iron", "cast iron",
    "steel", "stainless steel", "brushed steel",
    "brass", "bronze", "copper", "gold", "chrome", "nickel",
    "aluminum",

    # Upholstery fabrics
    "fabric", "upholstered",
    "velvet", "velour",
    "linen", "cotton", "canvas",
    "leather", "faux leather", "vegan leather", "bonded leather",
    "suede", "microfiber", "chenille",
    "boucle", "bouclé", "sherpa", "teddy",
    "tweed", "herringbone", "performance fabric",

    # Hard surfaces
    "glass", "tempered glass", "frosted glass",
    "marble", "granite", "quartz", "stone", "travertine", "slate",
    "concrete", "cement", "terrazzo",
    "ceramic", "porcelain", "tile",
    "plastic", "acrylic", "lucite", "resin",
    "lacquer", "lacquered",
]

COLORS_EXPANDED = [
    # Neutrals - detailed
    "white", "off-white", "ivory", "cream", "bone", "eggshell",
    "black", "charcoal", "ebony",
    "gray", "grey", "light gray", "dark gray", "slate", "pewter", "graphite",
    "beige", "tan", "taupe", "greige", "sand", "khaki", "camel",
    "brown", "chocolate", "espresso", "mocha", "coffee", "walnut", "chestnut",
    "cognac", "caramel", "amber", "rust", "terracotta", "sienna",

    # Blues
    "blue", "navy", "navy blue", "dark blue", "royal blue",
    "light blue", "sky blue", "baby blue", "powder blue",
    "teal", "turquoise", "aqua", "cyan", "cerulean", "indigo",

    # Greens
    "green", "dark green", "forest green", "hunter green", "emerald",
    "sage", "sage green", "olive", "olive green", "moss", "fern",
    "mint", "seafoam", "eucalyptus",

    # Warm colors
    "red", "burgundy", "wine", "maroon", "crimson", "ruby",
    "orange", "burnt orange", "coral", "peach", "apricot",
    "yellow", "mustard", "gold", "golden", "honey", "ochre",
    "pink", "blush", "rose", "dusty pink", "mauve",

    # Purples
    "purple", "plum", "eggplant", "aubergine", "violet", "lilac", "lavender",

    # Natural tones
    "natural", "nude", "neutral", "earthy", "earth tone",
]

# Texture and pattern descriptors for enhanced matching
TEXTURES = [
    "tufted", "button-tufted", "channel-tufted",
    "quilted", "padded", "cushioned",
    "woven", "braided", "knitted", "crocheted",
    "ribbed", "fluted", "grooved", "paneled",
    "smooth", "polished", "matte", "satin", "glossy",
    "textured", "embossed", "carved", "etched",
    "distressed", "weathered", "aged", "antique finish",
]

PATTERNS = [
    "solid", "plain",
    "striped", "pinstripe", "awning stripe",
    "geometric", "chevron", "herringbone", "zigzag",
    "floral", "botanical", "leaf pattern",
    "abstract", "modern pattern",
    "plaid", "checkered", "gingham",
    "ikat", "suzani", "damask", "paisley",
]


# Furniture synonym mapping for type guard
FURNITURE_SYNONYMS = {
    "sofa": ["couch", "loveseat", "settee", "sectional", "sleeper", "sofa bed"],
    "couch": ["sofa", "loveseat", "settee", "sectional"],
    "chair": ["armchair", "accent chair", "lounge chair", "club chair", "recliner", "rocker"],
    "armchair": ["chair", "accent chair", "lounge chair", "club chair"],
    "table": ["desk", "stand", "console"],
    "coffee table": ["cocktail table", "tea table"],
    "side table": ["end table", "accent table", "lamp table"],
    "nightstand": ["bedside table", "night table", "bedside stand"],
    "console table": ["sofa table", "entry table", "hallway table", "entryway table"],
    "shelf": ["bookcase", "shelving", "bookshelf", "etagere", "étagère", "wall shelf"],
    "bookcase": ["bookshelf", "shelf", "shelving", "etagere"],
    "bed": ["bedframe", "bed frame", "headboard", "platform bed", "sleigh bed"],
    "dresser": ["chest of drawers", "bureau", "chest", "highboy"],
    "cabinet": ["cupboard", "sideboard", "buffet", "credenza", "hutch", "armoire"],
    "lamp": ["light", "lighting", "fixture"],
    "floor lamp": ["standing lamp", "torchiere", "arc lamp"],
    "table lamp": ["desk lamp", "bedside lamp"],
    "rug": ["carpet", "area rug", "runner", "mat"],
    "ottoman": ["footstool", "pouf", "hassock", "footrest"],
    "bench": ["settee", "banquette", "entry bench"],
    "stool": ["bar stool", "counter stool", "barstool"],
    "desk": ["writing desk", "work desk", "computer desk", "secretary"],
    "tv stand": ["media console", "entertainment center", "media cabinet", "tv console"],
}

# Hard negative keywords that indicate non-product pages
HARD_NEGATIVES = [
    # Content/editorial
    "decor", "how to", "ideas", "tutorial", "guide", "inspiration",
    "tips", "tricks", "diy", "blog", "article", "review", "reviews",
    "best of", "top 10", "roundup", "collection of",

    # Non-furniture items (keep "only" variants to exclude covers without products)
    "poster", "print", "canvas", "wall art", "artwork", "painting",
    "pillow cover only", "cushion cover only", "slipcover only",
    "curtain", "drape",
    # Note: "pillow", "blanket", "throw" are allowed for bed component searches

    # Service-related
    "assembly", "installation", "repair", "cleaning",
    "rental", "rent", "lease",

    # Generic/non-specific
    "accessories", "misc", "lot of", "bundle",
]


# ============================================================
# Product Search Exclusions - Filter out Plans, Blueprints, PDFs
# These are NOT actual furniture products - they are drawings/documents
# ============================================================

_product_filter_logger = logging.getLogger("spaces_ai.product_filter")

# Tier 1: Phrase matches — high-signal multi-word phrases, always filter via substring
EXCLUDED_PHRASES = [
    "floor plan", "building plan", "woodworking plan",
    "furniture plan", "sewing pattern", "pattern book",
    "pdf download", "instant download", "digital download",
    "printable", "e-book", "ebook", "svg",
    "cut list", "cutting list",
    "diy guide", "diy project", "build your own",
    "how to build", "step by step",
]

# Tier 2: Single words — only match at word boundaries so "platform" doesn't match "plan"
EXCLUDED_WORD_BOUNDARY = [
    "plan", "plans",
    "blueprint", "blueprints",
    "template", "templates",
    "pattern", "patterns",
    "pdf",
]

# Pre-compile word-boundary regexes for performance
_WORD_BOUNDARY_PATTERNS = [
    (word, re.compile(rf"\b{re.escape(word)}\b", re.IGNORECASE))
    for word in EXCLUDED_WORD_BOUNDARY
]


def is_valid_product(title: str) -> bool:
    """
    Filter out plans, blueprints, PDFs - we need real furniture photos.

    Uses two-tier filtering:
    1. Phrase match (substring) for high-signal multi-word terms
    2. Word-boundary match for single words to avoid false positives
       (e.g. "Platform Bed" won't match "plan")

    Args:
        title: Product title from search results

    Returns:
        True if the product appears to be actual furniture (not a plan/blueprint)
    """
    if not title:
        return True  # Empty titles pass through for other filters

    title_lower = title.lower()

    # Tier 1: phrase match (substring)
    for phrase in EXCLUDED_PHRASES:
        if phrase in title_lower:
            _product_filter_logger.debug(
                "Filtered '%s': matched phrase '%s'", title, phrase
            )
            return False

    # Tier 2: word-boundary match
    for word, pattern in _WORD_BOUNDARY_PATTERNS:
        if pattern.search(title_lower):
            _product_filter_logger.debug(
                "Filtered '%s': matched word-boundary '%s'", title, word
            )
            return False

    return True


# Bed component configuration for composite furniture detection
# When a bed is detected, search for these additional components
BED_COMPONENTS = {
    "bed_frame": {
        "search_terms": ["bed frame", "platform bed", "bed", "headboard"],
        "synonyms": ["bedframe", "bed frame", "platform bed", "sleigh bed", "panel bed"],
    },
    "bedding": {
        "search_terms": ["comforter", "duvet", "quilt", "bedding set"],
        "synonyms": ["comforter", "duvet", "duvet cover", "quilt", "bedspread", "bed cover"],
    },
    "throw": {
        "search_terms": ["throw blanket", "bed throw", "blanket"],
        "synonyms": ["throw", "throw blanket", "blanket", "bed blanket", "knit throw"],
    },
    "pillows": {
        "search_terms": ["bed pillow", "decorative pillow", "pillow set"],
        "synonyms": ["pillow", "pillows", "throw pillow", "accent pillow", "bed pillow", "decorative pillow"],
    },
}


# ============================================================
# Bed Detection Configuration
# Two-stage filtering to distinguish actual beds from bedroom accessories
# Only actual sleeping furniture should trigger bed component search
# ============================================================

# Primary bed indicators - terms that definitively indicate sleeping furniture
# These are checked AFTER exclusions, so multi-word terms are preferred
BED_PRIMARY_INDICATORS = [
    # Standard bed types
    "bed frame", "platform bed", "sleigh bed", "canopy bed",
    "four poster", "poster bed", "panel bed", "upholstered bed",
    "storage bed", "captain's bed", "trundle bed", "bunk bed",
    "murphy bed", "daybed", "sleeper sofa", "sofa bed",
    "headboard", "footboard", "mattress", "loft bed",
    "king bed", "queen bed", "twin bed", "full bed",
    # Tufted/styled bed variants (common Gemini responses)
    "tufted bed", "channel tufted bed", "button tufted bed",
    "wingback bed", "wingback headboard", "tufted headboard",
    "upholstered headboard", "velvet bed", "linen bed",
    "fabric bed", "leather bed", "wood bed", "metal bed",
]

# Exclusion terms - if these appear in the label, it's NOT a bed
# Even if "bed" appears elsewhere in the string
# Comprehensive list of all non-bed furniture types
BED_EXCLUSION_TERMS = [
    # Lighting
    "lamp", "light", "chandelier", "sconce", "pendant", "fixture",
    # Tables
    "table", "desk", "console", "coffee", "side", "end", "dining",
    # Seating (non-bed)
    "chair", "sofa", "couch", "loveseat", "sectional", "recliner",
    "bench", "stool", "ottoman", "pouf", "armchair", "rocker",
    # Storage
    "dresser", "cabinet", "shelf", "bookcase", "wardrobe", "armoire",
    "credenza", "sideboard", "buffet", "hutch", "chest",
    # Decor
    "rug", "carpet", "curtain", "drape", "mirror", "clock", "art",
    "plant", "vase", "picture", "painting", "sculpture", "frame",
    # Bedroom accessories (not the bed itself)
    "beside", "bedside", "side", "night", "reading", "accent",
    # Bedding items (accessories, not furniture)
    "pillow", "cushion", "throw", "blanket", "duvet", "comforter",
    "sheet", "coverlet", "quilt", "linens", "bedspread", "bedding",
    # Other furniture
    "vanity", "stand", "rack", "cart", "tv", "media", "entertainment",
]

# Compound terms that are definitively NOT beds (checked first for speed)
NOT_BED_COMPOUND_TERMS = [
    # Bedroom furniture (not beds)
    "bedside lamp", "bedside table", "bedside cabinet", "bedside stand",
    "bedroom lamp", "bedroom dresser", "bedroom rug", "bedroom chair",
    "bedroom curtain", "bedroom mirror", "bedroom plant", "bedroom bench",
    "bedroom vanity", "bedroom cabinet", "bedroom shelf", "bedroom art",
    "nightstand", "night stand", "night table",
    # Lamps
    "reading lamp", "table lamp", "floor lamp", "desk lamp", "wall lamp",
    "pendant lamp", "ceiling lamp", "arc lamp",
    # Living room furniture
    "coffee table", "side table", "end table", "console table",
    "tv stand", "media console", "entertainment center",
    # Bedding accessories
    "throw pillow", "bed pillow", "decorative pillow", "accent pillow",
    "throw blanket", "bed throw", "bed blanket",
    # Other
    "picture frame", "photo frame", "wall art", "wall mirror",
]


# ============================================================
# Quality Retailer Domains for Trending Products
# These are retailers known for curated, aesthetic products
# Priority is visual quality and unique designs, not just brand prestige
# ============================================================

QUALITY_RETAILER_DOMAINS = [
    # Art & Wall Decor Specialists
    "drool.com",
    "olivergal.com", 
    "art.com",
    "minted.com",
    "society6.com",
    "icanvas.com",
    "artfinder.com",
    "saatchiart.com",
    
    # Curated Home Decor
    "anthropologie.com",
    "urbanoutfitters.com",
    "cb2.com",
    "westelm.com",
    "article.com",
    "crateandbarrel.com",
    "roomandboard.com",
    "designwithinreach.com",
    "serenaandlily.com",
    "burkedecor.com",
    
    # Specialty Decor
    "etsy.com",
    "1stdibs.com",
    "chairish.com",
    "worldmarket.com",
    "zgallerie.com",
    "potterybarn.com",
    "rejuvenation.com",
    "lumens.com",
    
    # General with good curation
    "wayfair.com",
    "allmodern.com",
    "houzz.com",
    "target.com",
    "amazon.com",
]

# Store quality scores for ranking (0.0-1.0)
# Higher = better visual curation and product quality
QUALITY_RETAILER_SCORES = {
    # Art specialists (highest)
    "drool": 0.95,
    "oliver gal": 0.93,
    "olivergal": 0.93,
    "minted": 0.92,
    "art.com": 0.90,
    "saatchi art": 0.90,
    "society6": 0.88,
    "icanvas": 0.87,
    
    # Premium curated
    "anthropologie": 0.92,
    "cb2": 0.91,
    "west elm": 0.90,
    "article": 0.90,
    "room & board": 0.90,
    "design within reach": 0.89,
    "serena & lily": 0.88,
    "rejuvenation": 0.88,
    
    # Quality specialty
    "1stdibs": 0.93,
    "chairish": 0.88,
    "burke decor": 0.87,
    "z gallerie": 0.85,
    "etsy": 0.80,  # Variable quality
    
    # Good mid-tier
    "crate & barrel": 0.87,
    "pottery barn": 0.85,
    "world market": 0.82,
    "urban outfitters": 0.80,
    "lumens": 0.85,
    
    # General retailers
    "wayfair": 0.78,
    "allmodern": 0.80,
    "target": 0.75,
    "amazon": 0.65,  # Very variable quality
    
    "default": 0.70,
}


# ============================================================
# Non-Retailer Domain Blocklist
# These domains never sell furniture - always filter them from reverse image search
# ============================================================

NON_RETAILER_BLOCKLIST = {
    # Social Media
    "instagram.com",
    "pinterest.com",
    "pinterest.co.uk",
    "pin.it",
    "facebook.com",
    "fb.com",
    "twitter.com",
    "x.com",
    "tiktok.com",
    "youtube.com",
    "youtu.be",
    "linkedin.com",
    "reddit.com",
    "tumblr.com",

    # Blogs & Editorial Platforms
    "medium.com",
    "blogspot.com",
    "wordpress.com",
    "wordpress.org",
    "blogger.com",
    "substack.com",
    "wix.com",
    "squarespace.com",

    # Magazines & Editorial Sites (feature furniture, don't sell it)
    "architecturaldigest.com",
    "elledecor.com",
    "housebeautiful.com",
    "apartmenttherapy.com",
    "dwell.com",
    "dezeen.com",
    "designmilk.com",
    "mydomaine.com",
    "domino.com",
    "veranda.com",
    "hgtv.com",
    "bhg.com",
    "countryliving.com",
    "realsimple.com",
    "marthastewart.com",
    "thekitchn.com",
    "remodelista.com",
    "curbed.com",
    "lonny.com",

    # Woodworking / Plans (NOT product sellers)
    "finewoodworking.com",
    "woodmagazine.com",
    "popularwoodworking.com",
    "woodworkersjournal.com",
    "woodsmith.com",
    "ana-white.com",
    "thedesignconfidential.com",
    "shanty-2-chic.com",

    # Stock Photos / Image Sites
    "shutterstock.com",
    "istockphoto.com",
    "gettyimages.com",
    "unsplash.com",
    "pexels.com",
    "pixabay.com",
    "depositphotos.com",
    "123rf.com",
    "alamy.com",
    "dreamstime.com",

    # Review / Comparison Sites (may link but don't sell)
    "thespruce.com",
    "bobvila.com",
    "consumerreports.org",
    "nytimes.com",
    "wirecutter.com",
    "cnet.com",
    "tomsguide.com",
    "reviewed.com",
    "goodhousekeeping.com",

    # Classifieds / Used Items
    "craigslist.org",
    "kijiji.ca",
    "gumtree.com",
    "offerup.com",
    "letgo.com",
    "mercari.com",
    "poshmark.com",
    "thredup.com",
}

# Title patterns that indicate non-product content (DIY plans, tutorials, etc.)
NON_PRODUCT_TITLE_PATTERNS = [
    "diy plan",
    "diy project",
    "woodworking plan",
    "build plan",
    "furniture plan",
    "free plan",
    "pdf plan",
    "blueprint",
    "how to build",
    "how to make",
    "tutorial",
    "step by step",
    "building instructions",
    "diy guide",
    "craft project",
    "wood plan",
    "cut list",
    "materials list",
]


def is_blocked_domain(url: str) -> bool:
    """
    Check if URL is from a non-retailer domain that should be blocked.

    Args:
        url: URL to check

    Returns:
        True if URL should be blocked (not a retailer)
    """
    if not url:
        return False

    try:
        from urllib.parse import urlparse
        parsed = urlparse(url.lower())
        domain = parsed.netloc.replace("www.", "")

        # Check exact match
        if domain in NON_RETAILER_BLOCKLIST:
            return True

        # Check if any blocklist domain is a suffix (for subdomains)
        for blocked in NON_RETAILER_BLOCKLIST:
            if domain.endswith(f".{blocked}"):
                return True

        return False
    except Exception:
        return False


def is_non_product_title(title: str) -> bool:
    """
    Check if title indicates non-product content (DIY plans, tutorials, etc.).

    Args:
        title: Product/result title to check

    Returns:
        True if title suggests this is NOT a purchasable product
    """
    if not title:
        return False

    title_lower = title.lower()
    return any(pattern in title_lower for pattern in NON_PRODUCT_TITLE_PATTERNS)


# ============================================================
# AI Product Curation Settings
# Controls how Gemini Vision evaluates product quality
# ============================================================

AI_PRODUCT_CURATION = {
    # Enable/disable AI curation (can be overridden by env var)
    "enabled": True,

    # Minimum quality score to include product (0.0-1.0)
    "min_quality_score": 0.5,

    # Maximum products to evaluate per category (cost control)
    "max_products_to_evaluate": 16,

    # Products per Gemini batch request
    "batch_size": 8,

    # Score weighting (must sum to 1.0)
    "score_weights": {
        "visual_quality": 0.35,     # Image clarity, professional photography
        "design_aesthetic": 0.35,   # Modern, premium look vs generic
        "style_match": 0.30,        # Fits requested style/room
    },

    # Minimum image dimensions to consider (pixels)
    "min_image_dimension": 200,
}


# ============================================================
# URL Normalizer Configuration
# Settings for the Universal Product Link Normalizer
# ============================================================

URL_NORMALIZER_CONFIG = {
    # Enable/disable the URL normalizer feature
    "enabled": os.getenv("URL_NORMALIZER_ENABLED", "true").lower() == "true",

    # Concurrency settings
    "max_concurrent": int(os.getenv("URL_NORMALIZER_MAX_CONCURRENT", "15")),
    "max_per_domain": int(os.getenv("URL_NORMALIZER_MAX_PER_DOMAIN", "3")),

    # Timeout settings (milliseconds)
    "default_timeout_ms": int(os.getenv("URL_NORMALIZER_TIMEOUT_MS", "10000")),

    # Redirect resolution
    "max_redirects": 10,

    # Product page classification threshold (0.0-1.0)
    "classification_threshold": 0.50,

    # Google Shopping settings
    "max_shopping_candidates": 3,

    # Cache TTLs (seconds)
    "cache_ttl": {
        "redirect_resolution": 24 * 60 * 60,    # 1 day
        "canonical_extraction": 7 * 24 * 60 * 60,  # 7 days
        "validation_result": 12 * 60 * 60,       # 12 hours
        "shopping_candidates": 3 * 24 * 60 * 60,  # 3 days
    },
}


# ============================================================
# VAPO (Vertex AI Prompt Optimizer) Configuration
# Settings for prompt optimization and A/B testing
# ============================================================

VAPO_CONFIG = {
    # Master feature flag for prompt optimization
    "enabled": os.getenv("VAPO_ENABLED", "true").lower() == "true",

    # GCP project and location for Vertex AI
    "project_id": os.getenv("GOOGLE_CLOUD_PROJECT", None),
    "location": os.getenv("VAPO_LOCATION", "us-central1"),

    # A/B test allocation (0.0-1.0)
    # Fraction of traffic routed to optimized prompts
    "ab_test_allocation": float(os.getenv("VAPO_AB_TEST_ALLOCATION", "0.0")),

    # Enable usage logging for metrics tracking
    "enable_logging": os.getenv("VAPO_ENABLE_LOGGING", "true").lower() == "true",

    # Path to prompts directory (relative to backend/)
    "prompts_dir": os.getenv("VAPO_PROMPTS_DIR", "prompts"),

    # Zero-shot optimization settings
    "zero_shot": {
        # Auto-apply zero-shot suggestions (vs manual review)
        "auto_apply": os.getenv("VAPO_ZERO_SHOT_AUTO_APPLY", "false").lower() == "true",
    },

    # Data-driven optimization settings
    "data_driven": {
        # Minimum samples required for data-driven optimization
        "min_samples": int(os.getenv("VAPO_MIN_SAMPLES", "50")),
        # Default target model for optimization
        "target_model": os.getenv("VAPO_TARGET_MODEL", "gemini-2.5-flash"),
        # QPS limit for optimization jobs
        "qps": int(os.getenv("VAPO_QPS", "1")),
    },

    # Priority prompts for optimization (in order)
    "priority_prompts": [
        "revamp_integration",
        "iterative_surgical",
        "color_agent",
        "style_agent",
        "room_redesign",
        "object_detection",
    ],
}
