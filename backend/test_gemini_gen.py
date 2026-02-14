
import os
import traceback
from dotenv import load_dotenv
from google import genai
from google.genai import types

load_dotenv()

def inspect_sdk():
    print("Inspecting google.genai.types...")
    print(dir(types))
    
    if hasattr(types, 'GenerateContentConfig'):
        print("\nGenerateContentConfig fields:")
        try:
            # Try to inspect annotations if available
            print(types.GenerateContentConfig.__annotations__)
        except AttributeError:
            print("No annotations found")

def test_image_gen():
    api_key = os.getenv("GOOGLE_API_KEY")
    if not api_key:
        print("GOOGLE_API_KEY not found")
        return

    client = genai.Client(api_key=api_key)
    
    print("\nTesting Image Generation...")
    try:
        # Try finding the correct configuration
        # Attempt 1: Using dict but maybe checked differently now?
        # The error said "image_config" is extra forbidden. 
        # This implies GenerateContentConfig does NOT have 'image_config' field.
        
        # specific param for imagen? maybe 'generation_config'?
        
        config = types.GenerateContentConfig(
            response_modalities=["IMAGE"],
            temperature=0.4
        )
        
        # Let's see if we can pass image usage param differently
        print("Trying generation without image_config first...")
        
        response = client.models.generate_content(
            model="gemini-3-pro-image-preview",
            contents="A futuristic chair",
            config=config
        )
        print("Success without config!")
        print(response)

    except Exception:
        traceback.print_exc()

if __name__ == "__main__":
    inspect_sdk()
    test_image_gen()
