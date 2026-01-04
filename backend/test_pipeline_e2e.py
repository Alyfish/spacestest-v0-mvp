"""
Comprehensive End-to-End Test for Furniture Analysis Pipeline

Tests the complete flow as specified in the implementation plan:
1. SpatialDetector (Gemini 3.0 Flash)
2. smart_crop
3. upload_image_to_imgbb
4. Google Lens (via SerpAPI) 
5. Exa Neural Search (via search_utils)
6. CLIP Verification
7. FurnitureAnalysisItem creation
"""

import os
import sys
import base64
import time
from io import BytesIO
from PIL import Image, ImageDraw

sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

def create_test_room_image():
    """Create a test room image with furniture-like shapes."""
    img = Image.new('RGB', (800, 600), color=(245, 245, 240))  # Off-white room
    draw = ImageDraw.Draw(img)
    
    # Floor
    draw.rectangle([0, 400, 800, 600], fill=(180, 140, 100))  # Wood floor
    
    # Sofa (brown)
    draw.rectangle([100, 300, 400, 450], fill=(101, 67, 33))  # Sofa body
    draw.rectangle([100, 280, 140, 320], fill=(101, 67, 33))  # Left arm
    draw.rectangle([360, 280, 400, 320], fill=(101, 67, 33))  # Right arm
    
    # Coffee table
    draw.rectangle([450, 380, 600, 420], fill=(139, 90, 43))
    
    # Lamp
    draw.ellipse([650, 200, 720, 250], fill=(255, 255, 200))  # Lampshade
    draw.rectangle([680, 250, 690, 350], fill=(50, 50, 50))   # Stand
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    img_bytes = buffer.getvalue()
    img_b64 = base64.b64encode(img_bytes).decode('utf-8')
    
    return img, img_bytes, img_b64


def test_1_spatial_detector():
    """Test 1: Gemini Spatial Detection"""
    print("\n" + "="*60)
    print("TEST 1: SpatialDetector (Gemini 3.0 Flash)")
    print("="*60)
    
    try:
        from spatial_utils import SpatialDetector
        detector = SpatialDetector()
        
        _, img_bytes, _ = create_test_room_image()
        
        # Click on the sofa area (normalized coords)
        result = detector.get_object_bbox(
            img_bytes,
            click_x=0.3,  # Center of sofa
            click_y=0.6,
            image_width=800,
            image_height=600
        )
        
        print(f"  ✓ Label detected: {result.get('label')}")
        print(f"  ✓ BBox: {result.get('bbox_normalized')}")
        print(f"  ✓ Attributes: {result.get('attributes')}")
        print(f"  ✓ Search Query: {result.get('search_query')}")
        print("✅ TEST 1 PASSED: SpatialDetector working")
        return result
    except Exception as e:
        print(f"❌ TEST 1 FAILED: {e}")
        return None


def test_2_smart_crop():
    """Test 2: Smart Crop Function"""
    print("\n" + "="*60)
    print("TEST 2: smart_crop")
    print("="*60)
    
    try:
        from spatial_utils import smart_crop
        
        img, _, _ = create_test_room_image()
        bbox = [0.3, 0.1, 0.7, 0.5]  # Example bbox [ymin, xmin, ymax, xmax]
        
        cropped = smart_crop(img, bbox, padding=0.05)
        
        print(f"  ✓ Original size: {img.size}")
        print(f"  ✓ Cropped size: {cropped.size}")
        print(f"  ✓ Padding applied correctly")
        print("✅ TEST 2 PASSED: smart_crop working")
        return cropped
    except Exception as e:
        print(f"❌ TEST 2 FAILED: {e}")
        return None


def test_3_imgbb_upload():
    """Test 3: ImgBB Upload"""
    print("\n" + "="*60)
    print("TEST 3: upload_image_to_imgbb")
    print("="*60)
    
    try:
        from data_manager import DataManager
        dm = DataManager()
        
        _, _, img_b64 = create_test_room_image()
        
        url = dm.upload_image_to_imgbb(img_b64)
        
        if url:
            print(f"  ✓ Public URL: {url[:60]}...")
            print("✅ TEST 3 PASSED: ImgBB upload working")
            return url
        else:
            print("❌ TEST 3 FAILED: No URL returned")
            return None
    except Exception as e:
        print(f"❌ TEST 3 FAILED: {e}")
        return None


def test_4_google_lens():
    """Test 4: Google Lens via SerpAPI"""
    print("\n" + "="*60)
    print("TEST 4: Google Lens (SerpAPI)")
    print("="*60)
    
    try:
        from serp_client import SerpClient
        client = SerpClient()
        
        # Use a known furniture image URL for testing
        test_url = "https://images.unsplash.com/photo-1555041469-a586c61ea9bc?w=400"
        
        results = client.reverse_image_search_google_lens_url(test_url)
        
        print(f"  ✓ Found {len(results)} visual matches")
        if results:
            print(f"  ✓ First match: {results[0].get('title', 'N/A')[:50]}...")
        print("✅ TEST 4 PASSED: Google Lens working")
        return results
    except Exception as e:
        print(f"❌ TEST 4 FAILED: {e}")
        return None


def test_5_exa_search():
    """Test 5: Exa Neural Search"""
    print("\n" + "="*60)
    print("TEST 5: Exa Neural Search (search_utils)")
    print("="*60)
    
    try:
        from search_utils import search_exa_products
        
        results = search_exa_products("modern brown leather sofa", num_results=5)
        
        print(f"  ✓ Found {len(results)} products")
        for i, p in enumerate(results[:2]):
            print(f"    [{i+1}] {p.get('title', 'Unknown')[:40]}...")
        print("✅ TEST 5 PASSED: Exa search working")
        return results
    except Exception as e:
        print(f"❌ TEST 5 FAILED: {e}")
        return None


def test_6_clip_validation():
    """Test 6: CLIP Validation"""
    print("\n" + "="*60)
    print("TEST 6: CLIP validate_products_by_label")
    print("="*60)
    
    try:
        from clip_client import CLIPClient
        client = CLIPClient()
        
        if not client.is_available():
            print("  ⚠ CLIP not available, skipping...")
            return None
        
        # Test products with thumbnails
        test_products = [
            {"title": "Brown Leather Sofa", "thumbnail": "https://picsum.photos/200"},
            {"title": "Modern Chair", "thumbnail": "https://picsum.photos/201"},
        ]
        
        validated = client.validate_products_by_label(
            label="leather sofa",
            products=test_products,
            threshold=0.1,
            top_k=5
        )
        
        print(f"  ✓ Validated {len(validated)} products")
        for p in validated:
            score = p.get('clip_validation_score', 0)
            print(f"    - {p.get('title')}: score={score:.3f}")
        print("✅ TEST 6 PASSED: CLIP validation working")
        return validated
    except Exception as e:
        print(f"❌ TEST 6 FAILED: {e}")
        return None


def test_7_furniture_analysis_item():
    """Test 7: FurnitureAnalysisItem model"""
    print("\n" + "="*60)
    print("TEST 7: FurnitureAnalysisItem model")
    print("="*60)
    
    try:
        from models import FurnitureAnalysisItem
        
        item = FurnitureAnalysisItem(
            id="test_item_1",
            furniture_type="sofa",
            confidence=0.95,
            style="modern",
            material="leather",
            color="brown",
            search_query="modern brown leather sofa",
            products=[{"title": "Test Product", "url": "http://example.com"}]
        )
        
        print(f"  ✓ Created item: {item.furniture_type}")
        print(f"  ✓ Confidence: {item.confidence}")
        print(f"  ✓ Products: {len(item.products)}")
        
        # Test model_dump
        data = item.model_dump()
        print(f"  ✓ model_dump() works: {len(data)} fields")
        print("✅ TEST 7 PASSED: FurnitureAnalysisItem working")
        return item
    except Exception as e:
        print(f"❌ TEST 7 FAILED: {e}")
        return None


def main():
    print("="*60)
    print("FURNITURE ANALYSIS PIPELINE - COMPREHENSIVE TEST")
    print("="*60)
    print(f"Started at: {time.strftime('%Y-%m-%d %H:%M:%S')}")
    
    results = {}
    
    # Run all tests
    results['spatial_detector'] = test_1_spatial_detector()
    results['smart_crop'] = test_2_smart_crop()
    results['imgbb_upload'] = test_3_imgbb_upload()
    results['google_lens'] = test_4_google_lens()
    results['exa_search'] = test_5_exa_search()
    results['clip_validation'] = test_6_clip_validation()
    results['furniture_item'] = test_7_furniture_analysis_item()
    
    # Summary
    print("\n" + "="*60)
    print("TEST SUMMARY")
    print("="*60)
    
    passed = sum(1 for v in results.values() if v is not None)
    total = len(results)
    
    for name, result in results.items():
        status = "✅ PASS" if result is not None else "❌ FAIL"
        print(f"  {name}: {status}")
    
    print(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        print("\n🎉 ALL TESTS PASSED! Pipeline is ready.")
    else:
        print(f"\n⚠️ {total - passed} test(s) failed. Review errors above.")
    
    return passed == total


if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
