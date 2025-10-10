"""
Affiliate Link Converter
Converts regular product URLs to affiliate links for various retailers.
"""

import re
from typing import Dict, List, Optional, Tuple
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
import logging

logger = logging.getLogger(__name__)


class AffiliateClient:
    """Client for converting product URLs to affiliate links."""
    
    # Placeholder affiliate IDs - to be replaced with actual IDs
    AFFILIATE_IDS = {
        "amazon": "YOUR_AMAZON_TAG",
        "ikea": "YOUR_IKEA_AFFILIATE_ID",
        "wayfair": "YOUR_WAYFAIR_AFFILIATE_ID",
        "target": "YOUR_TARGET_AFFILIATE_ID",
        "homedepot": "YOUR_HOMEDEPOT_AFFILIATE_ID",
        "lowes": "YOUR_LOWES_AFFILIATE_ID",
        "walmart": "YOUR_WALMART_AFFILIATE_ID",
        "westelm": "YOUR_WESTELM_AFFILIATE_ID",
        "potterybarn": "YOUR_POTTERYBARN_AFFILIATE_ID",
        "crateandbarrel": "YOUR_CRATEANDBARREL_AFFILIATE_ID",
    }
    
    def __init__(self):
        """Initialize the affiliate client."""
        logger.info("🔗 Affiliate Client initialized")
    
    def identify_retailer(self, url: str) -> Optional[str]:
        """
        Identify the retailer from a product URL.
        
        Args:
            url: Product URL
            
        Returns:
            Retailer name or None if not recognized
        """
        try:
            parsed = urlparse(url.lower())
            domain = parsed.netloc
            
            # Remove www. prefix
            domain = domain.replace("www.", "")
            
            # Map domains to retailer names
            if "amazon.com" in domain or "amzn.to" in domain:
                return "amazon"
            elif "ikea.com" in domain:
                return "ikea"
            elif "wayfair.com" in domain:
                return "wayfair"
            elif "target.com" in domain:
                return "target"
            elif "homedepot.com" in domain:
                return "homedepot"
            elif "lowes.com" in domain:
                return "lowes"
            elif "walmart.com" in domain:
                return "walmart"
            elif "westelm.com" in domain:
                return "westelm"
            elif "potterybarn.com" in domain:
                return "potterybarn"
            elif "crateandbarrel.com" in domain or "cb2.com" in domain:
                return "crateandbarrel"
            else:
                return None
                
        except Exception as e:
            logger.error(f"Error identifying retailer: {e}")
            return None
    
    def extract_product_id(self, url: str, retailer: str) -> Optional[str]:
        """
        Extract product ID from URL based on retailer.
        
        Args:
            url: Product URL
            retailer: Retailer name
            
        Returns:
            Product ID or None
        """
        try:
            if retailer == "amazon":
                # Amazon ASIN pattern: /dp/ASIN or /gp/product/ASIN
                match = re.search(r'/(?:dp|gp/product)/([A-Z0-9]{10})', url)
                return match.group(1) if match else None
                
            elif retailer == "ikea":
                # IKEA product number pattern
                match = re.search(r'/(\d{8,9})/', url)
                return match.group(1) if match else None
                
            elif retailer == "wayfair":
                # Wayfair SKU pattern
                match = re.search(r'sku=([A-Z0-9]+)', url)
                return match.group(1) if match else None
                
            elif retailer == "target":
                # Target product ID pattern: /A-XXXXXXX
                match = re.search(r'/A-(\d+)', url)
                return match.group(1) if match else None
                
            elif retailer == "walmart":
                # Walmart product ID pattern
                match = re.search(r'/(\d{8,9})', url)
                return match.group(1) if match else None
                
            else:
                # Generic: try to find any product ID pattern
                parsed = urlparse(url)
                path_parts = parsed.path.split('/')
                # Return last non-empty path segment
                for part in reversed(path_parts):
                    if part and not part.endswith('.html'):
                        return part
                return None
                
        except Exception as e:
            logger.error(f"Error extracting product ID for {retailer}: {e}")
            return None
    
    def convert_to_affiliate(self, url: str, retailer: str, product_id: Optional[str] = None) -> str:
        """
        Convert a regular product URL to an affiliate URL.
        
        Args:
            url: Original product URL
            retailer: Retailer name
            product_id: Product ID (optional, will be extracted if not provided)
            
        Returns:
            Affiliate URL
        """
        try:
            if not product_id:
                product_id = self.extract_product_id(url, retailer)
            
            affiliate_id = self.AFFILIATE_IDS.get(retailer, "")
            
            if retailer == "amazon":
                # Amazon affiliate link format
                if product_id:
                    return f"https://www.amazon.com/dp/{product_id}?tag={affiliate_id}"
                else:
                    # Add tag to existing URL
                    parsed = urlparse(url)
                    params = parse_qs(parsed.query)
                    params['tag'] = [affiliate_id]
                    new_query = urlencode(params, doseq=True)
                    return urlunparse((parsed.scheme, parsed.netloc, parsed.path, 
                                     parsed.params, new_query, parsed.fragment))
            
            elif retailer == "ikea":
                # IKEA affiliate link (simplified)
                return f"{url}?affiliate_id={affiliate_id}"
            
            elif retailer == "wayfair":
                # Wayfair affiliate link
                return f"{url}&refid={affiliate_id}"
            
            elif retailer == "target":
                # Target affiliate link
                parsed = urlparse(url)
                params = parse_qs(parsed.query)
                params['afid'] = [affiliate_id]
                new_query = urlencode(params, doseq=True)
                return urlunparse((parsed.scheme, parsed.netloc, parsed.path, 
                                 parsed.params, new_query, parsed.fragment))
            
            else:
                # Generic: append affiliate parameter
                separator = "&" if "?" in url else "?"
                return f"{url}{separator}affiliate={affiliate_id}"
                
        except Exception as e:
            logger.error(f"Error converting to affiliate link: {e}")
            return url  # Return original URL if conversion fails
    
    def generate_cart_url(self, retailer: str, product_ids: List[str]) -> str:
        """
        Generate a single cart URL that adds all products at once.
        
        Args:
            retailer: Retailer name
            product_ids: List of product IDs
            
        Returns:
            Cart URL with all products
        """
        affiliate_id = self.AFFILIATE_IDS.get(retailer, "")
        
        if retailer == "amazon":
            # Amazon cart URL format: add multiple ASINs
            # Example: https://www.amazon.com/gp/aws/cart/add.html?ASIN.1=B001&Quantity.1=1&ASIN.2=B002&Quantity.2=1&tag=TAG
            asin_params = []
            for i, asin in enumerate(product_ids, 1):
                asin_params.append(f"ASIN.{i}={asin}&Quantity.{i}=1")
            params_str = "&".join(asin_params)
            return f"https://www.amazon.com/gp/aws/cart/add.html?{params_str}&tag={affiliate_id}"
        
        elif retailer == "ikea":
            # IKEA cart URL (simplified - actual implementation may vary)
            items = ",".join(product_ids)
            return f"https://www.ikea.com/us/en/shoppingcart/?items={items}&affiliate_id={affiliate_id}"
        
        elif retailer == "wayfair":
            # Wayfair cart URL
            skus = ",".join(product_ids)
            return f"https://www.wayfair.com/v/checkout/cart?skus={skus}&refid={affiliate_id}"
        
        elif retailer == "target":
            # Target cart URL
            items = ",".join(product_ids)
            return f"https://www.target.com/co-cart?items={items}&afid={affiliate_id}"
        
        elif retailer == "walmart":
            # Walmart cart URL
            items = ",".join(product_ids)
            return f"https://www.walmart.com/cart?items={items}&affcamid={affiliate_id}"
        
        else:
            # Generic fallback: return first product's affiliate link
            return f"https://{retailer}.com/cart?items={','.join(product_ids)}&affiliate={affiliate_id}"
    
    def get_retailer_display_name(self, retailer: str) -> str:
        """Get display name for retailer."""
        display_names = {
            "amazon": "Amazon",
            "ikea": "IKEA",
            "wayfair": "Wayfair",
            "target": "Target",
            "homedepot": "Home Depot",
            "lowes": "Lowe's",
            "walmart": "Walmart",
            "westelm": "West Elm",
            "potterybarn": "Pottery Barn",
            "crateandbarrel": "Crate & Barrel",
        }
        return display_names.get(retailer, retailer.title())
    
    def process_urls(self, urls: List[str]) -> Dict[str, List[Dict[str, str]]]:
        """
        Process a list of product URLs and group by retailer.
        
        Args:
            urls: List of product URLs
            
        Returns:
            Dictionary mapping retailer to list of product info
        """
        grouped_products = {}
        
        for url in urls:
            url = url.strip()
            if not url:
                continue
            
            retailer = self.identify_retailer(url)
            if not retailer:
                logger.warning(f"Could not identify retailer for URL: {url}")
                continue
            
            product_id = self.extract_product_id(url, retailer)
            affiliate_url = self.convert_to_affiliate(url, retailer, product_id)
            
            if retailer not in grouped_products:
                grouped_products[retailer] = []
            
            grouped_products[retailer].append({
                "original_url": url,
                "affiliate_url": affiliate_url,
                "product_id": product_id or "unknown",
            })
        
        return grouped_products

