"""
OpenRouter AI Image Generation Client for product visualization
Uses FLUX and other image generation models via OpenRouter API
"""

import base64
import os
from io import BytesIO
from pathlib import Path
from typing import Optional, Tuple

import requests
from dotenv import load_dotenv
from openai import OpenAI
from PIL import Image

load_dotenv()


class GeminiImageClient:
    """Client for AI image generation through OpenRouter"""

    def __init__(self, api_key: str = None):
        """Initialize OpenRouter client with API key"""
        self.api_key = api_key or os.getenv("OPENROUTER_API_KEY")
        if not self.api_key:
            raise ValueError("OPENROUTER_API_KEY not found in environment variables")

        # Configure OpenRouter client
        self.client = OpenAI(
            base_url="https://openrouter.ai/api/v1",
            api_key=self.api_key,
        )

        print(
            f"🔧 OpenRouter Gemini Client initialized with API key: {self.api_key[:10]}..."
        )

    def generate_product_visualization(
        self,
        original_room_image_path: str,
        product_image_url: str,
        space_type: str,
        product_title: str,
        inspiration_recommendations: list = None,
        marker_locations: list = None,
        custom_prompt: Optional[str] = None,
        project_data_dir: Path = None,
    ) -> Tuple[str, str]:
        """
        Generate a new image showing the product integrated into the original room

        Args:
            original_room_image_path: Path to the user's original room image (base)
            product_image_url: URL of the product image to integrate
            space_type: Type of space (bedroom, living room, etc.)
            product_title: Title of the product for context
            inspiration_recommendations: List of inspiration analysis recommendations
            marker_locations: List of marker locations where improvements are needed
            custom_prompt: Optional custom prompt from user
            project_data_dir: Directory to save the generated image

        Returns:
            Tuple of (generated_image_path, generation_prompt)
        """
        try:
            print(f"🎨 Generating visualization for product: {product_title[:50]}...")
            print(f"   Space type: {space_type}")
            print(f"   Original room image: {original_room_image_path}")
            print(f"   Product image URL: {product_image_url}")

            # Load the original room image
            original_room_image = Image.open(original_room_image_path)
            print(f"✅ Loaded original room image: {original_room_image.size}")

            # Download the product image for reference
            product_image = self._download_image(product_image_url)
            if not product_image:
                raise Exception("Failed to download product image")

            # Convert images to base64 for OpenRouter
            def image_to_base64(img):
                buffer = BytesIO()
                img.save(buffer, format="PNG")
                return base64.b64encode(buffer.getvalue()).decode("utf-8")

            original_image_b64 = image_to_base64(original_room_image)
            product_image_b64 = image_to_base64(product_image)

            original_image_url = f"data:image/png;base64,{original_image_b64}"
            product_image_url_b64 = f"data:image/png;base64,{product_image_b64}"

            # Create comprehensive prompt with all context
            generation_prompt = self._create_integration_prompt(
                space_type=space_type,
                product_title=product_title,
                inspiration_recommendations=inspiration_recommendations or [],
                marker_locations=marker_locations or [],
                custom_prompt=custom_prompt,
            )

            print(f"🎨 Integration prompt: {generation_prompt}")

            # Use FLUX for image-to-image generation
            response = self.client.chat.completions.create(
                extra_headers={
                    "HTTP-Referer": "https://spaces-ai.com",
                    "X-Title": "Spaces AI - Interior Design Tool",
                },
                model="google/gemini-2.5-flash-image-preview",  # Gemini for image analysis and generation
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": generation_prompt},
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": original_image_url,
                                    "detail": "high",
                                },
                            },
                            {
                                "type": "image_url",
                                "image_url": {
                                    "url": product_image_url_b64,
                                    "detail": "high",
                                },
                            },
                        ],
                    }
                ],
                max_tokens=1024,
                temperature=0.4,  # Lower temperature for more consistent results
            )

            # DEBUG: Print the ENTIRE response structure
            print("🔍 FULL OPENROUTER RESPONSE DEBUG:")
            print("=" * 80)

            # Print the raw response object
            import json

            print("📦 RAW RESPONSE:")
            if hasattr(response, "model_dump"):
                try:
                    response_dict = response.model_dump()
                    print(json.dumps(response_dict, indent=2, default=str))
                except Exception as e:
                    print(f"Error dumping model: {e}")
                    print(f"Response dict: {response.__dict__}")
            else:
                print(f"Response dict: {response.__dict__}")

            print("=" * 80)
            print("🔍 RESPONSE ANALYSIS:")
            print(f"Response type: {type(response)}")
            print(
                f"Response attributes: {[attr for attr in dir(response) if not attr.startswith('_')]}"
            )

            # Check every attribute of the response
            for attr in ["choices", "usage", "id", "created", "model", "object"]:
                if hasattr(response, attr):
                    value = getattr(response, attr)
                    print(f"Response.{attr}: {type(value)} = {value}")

            print("=" * 80)
            print("🔍 CHOICES ANALYSIS:")
            if hasattr(response, "choices") and response.choices:
                for i, choice in enumerate(response.choices):
                    print(f"Choice {i}:")
                    print(f"  Type: {type(choice)}")
                    print(
                        f"  Attributes: {[attr for attr in dir(choice) if not attr.startswith('_')]}"
                    )

                    # Check every attribute of the choice
                    for attr in ["message", "finish_reason", "index", "delta"]:
                        if hasattr(choice, attr):
                            value = getattr(choice, attr)
                            print(f"  choice.{attr}: {type(value)} = {value}")

                    # Deep dive into message
                    if hasattr(choice, "message"):
                        message = choice.message
                        print("  MESSAGE ANALYSIS:")
                        print(f"    Type: {type(message)}")
                        print(
                            f"    Attributes: {[attr for attr in dir(message) if not attr.startswith('_')]}"
                        )

                        # Check every attribute of the message
                        for attr in [
                            "role",
                            "content",
                            "tool_calls",
                            "function_call",
                            "images",
                        ]:
                            if hasattr(message, attr):
                                value = getattr(message, attr)
                                if (
                                    attr == "content"
                                    and isinstance(value, str)
                                    and len(value) > 200
                                ):
                                    print(
                                        f"    message.{attr}: {type(value)} = {value[:200]}...[{len(value)} chars total]"
                                    )
                                elif attr == "images" and value:
                                    print(
                                        f"    message.{attr}: {type(value)} = Found {len(value)} images"
                                    )
                                    for i, img in enumerate(value):
                                        if hasattr(img, "image_url") and hasattr(
                                            img.image_url, "url"
                                        ):
                                            url_preview = (
                                                img.image_url.url[:100]
                                                if len(img.image_url.url) > 100
                                                else img.image_url.url
                                            )
                                            print(f"      Image {i}: {url_preview}...")
                                else:
                                    print(
                                        f"    message.{attr}: {type(value)} = {value}"
                                    )

            print("=" * 80)

            response_content = (
                response.choices[0].message.content if response.choices else None
            )

            # Look for generated image in the correct location
            generated_image = None

            # Check if there are images in the message (Gemini format)
            if (
                response.choices
                and hasattr(response.choices[0].message, "images")
                and response.choices[0].message.images
                and len(response.choices[0].message.images) > 0
            ):
                print("🎨 Found images in message.images!")

                # Access as dictionary since images come back as dicts, not objects
                first_image = response.choices[0].message.images[0]
                print(f"First image structure: {first_image}")

                if isinstance(first_image, dict) and "image_url" in first_image:
                    image_data_url = first_image["image_url"]["url"]
                    print(f"Image data URL preview: {image_data_url[:100]}...")

                    # Extract base64 data from data URL
                    if image_data_url.startswith("data:image/"):
                        import re

                        base64_match = re.search(
                            r"data:image/[^;]+;base64,(.+)", image_data_url
                        )
                        if base64_match:
                            image_data = base64_match.group(1)
                            generated_image = Image.open(
                                BytesIO(base64.b64decode(image_data))
                            )
                            print(
                                "✅ Successfully extracted generated image from message.images"
                            )
                        else:
                            print("❌ Could not extract base64 from image data URL")
                    else:
                        print(
                            f"❌ Image URL doesn't start with data:image/, got: {image_data_url[:50]}"
                        )
                else:
                    print(
                        f"❌ Unexpected image structure: {type(first_image)} = {first_image}"
                    )

            # Fallback: Check if image is in response content (old method)
            elif response_content and "data:image" in response_content:
                import re

                base64_match = re.search(
                    r'data:image/[^;]+;base64,([^"\'>\s]+)', response_content
                )
                if base64_match:
                    image_data = base64_match.group(1)
                    generated_image = Image.open(BytesIO(base64.b64decode(image_data)))
                    print(
                        "✅ Successfully extracted generated image from response content"
                    )
                else:
                    print("⚠️ No base64 image found in content")

            # If no image found, create preview
            if generated_image is None:
                print("⚠️ No generated image found, creating preview")
                generated_image = self._create_integration_preview(
                    original_room_image, product_image, generation_prompt
                )

            # Convert generated image to base64 string
            buffer = BytesIO()
            generated_image.save(buffer, format="PNG")
            image_base64 = base64.b64encode(buffer.getvalue()).decode("utf-8")

            print(f"✅ Generated image converted to base64 ({len(image_base64)} chars)")

            return image_base64, generation_prompt

        except Exception as e:
            print(f"❌ Error generating product visualization: {e}")
            raise e

    def _download_image(self, image_url: str) -> Optional[Image.Image]:
        """Download and return a PIL Image from a URL"""
        try:
            print(f"📥 Downloading product image from: {image_url}")

            # Try direct download first
            response = requests.get(
                image_url,
                headers={
                    "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
                },
                timeout=10,
            )

            if response.status_code == 200:
                # Check if it's actually an image
                content_type = response.headers.get("content-type", "")
                if content_type.startswith("image/"):
                    image = Image.open(BytesIO(response.content))
                    print(f"✅ Successfully downloaded image: {image.size}")
                    return image
                else:
                    print(f"⚠️ Content-Type is not an image: {content_type}")

            # Try with proxy if direct fails
            print("🔄 Trying with image proxy...")
            proxy_url = f"https://images.weserv.nl/?url={requests.utils.quote(image_url, safe='')}&w=1024&h=1024&fit=cover"

            response = requests.get(proxy_url, timeout=15)
            if response.status_code == 200:
                image = Image.open(BytesIO(response.content))
                print(f"✅ Successfully downloaded via proxy: {image.size}")
                return image

            print(f"❌ Failed to download image. Status: {response.status_code}")
            return None

        except Exception as e:
            print(f"❌ Error downloading image: {e}")
            return None

    def _create_visualization_prompt(
        self, space_type: str, product_title: str, custom_prompt: Optional[str] = None
    ) -> str:
        """Create a detailed prompt for product visualization"""

        if custom_prompt:
            base_prompt = custom_prompt
        else:
            # Generate context-aware prompt based on space type
            space_contexts = {
                "bedroom": "a cozy, modern bedroom with soft lighting and neutral tones",
                "living_room": "a stylish living room with comfortable seating and warm ambiance",
                "kitchen": "a clean, modern kitchen with natural lighting and organized space",
                "dining_room": "an elegant dining area with good lighting and sophisticated decor",
                "office": "a productive home office space with clean lines and organized setup",
                "bathroom": "a spa-like bathroom with clean, minimal design and good lighting",
                "outdoor": "an outdoor patio or deck area with natural elements and comfortable setting",
            }

            space_context = space_contexts.get(
                space_type.lower(), f"a well-designed {space_type}"
            )

            base_prompt = f"""
            Create a realistic, high-quality interior design visualization showing this product 
            beautifully integrated into {space_context}. 
            
            The product should be the focal point and look natural in the space. 
            Use professional interior design principles with:
            - Proper scale and proportions
            - Complementary colors and textures  
            - Good lighting that highlights the product
            - A cohesive, sophisticated style
            - High-end, magazine-quality aesthetic
            
            Product: {product_title}
            """

        return base_prompt.strip()

    def _create_integration_prompt(
        self,
        space_type: str,
        product_title: str,
        inspiration_recommendations: list,
        marker_locations: list,
        custom_prompt: Optional[str] = None,
    ) -> str:
        """Create a comprehensive prompt for integrating product into the original room"""

        # Build context from inspiration recommendations
        inspiration_context = ""
        if inspiration_recommendations:
            inspiration_context = "\n\nInspiration Style Guide:\n"
            for i, rec in enumerate(inspiration_recommendations[:3], 1):
                inspiration_context += f"{i}. {rec}\n"

        # Build context from marker locations
        marker_context = ""
        if marker_locations:
            marker_context = "\n\nImprovement Areas Marked by User:\n"
            for i, marker in enumerate(marker_locations[:5], 1):
                # Assuming markers have x, y coordinates and maybe a description
                marker_info = f"Area {i}"
                if isinstance(marker, dict):
                    if "x" in marker and "y" in marker:
                        marker_info += f" at position ({marker['x']}, {marker['y']})"
                    if "description" in marker:
                        marker_info += f": {marker['description']}"
                marker_context += f"- {marker_info}\n"

        # Custom user prompt
        user_context = ""
        if custom_prompt:
            user_context = f"\n\nUser's Specific Request:\n{custom_prompt}\n"

        # Main integration prompt
        base_prompt = f"""
CRITICAL INSTRUCTIONS - ROOM STRUCTURE PRESERVATION:
- The original room's walls, ceiling, flooring, windows, and doors MUST remain exactly identical
- Only add/integrate the new product into the existing space  
- Do NOT change room dimensions, architectural elements, or structural features
- Do NOT move or remove existing furniture unless specifically marked for improvement
- Preserve all lighting, textures, and spatial relationships

TASK: Integrate the product "{product_title}" into the original {space_type} image.

INTEGRATION REQUIREMENTS:
1. **Preserve Original Room**: Keep walls, ceiling, floor, windows exactly as shown in the original image
2. **Natural Placement**: Position the product where it would logically belong in this space type
3. **Scale Accuracy**: Ensure the product is properly sized for the room
4. **Lighting Consistency**: Match the lighting and shadows of the original room
5. **Style Harmony**: Make the product fit the existing room's aesthetic
{inspiration_context}
{marker_context}
{user_context}

OUTPUT: Generate a new image that shows the exact same room with the product seamlessly integrated. 
The result should look like the product was always meant to be in that space.

EMPHASIS: The room structure, walls, layout, and architectural features must be IDENTICAL to the original image.
Only the product should be added - everything else stays exactly the same.
"""

        return base_prompt.strip()

    def _create_integration_preview(
        self, original_room_image: Image.Image, product_image: Image.Image, prompt: str
    ) -> Image.Image:
        """Create a side-by-side preview when actual generation fails"""
        try:
            # Create a larger canvas to show both images side by side
            room_width, room_height = original_room_image.size
            product_width, product_height = product_image.size

            # Scale product image to match room height if needed
            if product_height > room_height:
                ratio = room_height / product_height
                new_product_width = int(product_width * ratio)
                product_image = product_image.resize(
                    (new_product_width, room_height), Image.Resampling.LANCZOS
                )
                product_width = new_product_width

            # Create canvas
            canvas_width = (
                room_width + product_width + 60
            )  # 60px for spacing and labels
            canvas_height = (
                max(room_height, product_height) + 120
            )  # Extra space for text

            canvas = Image.new("RGB", (canvas_width, canvas_height), color="#f8f9fa")

            # Paste original room image
            canvas.paste(original_room_image, (20, 60))

            # Paste product image
            canvas.paste(product_image, (room_width + 40, 60))

            # Add text labels
            from PIL import ImageDraw, ImageFont

            draw = ImageDraw.Draw(canvas)

            try:
                font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 24)
                small_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 18)
            except (IOError, OSError):
                font = ImageFont.load_default()
                small_font = ImageFont.load_default()

            # Labels
            draw.text((20, 20), "Original Room", fill="#2d3748", font=font)
            draw.text(
                (room_width + 40, 20), "Product to Integrate", fill="#2d3748", font=font
            )

            # Arrow indicating integration
            arrow_y = 60 + room_height // 2
            arrow_x = room_width + 20
            draw.text((arrow_x - 10, arrow_y), "→", fill="#4299e1", font=font)

            # Instructions at bottom
            instruction = (
                "Preview: Product will be integrated into the original room structure"
            )
            draw.text(
                (20, canvas_height - 40), instruction, fill="#718096", font=small_font
            )

            return canvas

        except Exception as e:
            print(f"⚠️ Error creating integration preview: {e}")
            return original_room_image

    def _create_professional_visualization(
        self, description: str, product_title: str, space_type: str
    ) -> Image.Image:
        """Create a professional visualization report image"""
        try:
            from PIL import Image, ImageDraw, ImageFont

            # Create a canvas with professional colors
            width, height = 1200, 900
            image = Image.new("RGB", (width, height), color="#ffffff")
            draw = ImageDraw.Draw(image)

            # Try to use nice fonts
            try:
                title_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 36)
                subtitle_font = ImageFont.truetype(
                    "/System/Library/Fonts/Arial.ttf", 28
                )
                body_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 22)
                small_font = ImageFont.truetype("/System/Library/Fonts/Arial.ttf", 18)
            except (IOError, OSError):
                try:
                    title_font = ImageFont.load_default()
                    subtitle_font = ImageFont.load_default()
                    body_font = ImageFont.load_default()
                    small_font = ImageFont.load_default()
                except Exception:
                    title_font = subtitle_font = body_font = small_font = None

            # Header section with gradient-like effect
            for i in range(120):
                color_val = int(255 - (i * 0.3))
                draw.rectangle(
                    [0, i, width, i + 1],
                    fill=(
                        min(color_val, 255),
                        min(color_val + 10, 255),
                        min(color_val + 20, 255),
                    ),
                )

            # Main title
            title = "🏠 AI Interior Design Visualization"
            if title_font:
                title_bbox = draw.textbbox((0, 0), title, font=title_font)
                title_width = title_bbox[2] - title_bbox[0]
                draw.text(
                    ((width - title_width) // 2, 30),
                    title,
                    fill="#1a202c",
                    font=title_font,
                )

            # Product and space info
            y_pos = 140
            product_info = f"Product: {product_title}"
            space_info = f"Space: {space_type.title()} Design"

            if subtitle_font:
                draw.text((50, y_pos), product_info, fill="#2d3748", font=subtitle_font)
                y_pos += 40
                draw.text((50, y_pos), space_info, fill="#4a5568", font=small_font)
                y_pos += 60

            # Word wrap the description with better formatting
            words = description.split()
            lines = []
            current_line = ""
            max_width = width - 100  # Padding on sides

            for word in words:
                test_line = current_line + (" " if current_line else "") + word
                if body_font:
                    bbox = draw.textbbox((0, 0), test_line, font=body_font)
                    line_width = bbox[2] - bbox[0]
                else:
                    line_width = len(test_line) * 12  # rough estimate

                if line_width <= max_width:
                    current_line = test_line
                else:
                    if current_line:
                        lines.append(current_line)
                        current_line = word
                    else:
                        lines.append(word)

            if current_line:
                lines.append(current_line)

            # Add section divider
            draw.rectangle([50, y_pos, width - 50, y_pos + 2], fill="#e2e8f0")
            y_pos += 20

            # Draw the description text with better spacing
            line_height = 32

            for i, line in enumerate(lines):
                if y_pos > height - 100:  # Stop if we run out of space
                    break

                # Highlight section headers (lines with **text**)
                if line.strip().startswith("**") and line.strip().endswith("**"):
                    # Section header
                    header_text = line.strip().replace("**", "")
                    if subtitle_font:
                        draw.text(
                            (50, y_pos), header_text, fill="#2d3748", font=subtitle_font
                        )
                    y_pos += 40
                else:
                    # Regular text
                    if body_font:
                        draw.text((70, y_pos), line, fill="#4a5568", font=body_font)
                    else:
                        draw.text((70, y_pos), line, fill="#4a5568")
                    y_pos += line_height

            # Add professional footer
            draw.rectangle([0, height - 80, width, height], fill="#f7fafc")
            footer_text = "✨ AI-Powered Interior Design Analysis • Spaces AI Platform"
            if small_font:
                footer_bbox = draw.textbbox((0, 0), footer_text, font=small_font)
                footer_width = footer_bbox[2] - footer_bbox[0]
                draw.text(
                    ((width - footer_width) // 2, height - 45),
                    footer_text,
                    fill="#718096",
                    font=small_font,
                )

            return image

        except Exception as e:
            print(f"⚠️ Error creating professional visualization: {e}")
            # Return a simple professional fallback
            fallback = Image.new("RGB", (1200, 900), color="#ffffff")
            draw = ImageDraw.Draw(fallback)
            draw.text(
                (50, 100), f"AI Visualization for: {product_title}", fill="#2d3748"
            )
            draw.text((50, 150), f"Space Type: {space_type}", fill="#4a5568")
            draw.text(
                (50, 250), "Visualization analysis generated by AI", fill="#718096"
            )
            return fallback
