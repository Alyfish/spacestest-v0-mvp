"""
End-to-End Test for Furniture Analysis Pipeline

This test verifies the complete flow:
1. SpatialDetector (Gemini object detection)
2. smart_crop (Image cropping)
3. upload_image_to_imgbb (Public URL generation)
4. Google Lens (via serp_client)
5. Exa Neural Search (via search_utils)
6. CLIP Validation (via clip_client)
"""

import os
import sys
import base64
from io import BytesIO
from PIL import Image

# Add backend to path
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

def create_test_image():
    """Create a simple test image (500x500 blue square with a chair-like shape)."""
    img = Image.new('RGB', (500, 500), color=(200, 200, 200))
    # Draw a simple rectangle to simulate furniture
    from PIL import ImageDraw
    draw = ImageDraw.Draw(img)
    # Chair-like shape
    draw.rectangle([150, 200, 350, 400], fill=(139, 69, 19))  # Brown chair
    draw.rectangle([150, 100, 200, 200], fill=(139, 69, 19))  # Chair back
    
    buffer = BytesIO()
    img.save(buffer, format='PNG')
    return img, base64.b64encode(buffer.getvalue()).decode('utf-8')

def test_spatial_detector():
    """Test the SpatialDetector component."""
    print("\n=== Testing SpatialDetector ===")
    try:
        from spatial_utils import SpatialDetector
        detector = SpatialDetector()
        
        # Get test image bytes
        img, img_b64 = create_test_image()
        img_bytes = base64.b64decode(img_b64)
        
        # Simulate a click at the center (where our "chair" is)
        result = detector.get_object_bbox(
            img_bytes,
            click_x=0.5,
            click_y=0.6,
            image_width=500,
            image_height=500
        )
        
        print(f"  Label: {result.get('label')}")
        print(f"  BBox: {result.get('bbox_normalized')}")
        print(f"  Attributes: {result.get('attributes')}")
        print(f"  Search Query: {result.get('search_query')}")
        print("✅ SpatialDetector works!")
        return result
    except Exception as e:
        print(f"❌ SpatialDetector failed: {e}")
        return None

def test_smart_crop():
    """Test the smart_crop function."""
    print("\n=== Testing smart_crop ===")
    try:
        from spatial_utils import smart_crop
        
        img, _ = create_test_image()
        bbox = [0.2, 0.3, 0.8, 0.7]  # Example bbox
        
        cropped = smart_crop(img, bbox, padding=0.05)
        print(f"  Original size: {img.size}")
        print(f"  Cropped size: {cropped.size}")
        print("✅ smart_crop works!")
        return cropped
    except Exception as e:
        print(f"❌ smart_crop failed: {e}")
        return None

def test_imgbb_upload():
    """Test ImgBB upload."""
    print("\n=== Testing ImgBB Upload ===")
    try:
        from data_manager import DataManager
        
        dm = DataManager()
        _, img_b64 = create_test_image()
        
        url = dm.upload_image_to_imgbb(img_b64)
        if url:
            print(f"  Public URL: {url}")
            print("✅ ImgBB upload works!")
            return url
        else:
            print("❌ ImgBB upload returned None")
            return None
    except Exception as e:
        print(f"❌ ImgBB upload failed: {e}")
        return None

def test_search_utils():
    """Test Exa search via search_utils."""
    print("\n=== Testing search_utils (Exa) ===")
    try:
        from search_utils import search_exa_products
        
        results = search_exa_products("modern brown wooden chair", num_results=3)
        print(f"  Found {len(results)} products")
        for i, r in enumerate(results[:2]):
            print(f"    [{i+1}] {r.get('title', 'No title')[:50]}...")
        print("✅ search_utils works!")
        return results
    except Exception as e:
        print(f"❌ search_utils failed: {e}")
        return None

def test_clip_validation():
    """Test CLIP validation."""
    print("\n=== Testing CLIP Validation ===")
    try:
        from clip_client import CLIPClient
        
        client = CLIPClient()
        if not client.is_available():
            print("  CLIP not available, skipping...")
            return None
        
        # Test with a simple label
        test_products = [
            {"title": "Modern Wooden Chair", "thumbnail": "https://picsum.photos/200"},
            {"title": "Blue Plastic Table", "thumbnail": "https://picsum.photos/200"},
        ]
        
        validated = client.validate_products_by_label(
            label="wooden chair",
            products=test_products,
            threshold=0.1,
            top_k=2
        )
        
        print(f"  Validated {len(validated)} products")
        for p in validated:
            print(f"    - {p.get('title')}: score={p.get('clip_validation_score', 'N/A'):.3f}")
        print("✅ CLIP validation works!")
        return validated
    except Exception as e:
        print(f"❌ CLIP validation failed: {e}")
        return None

def main():
    print("=" * 60)
    print("FURNITURE ANALYSIS PIPELINE - END-TO-END TEST")
    print("=" * 60)
    
    # Run all tests
    test_spatial_detector()
    test_smart_crop()
    test_imgbb_upload()
    test_search_utils()
    test_clip_validation()
    
    print("\n" + "=" * 60)
    print("TEST COMPLETE")
    print("=" * 60)

if __name__ == "__main__":
    main()
