#!/usr/bin/env python3
"""
CLI test script for Exa API functionality
"""

import json
import os
import sys
from pathlib import Path

import requests
from dotenv import load_dotenv
from exa_client import ExaClient

load_dotenv()


def save_images_debug(products, query):
    """Save product images and data for debugging"""
    # Create temp directory
    temp_dir = Path("temp")
    temp_dir.mkdir(exist_ok=True)

    # Clean query for filename
    safe_query = "".join(c for c in query if c.isalnum() or c in (" ", "_")).rstrip()
    safe_query = safe_query.replace(" ", "_")[:50]

    # Save product data as JSON
    products_file = temp_dir / f"products_{safe_query}.json"
    with open(products_file, "w") as f:
        json.dump(products, f, indent=2, default=str)

    print(f"\n💾 Saved product data to: {products_file}")

    # Extract and save all image URLs
    all_images = []
    product_info = []  # Store for later URL printing

    for i, product in enumerate(products):
        images = product.get("images", [])
        all_images.extend(images)

        # Store product info for URL section
        product_info.append(
            {
                "title": product.get("title", "Unknown"),
                "url": product.get("url", ""),
                "store": product.get("store", "Unknown"),
                "images": images,
            }
        )

        print(f"\n📦 Product {i + 1}: {product.get('title', 'Unknown')[:50]}...")
        print(f"   🖼️  Images found: {len(images)}")
        for j, img_url in enumerate(images):
            print(f"      {j + 1}. {img_url}")

    # Save all image URLs to text file
    urls_file = temp_dir / f"image_urls_{safe_query}.txt"
    with open(urls_file, "w") as f:
        f.write(f"Image URLs for query: {query}\n")
        f.write("=" * 50 + "\n\n")
        for i, product in enumerate(products):
            f.write(f"Product {i + 1}: {product.get('title', 'Unknown')}\n")
            f.write(f"Store: {product.get('store', 'Unknown')}\n")
            f.write(f"URL: {product.get('url', 'Unknown')}\n")
            images = product.get("images", [])
            f.write(f"Images ({len(images)}):\n")
            for img_url in images:
                f.write(f"  - {img_url}\n")
            f.write("\n" + "-" * 30 + "\n\n")

    print(f"💾 Saved image URLs to: {urls_file}")

    # Print all URLs for manual browser testing
    print("\n🌐 COPY-PASTE URLs FOR BROWSER TESTING:")
    print("=" * 70)

    for i, prod_info in enumerate(product_info):
        print(f"\n🛍️  PRODUCT {i + 1}: {prod_info['title'][:60]}")
        print(f"   Store: {prod_info['store']}")
        print("   📋 Product Page URL:")
        print(f"   {prod_info['url']}")

        if prod_info["images"]:
            print(f"\n   🖼️  Images ({len(prod_info['images'])}):")
            for j, img_url in enumerate(
                prod_info["images"][:2]
            ):  # Show first 2 images per product
                print(f"   \n   Image {j + 1}:")
                print(f"   🔗 Direct: {img_url}")
                proxy_url = f"https://images.weserv.nl/?url={requests.utils.quote(img_url, safe='')}&w=400&h=300&fit=cover"
                print(f"   🔄 Proxy:  {proxy_url}")

        print(f"\n   {'-' * 50}")

    print("\n💡 How to test:")
    print("   1. Copy product page URLs - check if they work")
    print(
        "   2. Copy direct image URLs - WILL LIKELY SHOW CAPTCHA (this is the problem!)"
    )
    print("   3. Copy proxy image URLs - might bypass the CAPTCHA")
    print("   4. Compare: do you get CAPTCHA on direct vs actual images on proxy?")

    # Test what we actually get when downloading images (to detect CAPTCHAs)
    sample_images = all_images[:3]  # Test first 3 images
    if sample_images:
        print(
            f"\n🔍 Testing what backend gets when downloading {len(sample_images)} images:"
        )

        for i, img_url in enumerate(sample_images):
            try:
                # Try to download and see what we actually get
                response = requests.get(
                    img_url,
                    timeout=10,
                    headers={
                        "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                    },
                )
                content_type = response.headers.get("content-type", "unknown")
                content_preview = response.content[:200].decode(
                    "utf-8", errors="ignore"
                )

                print(f"\n   🔍 Image {i + 1}: {img_url}")
                print(f"      Status: {response.status_code}")
                print(f"      Content-Type: {content_type}")
                print(f"      Content size: {len(response.content)} bytes")

                # Check if it's actually HTML (CAPTCHA page)
                if (
                    content_type.startswith("text/html")
                    or "<html" in content_preview.lower()
                ):
                    print("      🚨 CAPTCHA DETECTED! Got HTML instead of image:")
                    print(f"      Preview: {content_preview[:100]}...")
                elif content_type.startswith("image/"):
                    print("      ✅ Looks like real image data")
                    print(f"      Preview: {content_preview[:50]} (binary data)")
                else:
                    print("      ⚠️  Unknown content type")
                    print(f"      Preview: {content_preview[:100]}...")

            except Exception as e:
                print(f"   ❌ Image {i + 1}: Error - {str(e)[:100]}...")

        print(
            "\n💡 Solution: Frontend now uses image proxy (images.weserv.nl) for blocked images"
        )
        print("   - Browser tries direct URL first")
        print("   - If CAPTCHA/blocked → automatically tries proxy")
        print("   - Proxy service can bypass CAPTCHA issues")

    print(f"\n📁 All debug files saved in: {temp_dir.absolute()}")
    return temp_dir


def test_exa_search():
    """Test Exa search functionality"""
    print("\n🔍 Testing Exa Search...")

    try:
        exa_client = ExaClient()

        # Test the exact query from the user
        query = "large abstract art for bedroom amazon"

        print(f"Testing query: '{query}'")

        # Test basic search
        search_results = exa_client.search_products(query, num_results=5)
        print("\n📝 Search Results Structure:")
        print(f"   - Results count: {len(search_results.get('results', []))}")

        if "error" in search_results:
            print(f"   - Error: {search_results['error']}")
        else:
            results = search_results.get("results", [])
            if results:
                first_result = results[0]
                print(f"   - First result URL: {first_result.get('url', 'N/A')}")
                print(f"   - First result title: {first_result.get('title', 'N/A')}")

        # Test full product search and analysis
        print("\n🛍️ Testing Full Product Analysis...")
        products = exa_client.search_and_analyze_products(
            query=query, space_type="bedroom", num_results=3
        )

        print(f"   - Analyzed products count: {len(products)}")
        if products:
            first_product = products[0]
            print(f"   - First product title: {first_product.get('title', 'N/A')}")
            print(f"   - First product store: {first_product.get('store', 'N/A')}")
            print(f"   - First product price: {first_product.get('price_str', 'N/A')}")
            print(f"   - First product images: {len(first_product.get('images', []))}")

            # Save images and product data for debugging
            save_images_debug(products, query)

    except Exception as e:
        print(f"❌ Exa Error: {e}")
        import traceback

        traceback.print_exc()


def main():
    """Main CLI function"""
    print("🚀 Exa API Test")
    print("=" * 30)

    # Check if EXA API key is set
    if not os.getenv("EXA_API_KEY"):
        print("❌ Error: EXA_API_KEY environment variable is not set")
        print("Please set your Exa API key:")
        print("export EXA_API_KEY='your-exa-api-key-here'")
        sys.exit(1)

    # Run Exa test
    test_exa_search()

    print("\n🎉 Exa test completed!")


if __name__ == "__main__":
    main()
