"""
Furniture Search Utilities using Exa Neural Search

This module provides a dedicated search client for finding furniture products
using Exa's neural search capabilities with domain filtering.
"""

import os
from typing import List, Dict, Any, Optional
from exa_py import Exa


# Trusted furniture domains for filtering search results
FURNITURE_DOMAINS = [
    "wayfair.com",
    "westelm.com",
    "cb2.com",
    "crateandbarrel.com",
    "potterybarn.com",
    "article.com",
    "ikea.com",
    "amazon.com",
    "target.com",
    "homedepot.com",
    "walmart.com",
    "overstock.com",
    "allmodern.com",
    "ashleyfurniture.com",
    "roomstogo.com",
    "livingspaces.com",
    "pier1.com",
    "homegoods.com",
]


class FurnitureSearchClient:
    """Client for searching furniture products using Exa Neural Search."""
    
    def __init__(self):
        api_key = os.getenv("EXA_API_KEY")
        if not api_key:
            raise ValueError("EXA_API_KEY not found in environment variables")
        self.client = Exa(api_key=api_key)
    
    def search_products(self, query: str, num_results: int = 10) -> List[Dict[str, Any]]:
        """
        Search for furniture products using Exa Neural Search.
        
        Args:
            query: Search query (e.g., "green velvet modern sofa")
            num_results: Number of results to return
            
        Returns:
            List of product dictionaries with title, url, thumbnail, etc.
        """
        try:
            print(f"🔍 Exa Neural Search: '{query}'")
            
            search_response = self.client.search_and_contents(
                query=query,
                type="neural",
                num_results=num_results,
                include_domains=FURNITURE_DOMAINS,
                text={"max_characters": 500},
            )
            
            products = []
            for result in search_response.results:
                # Extract price from text if available
                price = None
                text = getattr(result, 'text', '') or ''
                if '$' in text:
                    import re
                    price_match = re.search(r'\$[\d,]+\.?\d*', text)
                    if price_match:
                        price = price_match.group(0)
                
                products.append({
                    "title": result.title or "Unknown Product",
                    "url": result.url,
                    "description": text[:200] if text else "",
                    "price": price,
                    "price_str": price or "",
                    "thumbnail": "",  # Exa doesn't provide thumbnails directly
                    "store": self._extract_store(result.url),
                    "source_api": "exa",
                })
            
            print(f"🔍 Exa found {len(products)} products")
            return products
            
        except Exception as e:
            print(f"❌ Exa search error: {e}")
            return []
    
    def _extract_store(self, url: str) -> str:
        """Extract store name from URL."""
        from urllib.parse import urlparse
        try:
            domain = urlparse(url).netloc.lower()
            
            store_mapping = {
                "wayfair.com": "Wayfair",
                "westelm.com": "West Elm",
                "cb2.com": "CB2",
                "crateandbarrel.com": "Crate & Barrel",
                "potterybarn.com": "Pottery Barn",
                "article.com": "Article",
                "ikea.com": "IKEA",
                "amazon.com": "Amazon",
                "target.com": "Target",
                "homedepot.com": "Home Depot",
                "walmart.com": "Walmart",
                "overstock.com": "Overstock",
                "allmodern.com": "AllModern",
                "ashleyfurniture.com": "Ashley Furniture",
            }
            
            for domain_key, store_name in store_mapping.items():
                if domain_key in domain:
                    return store_name
            
            return domain.replace("www.", "").replace(".com", "").title()
        except Exception:
            return "Unknown Store"


# Convenience function for quick searches
def search_exa_products(query: str, num_results: int = 10) -> List[Dict[str, Any]]:
    """
    Convenience function to search for furniture products.
    
    Args:
        query: Search query
        num_results: Number of results
        
    Returns:
        List of product dictionaries
    """
    client = FurnitureSearchClient()
    return client.search_products(query, num_results)
