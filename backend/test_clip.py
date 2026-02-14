#!/usr/bin/env python3
"""
Quick test script to verify CLIP integration is working
"""

import sys

print("=" * 60)
print("Testing CLIP Integration")
print("=" * 60)

# Test 1: Import CLIP Client
print("\n1. Testing imports...")
try:
    from clip_client import CLIPClient
    print("   ✅ CLIP client module imported successfully")
except ImportError as e:
    print(f"   ❌ Failed to import CLIP client: {e}")
    print("\n   💡 Try running: uv sync")
    sys.exit(1)

# Test 2: Initialize CLIP Client
print("\n2. Initializing CLIP client...")
try:
    client = CLIPClient()
    print("   ✅ CLIP client initialized")
except Exception as e:
    print(f"   ❌ Failed to initialize: {e}")
    sys.exit(1)

# Test 3: Check if CLIP is available
print("\n3. Checking CLIP availability...")
if client.is_available():
    print("   ✅ CLIP model loaded and ready!")
else:
    print("   ❌ CLIP model not available")
    print("   💡 This usually means torch or transformers aren't installed")
    print("   💡 Run: uv sync")
    sys.exit(1)

# Test 4: Test text encoding
print("\n4. Testing text encoding...")
try:
    embedding = client.encode_text("modern gray sofa")
    if embedding is not None and len(embedding) > 0:
        print(f"   ✅ Text encoding works! (embedding size: {len(embedding)})")
    else:
        print("   ❌ Text encoding returned None")
        sys.exit(1)
except Exception as e:
    print(f"   ❌ Text encoding failed: {e}")
    sys.exit(1)

# Test 5: Test image analysis (with dummy data)
print("\n5. Testing furniture analysis...")
try:
    from PIL import Image
    import numpy as np
    
    # Create a simple test image (gray square)
    test_image = Image.fromarray(
        np.uint8(np.ones((224, 224, 3)) * 128), 
        'RGB'
    )
    
    result = client.analyze_furniture_region(test_image)
    if "search_query" in result:
        print(f"   ✅ Furniture analysis works!")
        print(f"   Generated query: '{result['search_query']}'")
    else:
        print(f"   ⚠️  Analysis returned but no search query")
        print(f"   Result: {result}")
except Exception as e:
    print(f"   ❌ Furniture analysis failed: {e}")
    sys.exit(1)

# Success!
print("\n" + "=" * 60)
print("✅ ALL TESTS PASSED! CLIP Integration is working!")
print("=" * 60)
print("\n📝 Next steps:")
print("   1. Restart your backend server (Ctrl+C then 'uv run fastapi dev')")
print("   2. Test the clip-search feature in your app")
print("   3. Look for '⚡ AI Enhanced' badge in search results")
print()

