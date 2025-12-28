"""
Gemini AI Client for Text, Vision, and Image Generation
Uses Google GenAI SDK (v1.40.0+)
"""

import base64
import os
import json
import traceback
from io import BytesIO
from pathlib import Path
from typing import Dict, Any, Optional, Tuple, TypeVar, Union, Type, List

import requests
from dotenv import load_dotenv
from PIL import Image
from pydantic import BaseModel

from google import genai
from google.genai import types

load_dotenv()

T = TypeVar("T", bound=BaseModel)

class GeminiClient:
    """Client for Google Gemini API (Text, Vision, Image)"""

    def __init__(self, api_key: str = None):
        """Initialize Google GenAI client with API key"""
        self.api_key = api_key or os.getenv("GOOGLE_API_KEY")
        if not self.api_key:
            # Fallback for systems where GOOGLE_API_KEY might be named differently
            self.api_key = os.getenv("GEMINI_API_KEY")
            
        if not self.api_key:
            raise ValueError("GOOGLE_API_KEY not found in environment variables")

        # Initialize the client
        self.client = genai.Client(api_key=self.api_key)

        print(f"🔧 Google GenAI Gemini Client initialized")

    def get_structured_completion(
        self,
        prompt: str,
        pydantic_model: Type[T],
        model: str = "gemini-2.5-flash",
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = None,
    ) -> T:
        """
        Get a structured response from Gemini using JSON schema enforcement

        Args:
            prompt: The input prompt
            pydantic_model: Pydantic model class for structured output
            model: The model to use (default: gemini-2.5-flash)
            max_tokens: Maximum tokens in response
            system_message: Optional system message
        """
        try:
            # Construct the full prompt
            full_prompt = prompt
            
            config = types.GenerateContentConfig(
                response_modalities=["TEXT"],
                response_mime_type="application/json",
                response_schema=pydantic_model,
                temperature=0.1,  # Low temperature for structural reliability
            )
            
            if max_tokens:
                config.max_output_tokens = max_tokens
                
            if system_message:
                config.system_instruction = system_message

            response = self.client.models.generate_content(
                model=model,
                contents=full_prompt,
                config=config,
            )

            # Parse the response
            if response.text:
                return pydantic_model.model_validate_json(response.text)
            else:
                raise ValueError("Empty response from Gemini API")

        except Exception as e:
            print(f"❌ Error in get_structured_completion: {e}")
            raise e

    def analyze_image_with_vision(
        self,
        prompt: str,
        pydantic_model: Type[T],
        image_path: str,
        model: str = "gemini-2.5-flash",
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = None,
        additional_image_paths: Optional[List[str]] = None,
    ) -> T:
        """
        Analyze an image using Vision API with structured output

        Args:
            prompt: The prompt describing what to analyze
            pydantic_model: Pydantic model class for structured output
            image_path: Path to the image file
            model: The vision model to use (default: gemini-2.5-flash)
            max_tokens: Maximum tokens
            system_message: Optional system message
        """
        try:
            # Build contents list: prompt + main image + optional extra images for context
            contents: List[Any] = [prompt]
            pil_image = Image.open(image_path)
            contents.append(pil_image)

            if additional_image_paths:
                for extra_path in additional_image_paths:
                    try:
                        contents.append(Image.open(extra_path))
                    except Exception as extra_err:
                        print(f"⚠️ Skipping additional image {extra_path}: {extra_err}")
            
            config = types.GenerateContentConfig(
                response_modalities=["TEXT"],
                response_mime_type="application/json",
                response_schema=pydantic_model,
                temperature=0.2, # Slightly higher for vision creativity/inference
            )

            if max_tokens:
                config.max_output_tokens = max_tokens
                
            if system_message:
                config.system_instruction = system_message

            response = self.client.models.generate_content(
                model=model,
                contents=contents,
                config=config,
            )

            if response.text:
                return pydantic_model.model_validate_json(response.text)
            else:
                raise ValueError("Empty response from Gemini Vision")

        except Exception as e:
            print(f"❌ Error in analyze_image_with_vision: {e}")
            raise e

    def analyze_color_application(
        self,
        image_path: str,
        palette_name: str,
        palette_colors: list,
        space_type: str,
        let_ai_decide: bool = False,
        model: str = "gemini-2.5-flash",
    ) -> Dict[str, Any]:
        """
        Color Agent: Analyze how to apply a color palette to a space.
        Uses a comprehensive 10-step design process to provide professional guidance.
        
        Args:
            image_path: Path to the original room image
            palette_name: Name of the selected palette
            palette_colors: List of HEX color codes
            space_type: Type of space (bedroom, living room, etc.)
            let_ai_decide: If true, AI optimizes colors regardless of palette
            model: The vision model to use
        """
        from models import ColorAnalysis
        
        try:
            print(f"🎨 Color Agent analyzing color application for {space_type}...")
            
            # Load the image
            pil_image = Image.open(image_path)
            
            # Build the Color Agent system prompt
            system_prompt = """You are an expert Color Agent specializing in interior design color application.
You are a design professional with deep expertise in color theory, interior design, and spatial aesthetics.
Your role is to provide detailed, professional guidance on how to apply colors to a space.

IMPORTANT: You are the design expert. Even when a user selects a specific color palette, you should:
- Adapt colors if they don't work well for the space
- Suggest better alternatives when needed
- Always prioritize what looks BEST for the room over strict palette adherence
- Note any adaptations you make in the palette_adaptations field"""

            # Build the user prompt with the 10-step process
            if let_ai_decide:
                color_context = "The user wants you to choose the BEST colors for this space. Analyze the room and select an optimal color palette."
            else:
                color_context = f"""The user has selected the "{palette_name}" palette with colors: {', '.join(palette_colors)}.
Use these colors as a starting point, but adapt as needed for the best result.
If certain colors don't work well for this space, feel free to suggest alternatives."""

            prompt = f"""Analyze this {space_type} image and provide comprehensive color application guidance.

{color_context}

Follow this 10-step professional design process:

1️⃣ UNDERSTAND THE SPACE
- Identify the space type and function
- Note if the space is empty or furnished
- List existing elements (flooring, walls, large furniture)

2️⃣ DEFINE MOOD AND ATMOSPHERE
- Describe the mood this space should evoke
- Explain how this mood guides color selection

3️⃣ ASSESS LIGHT CONDITIONS
- Describe natural lighting (windows, direction, intensity)
- Note artificial lighting considerations

4️⃣ SELECT AND JUSTIFY COLORS
Apply the 60-30-10 rule:
- 60% Primary colors for dominant surfaces
- 30% Secondary colors to complement
- 10% Accent colors for visual interest
Include HEX codes for each color.

5️⃣ COLOR THEORY APPROACH
Choose and explain your approach:
- Monochromatic: Variations of one hue
- Analogous: Neighboring hues
- Complementary: Opposite hues
- Triadic: Three evenly spaced hues

6️⃣ ASSIGN COLORS TO ELEMENTS
Specify exactly which colors go where:
- Walls and ceiling (with finish: matte, satin, etc.)
- Trim and doors
- Large furniture
- Textiles (rugs, curtains, bedding)
- Decor and accessories

7️⃣ LIGHT AND TEXTURE INTERACTION
- How colors look in daylight vs evening
- How finishes (matte, glossy, textured) affect perception

8️⃣ MAINTAIN COHESION
- Tips for flow with adjacent rooms
- Color transition recommendations

9️⃣ PERSONALIZATION TIPS
- Seasonal accent swaps
- Easy ways to refresh the look

🔟 PROVIDE STRUCTURED OUTPUT
Follow the required JSON schema exactly."""

            # Gemini API currently does not support additionalProperties in schemas reliably.
            # Request JSON text and validate locally with Pydantic for strict structure.
            response = self.client.models.generate_content(
                model=model,
                contents=[prompt, pil_image],
                config=types.GenerateContentConfig(
                    response_modalities=["TEXT"],
                    response_mime_type="application/json",
                    temperature=0.3,
                    system_instruction=system_prompt,
                ),
            )

            if not response.text:
                raise ValueError("Empty response from Color Agent")

            def load_json_payload(text: str) -> Dict[str, Any]:
                try:
                    return json.loads(text)
                except json.JSONDecodeError:
                    start = text.find("{")
                    end = text.rfind("}")
                    if start == -1 or end == -1:
                        raise
                    return json.loads(text[start : end + 1])

            def normalize_swatch_list(value: Any) -> list[dict]:
                swatches: list[dict] = []
                if isinstance(value, list):
                    for item in value:
                        if isinstance(item, str):
                            swatches.append({"hex": item, "description": ""})
                        elif isinstance(item, dict):
                            hex_val = item.get("hex") or item.get("color_hex") or item.get("color")
                            if not hex_val:
                                continue
                            swatches.append(
                                {
                                    "hex": hex_val,
                                    "description": item.get("description") or item.get("notes") or "",
                                }
                            )
                return swatches

            def normalize_color_assignments(
                value: Any, fallback_hex: Optional[str], fallback_name: str
            ) -> list[dict]:
                assignments: list[dict] = []
                if isinstance(value, list):
                    assignments = value
                elif isinstance(value, dict):
                    for key, details in value.items():
                        if not isinstance(details, dict):
                            continue
                        element_name = key.replace("_", " ").title()
                        color_hex = details.get("color_hex") or details.get("hex") or fallback_hex or "#000000"
                        color_name = details.get("color_name") or details.get("name") or fallback_name
                        assignments.append(
                            {
                                "element": element_name,
                                "color_hex": color_hex,
                                "color_name": color_name,
                                "finish": details.get("finish"),
                                "notes": details.get("notes") or details.get("description"),
                            }
                        )
                return assignments

            def normalize_color_analysis_payload(payload: Dict[str, Any]) -> Dict[str, Any]:
                expected_keys = {
                    "space_summary",
                    "primary_colors",
                    "secondary_colors",
                    "accent_colors",
                    "color_theory_approach",
                    "color_theory_rationale",
                    "color_assignments",
                    "lighting_notes",
                    "cohesion_tips",
                    "personalization_suggestions",
                    "palette_adaptations",
                }
                if expected_keys.issubset(set(payload.keys())):
                    return payload

                space_analysis = payload.get("space_analysis") or {}
                mood = payload.get("mood_atmosphere") or {}
                space_summary = payload.get("space_summary") or " ".join(
                    part
                    for part in [
                        space_analysis.get("space_type_function"),
                        mood.get("desired_mood"),
                        mood.get("mood_guidance"),
                    ]
                    if part
                ).strip()

                color_selection = payload.get("color_selection") or {}
                primary_colors = normalize_swatch_list(
                    payload.get("primary_colors") or color_selection.get("primary_colors")
                )
                secondary_colors = normalize_swatch_list(
                    payload.get("secondary_colors") or color_selection.get("secondary_colors")
                )
                accent_colors = normalize_swatch_list(
                    payload.get("accent_colors") or color_selection.get("accent_colors")
                )

                fallback_hex = primary_colors[0]["hex"] if primary_colors else None
                fallback_name = primary_colors[0].get("description", "Primary color") if primary_colors else "Primary color"

                color_theory = color_selection.get("color_theory_approach") or payload.get(
                    "color_theory_approach"
                )
                color_theory_rationale = (
                    payload.get("color_theory_rationale")
                    or color_selection.get("color_theory_rationale")
                )
                if isinstance(color_theory, dict):
                    color_theory_rationale = color_theory_rationale or color_theory.get("rationale")
                    color_theory = color_theory.get("approach") or color_theory.get("name")

                assignments_src = payload.get("color_assignments") or payload.get(
                    "color_assignment_to_elements"
                )
                color_assignments = normalize_color_assignments(
                    assignments_src or {}, fallback_hex, fallback_name
                )

                light_conditions = payload.get("light_conditions") or {}
                light_texture = payload.get("light_texture_interaction") or {}
                lighting_notes = payload.get("lighting_notes") or " ".join(
                    part
                    for part in [
                        light_conditions.get("natural_lighting"),
                        light_conditions.get("artificial_lighting"),
                        light_texture.get("daylight_perception"),
                        light_texture.get("evening_perception"),
                        light_texture.get("finish_notes"),
                    ]
                    if part
                ).strip()

                maintain_cohesion = payload.get("maintain_cohesion") or {}
                cohesion_tips = payload.get("cohesion_tips") or " ".join(
                    part
                    for part in [
                        maintain_cohesion.get("adjacent_rooms_flow"),
                        maintain_cohesion.get("transition_tips"),
                    ]
                    if part
                ).strip()

                personalization = payload.get("personalization_tips") or {}
                personalization_suggestions = payload.get("personalization_suggestions") or " ".join(
                    part
                    for part in [
                        personalization.get("seasonal_accent_swaps"),
                        personalization.get("refresh_ideas"),
                    ]
                    if part
                ).strip()

                palette_adaptations = payload.get("palette_adaptations") or color_selection.get(
                    "palette_adaptations"
                )

                return {
                    "space_summary": space_summary or "Summary not provided",
                    "primary_colors": primary_colors,
                    "secondary_colors": secondary_colors,
                    "accent_colors": accent_colors,
                    "color_theory_approach": color_theory or "Unknown",
                    "color_theory_rationale": color_theory_rationale or "Not provided",
                    "color_assignments": color_assignments,
                    "lighting_notes": lighting_notes or "Not provided",
                    "cohesion_tips": cohesion_tips or "Not provided",
                    "personalization_suggestions": personalization_suggestions or "Not provided",
                    "palette_adaptations": palette_adaptations,
                }

            def build_fallback_color_analysis() -> Dict[str, Any]:
                swatches = [{"hex": c, "description": "Palette color"} for c in palette_colors]
                primary = swatches[:2] or [{"hex": "#DDDDDD", "description": "Primary neutral"}]
                secondary = swatches[2:4]
                accent = swatches[4:5]
                assignments = [
                    {
                        "element": "Walls",
                        "color_hex": primary[0]["hex"],
                        "color_name": "Primary wall color",
                        "finish": "matte",
                        "notes": "Use for dominant wall surfaces.",
                    },
                    {
                        "element": "Textiles",
                        "color_hex": (secondary[0]["hex"] if secondary else primary[0]["hex"]),
                        "color_name": "Secondary textile color",
                        "finish": None,
                        "notes": "Apply to curtains, bedding, or rugs.",
                    },
                    {
                        "element": "Accents",
                        "color_hex": (accent[0]["hex"] if accent else primary[0]["hex"]),
                        "color_name": "Accent color",
                        "finish": None,
                        "notes": "Use for decor and small accessories.",
                    },
                ]
                return {
                    "space_summary": f"Color guidance for a {space_type} based on the selected palette.",
                    "primary_colors": primary,
                    "secondary_colors": secondary,
                    "accent_colors": accent,
                    "color_theory_approach": "Analogous",
                    "color_theory_rationale": "Palette tones are adjacent and cohesive.",
                    "color_assignments": assignments,
                    "lighting_notes": "Consider lighting temperature when evaluating final tones.",
                    "cohesion_tips": "Repeat key hues across adjacent spaces for continuity.",
                    "personalization_suggestions": "Rotate accent textiles seasonally for variety.",
                    "palette_adaptations": None,
                }

            try:
                payload = load_json_payload(response.text)
                try:
                    result = ColorAnalysis.model_validate(payload)
                except Exception:
                    normalized = normalize_color_analysis_payload(payload)
                    result = ColorAnalysis.model_validate(normalized)
                print(f"✅ Color Agent analysis complete")
                return result.model_dump()
            except Exception as parse_err:
                print(f"❌ Failed to parse Color Agent response: {parse_err}")
                print(f"Raw response: {response.text}")
                fallback = build_fallback_color_analysis()
                result = ColorAnalysis.model_validate(fallback)
                return result.model_dump()

        except Exception as e:
            print(f"❌ Error in analyze_color_application: {e}")
            traceback.print_exc()
            raise e

    def analyze_style_application(
        self,
        image_path: str,
        style_name: str,
        space_type: str,
        color_scheme: Dict[str, Any] = None,
        let_ai_decide: bool = False,
        model: str = "gemini-2.5-flash",
    ) -> Dict[str, Any]:
        """
        Style Agent: Analyze how to apply an interior design style to a space.
        Uses comprehensive design principles and the 10 major interior style definitions.
        
        Args:
            image_path: Path to the original room image
            style_name: Name of the selected style
            space_type: Type of space (bedroom, living room, etc.)
            color_scheme: Optional color scheme to coordinate with
            let_ai_decide: If true, AI chooses the optimal style
            model: The vision model to use
        """
        from models import StyleAnalysis
        
        try:
            print(f"🎨 Style Agent analyzing style application for {space_type}...")
            
            # Load the image
            pil_image = Image.open(image_path)
            
            # Build the comprehensive Style Agent system prompt
            system_prompt = """You are an expert interior designer and design historian.
Your role is to explain in detail how to design a space in a specific interior design style.

🧠 CONTEXT & DEFINITIONS OF MAJOR STYLES:

1️⃣ Art Deco - 1920s–1940s France/US. Glamorous, sleek, urban. Lacquered wood, chrome, glass, mirrored surfaces. Black, white, jewel tones, metallics. Geometric patterns, sunbursts, bold chandeliers.

2️⃣ Mid-Century Modern - 1940s–1970s America. Functional, warm, nature-connected. Teak, walnut, molded plastic, leather. Earthy neutrals + mustard, avocado. Low-slung profiles, tapered legs, Eames-style icons.

3️⃣ Scandinavian - Nordic origins. Bright, airy, calm (hygge). Pale woods, wool, linen. White, soft neutrals, muted pastels. Simple, functional, clutter-free.

4️⃣ Industrial - Converted factories/lofts. Raw, masculine, urban. Exposed brick, concrete, steel. Grays, blacks, browns. Vintage factory pieces, Edison bulbs.

5️⃣ Bohemian - 20th-century counterculture. Eclectic, free-spirited, global. Rattan, vintage textiles. Rich jewel tones, layered patterns. Mismatched pieces, string lights.

6️⃣ Contemporary - Always evolving. Clean, light, sophisticated. Glass, metals, stone. Neutrals with contrast. Low-profile, open layouts.

7️⃣ Traditional - 18th–19th century Europe. Formal, elegant, classic. Mahogany, silk, velvet. Rich warm palettes. Symmetrical, ornate, antiques.

8️⃣ Minimalist - 20th-century modernism. Serene, uncluttered. Matte finishes, smooth surfaces. White and neutral. Negative space is essential.

9️⃣ Farmhouse / Modern Farmhouse - Rural America. Cozy, rustic-modern. Shiplap, reclaimed wood. Soft neutrals, sage green. Slipcovered sofas, barn doors.

🔟 French Country - Rural France. Romantic, soft, vintage. Wrought iron, distressed wood. Cream, sage, lavender. Curved legs, weathered elegance.

IMPORTANT DESIGN PRINCIPLE: Keep ALL STRUCTURAL ASPECTS CONSTANT (walls, doors, flooring, ceiling). Only recommend changes to furniture, decor, and accessories.

You are the design expert. Tailor all recommendations specifically to the room shown in the image."""

            # Build the user prompt
            if let_ai_decide:
                style_context = "Analyze this room and recommend the BEST interior design style for it. Consider the room's architecture, lighting, and existing elements."
            else:
                style_context = f"""The user has selected the "{style_name}" style.
Provide detailed guidance on how to transform this room into that style."""

            color_context = ""
            if color_scheme:
                colors = color_scheme.get("colors", [])
                if colors:
                    color_context = f"\nCoordinate with the selected color palette: {', '.join(colors)}"

            prompt = f"""Analyze this {space_type} image and provide comprehensive style application guidance.

{style_context}{color_context}

Structure your response in these 6 sections:

1️⃣ OVERVIEW
- Brief description of the style
- Historical/cultural roots
- Mood and atmosphere this style creates

2️⃣ DEFINING CHARACTERISTICS
For this style, detail:
- Materials to use
- Color palette (with hex codes)
- Furniture characteristics and key pieces
- Patterns & textures
- Lighting fixtures and approach
- Decor & accessories

3️⃣ LAYOUT & SPATIAL PRINCIPLES
- Flow and zoning for this room
- Symmetry or asymmetry approach
- Balance of negative and positive space

4️⃣ SIGNATURE STYLING TIPS
- Practical advice for this room
- Common mistakes to avoid
- Pro designer insights

5️⃣ SPECIFIC RECOMMENDATIONS
For THIS room, recommend:
- 3-5 specific furniture pieces with descriptions
- 1-2 anchor furniture items that define the style
- A statement accessory
- Detailed transformation scenario

6️⃣ RELATED STYLES
- Similar styles and what distinguishes them

REMEMBER: Keep walls, doors, flooring, ceiling unchanged. Focus on furniture, decor, and styling."""

            config = types.GenerateContentConfig(
                response_modalities=["TEXT"],
                response_mime_type="application/json",
                response_schema=StyleAnalysis,
                temperature=0.3,
                system_instruction=system_prompt,
            )

            response = self.client.models.generate_content(
                model=model,
                contents=[prompt, pil_image],
                config=config,
            )

            if response.text:
                result = StyleAnalysis.model_validate_json(response.text)
                print(f"✅ Style Agent analysis complete")
                return result.model_dump()
            else:
                raise ValueError("Empty response from Style Agent")

        except Exception as e:
            print(f"❌ Error in analyze_style_application: {e}")
            traceback.print_exc()
            raise e

    def generate_room_redesign(
        self,
        original_room_image_path: str,
        prompt: str,
    ) -> str:
        """
        Generate a redesigned room image based on inspiration
        using Gemini 3 Pro Image (Nano Banana Pro)
        """
        try:
            print(f"🎨 Generating room redesign...")
            
            # Load images
            original_room_image = Image.open(original_room_image_path)
            
            # Use 'gemini-3-pro-image-preview'
            model_name = "gemini-3-pro-image-preview" 
            
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            )

            # Add technical requirement for aspect ratio
            final_prompt = f"{prompt}\n\nTechnical Requirement: Generate the image with a 1:1 Square Aspect Ratio."

            # Prepare the contents: text prompt + input image
            contents = [
                final_prompt,
                original_room_image
            ]

            print(f"🚀 Sending request to {model_name}...")
            response = self.client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )

            generated_image_b64 = None
            
            # Extract image from response
            for part in response.parts:
                if part.inline_data:
                    generated_image_b64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                    print("✅ Successfully generated redesign image")
                    break
            
            if not generated_image_b64:
                 raise ValueError("No image generated in response")

            return generated_image_b64

        except Exception as e:
            print(f"❌ Error generating room redesign: {e}")
            traceback.print_exc()
            raise e
    def generate_product_visualization(
        self,
        original_room_image_path: str,
        selected_products: list,
        space_type: str,
        inspiration_recommendations: list,
        marker_locations: list,
        custom_prompt: Optional[str] = None,
        project_data_dir: Optional[Path] = None,
        color_scheme: Dict[str, Any] = None,
        design_style: Dict[str, Any] = None,
    ) -> Tuple[str, str]:
        """
        Generate a new image showing multiple products integrated into the original room
        using Gemini 3 Pro Image (Nano Banana Pro)
        """
        try:
            print(f"🎨 Generating visualization for {len(selected_products)} products...")
            
            # Load room image
            original_room_image = Image.open(original_room_image_path)
            
            # Download all product images
            product_images = []
            product_titles = []
            for product in selected_products:
                img = self._download_image(product["image_url"])
                if img:
                    product_images.append(img)
                    product_titles.append(product["title"])
            
            if not product_images:
                raise Exception("Failed to download any product images")
            
            # Create aggregate product title for the prompt
            all_titles = ", ".join(product_titles)
            
            # Create prompt
            generation_prompt = self._create_integration_prompt(
                space_type=space_type,
                product_titles=product_titles,
                inspiration_recommendations=inspiration_recommendations or [],
                marker_locations=marker_locations or [],
                custom_prompt=custom_prompt,
                color_scheme=color_scheme,
                design_style=design_style,
            )

            # Configure for Image Generation
            model_name = "gemini-3-pro-image-preview" 
            
            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
            )

            # Add aspect ratio instruction
            final_prompt = f"{generation_prompt}\n\nTechnical Requirement: Generate the image with a 1:1 Square Aspect Ratio."

            # Prepare contents: prompt + original room + product images
            contents = [final_prompt, original_room_image] + product_images

            print(f"🚀 Sending request to {model_name} with {len(product_images)} product images...")
            response = self.client.models.generate_content(
                model=model_name,
                contents=contents,
                config=config,
            )

            generated_image_b64 = None
            
            # Extract image from response
            for part in response.parts:
                if part.inline_data:
                    generated_image_b64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                    print("✅ Successfully generated image")
                    break
            
            if not generated_image_b64:
                 raise ValueError("No image generated in response")

            return generated_image_b64, generation_prompt

        except Exception as e:
            print(f"❌ Error generating product visualization: {e}")
            traceback.print_exc()
            raise e

    def _download_image(self, image_url: str) -> Optional[Image.Image]:
        """Download and return a PIL Image from a URL"""
        try:
            print(f"📥 Downloading product image from: {image_url}")
            
            headers = {
                "User-Agent": "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36"
            }

            # Try direct download first
            response = requests.get(image_url, headers=headers, timeout=10)

            if response.status_code == 200:
                return Image.open(BytesIO(response.content))

            # Try with proxy if direct fails
            print("🔄 Trying with image proxy...")
            proxy_url = f"https://images.weserv.nl/?url={requests.utils.quote(image_url, safe='')}&w=1024&h=1024&fit=cover"
            
            response = requests.get(proxy_url, timeout=15)
            if response.status_code == 200:
                return Image.open(BytesIO(response.content))

            return None

        except Exception as e:
            print(f"❌ Error downloading image: {e}")
            return None

    def _create_integration_prompt(
        self,
        space_type: str,
        product_titles: list,
        inspiration_recommendations: list,
        marker_locations: list,
        custom_prompt: Optional[str] = None,
        color_scheme: Dict[str, Any] = None,
        design_style: Dict[str, Any] = None,
    ) -> str:
        """Create a comprehensive prompt for integrating multiple products into the original room"""
        
        # Build context
        context_parts = []
        
        titles_str = "', '".join(product_titles)
        context_parts.append(f"Task: Integrate the following products into this {space_type} image: '{titles_str}'.")
        
        if custom_prompt:
             context_parts.append(f"User Request: {custom_prompt}")

        if inspiration_recommendations:
            context_parts.append("Style Guide:\n" + "\n".join(f"- {rec}" for rec in inspiration_recommendations[:3]))

        if marker_locations:
             context_parts.append("Placement Areas:\n" + "\n".join(f"- Marker {i+1}: {m.description}" for i, m in enumerate(marker_locations) if hasattr(m, 'description')))

        if color_scheme:
             palette = color_scheme.get("colors", [])
             if palette:
                 context_parts.append(f"Color Palette: {', '.join(palette)}")
        
        if design_style:
             style = design_style.get("style_name")
             if style:
                 context_parts.append(f"Design Style: {style}")

        context_parts.append("""
        Instructions:
        - seamlessly composite the product into the room
        - match lighting, shadows, and perspective
        - preserve the original room structure (walls, floor, windows)
        - make it look photorealistic and high-design
        """)

        return "\n\n".join(context_parts)
