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
        model: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),  # Gemini 3 Flash
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = None,
    ) -> T:
        """
        Get a structured response from Gemini using JSON schema enforcement

        Args:
            prompt: The input prompt
            pydantic_model: Pydantic model class for structured output
            model: The model to use (default: gemini-3-flash-preview)
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
        model: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),  # Gemini 3 Flash
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
            model: The vision model to use (default: gemini-3-flash-preview)
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

    def analyze_images_with_vision(
        self,
        prompt: str,
        pydantic_model: Type[T],
        image_parts: List[Dict[str, Any]],  # List of {"inline_data": {"mime_type": "...", "data": "base64..."}}
        model: str = "gemini-3-flash-preview",
        max_tokens: Optional[int] = None,
        system_message: Optional[str] = None,
    ) -> T:
        """
        Analyze multiple images using Vision API with structured output.
        Used for batch product evaluation.

        Args:
            prompt: The prompt describing what to analyze
            pydantic_model: Pydantic model class for structured output
            image_parts: List of image dicts with inline_data containing mime_type and base64 data
            model: The vision model to use
            max_tokens: Maximum tokens
            system_message: Optional system message
        """
        try:
            # Convert image_parts to PIL images
            from PIL import Image
            from io import BytesIO
            import base64
            
            contents = [prompt]
            for img_part in image_parts:
                inline_data = img_part.get("inline_data", {})
                img_b64 = inline_data.get("data", "")
                if img_b64:
                    img_bytes = base64.b64decode(img_b64)
                    pil_image = Image.open(BytesIO(img_bytes))
                    contents.append(pil_image)
            
            config = types.GenerateContentConfig(
                response_modalities=["TEXT"],
                response_mime_type="application/json",
                response_schema=pydantic_model,
                temperature=0.3,  # Moderate for evaluation tasks
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
                raise ValueError("Empty response from Gemini Vision (multi-image)")

        except Exception as e:
            print(f"❌ Error in analyze_images_with_vision: {e}")
            raise e

    def analyze_color_application(
        self,
        image_path: str,
        palette_name: str,
        palette_colors: list,
        space_type: str,
        let_ai_decide: bool = False,
        model: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),  # Gemini 3 Flash
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
                # VAPO-optimized prompt (2026-02-07)
                # Guidelines applied: Underspecified, RedundancyInstructions, Reasoning, Structure
                color_context = """### CREATIVE COLOR PALETTE TASK
Analyze this space and propose a professional 5-color palette with rationale.

### INSTRUCTIONS
- Create exactly 5 distinct colors with descriptive names and specific hex codes.
- Be bold and creative - suitable for a high-end design project.
- Consider unexpected combinations and current design trends (2025-2026 palettes).
- Do NOT use generic colors like pure white (#FFFFFF), pure black (#000000), or basic beige.
- Mix warm and cool tones for visual interest.
- Provide a brief rationale explaining why this palette fits the space.

### OUTPUT FORMAT
Include both the palette and justification:

**Example Palette:**
- Soft terracotta: #E8A87C
- Sage green: #85CDCA
- Dusty rose: #C38D9E
- Deep teal: #2C6E63
- Warm cream: #F5E6D3

**Rationale:** [Why these colors work for this specific space]"""
            else:
                color_context = f"""The user has selected the \"{palette_name}\" palette with colors: {', '.join(palette_colors)}.
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


            # Gemini 3 doesn't support additional_properties in schemas, so we request JSON and parse locally
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
                # When let_ai_decide is True and palette is empty, use sensible defaults
                if let_ai_decide and not palette_colors:
                    # Provide default AI-like color choices based on space type
                    primary = [
                        {"hex": "#F5F0E6", "description": "Warm neutral base"},
                        {"hex": "#E8DCC8", "description": "Soft cream accent"}
                    ]
                    secondary = [
                        {"hex": "#A08060", "description": "Earthy mid-tone"},
                        {"hex": "#C8B896", "description": "Natural sand"}
                    ]
                    accent = [{"hex": "#6B4423", "description": "Rich brown accent"}]
                    space_summary = f"AI-selected color scheme for your {space_type}. Warm neutrals create a welcoming, versatile foundation."
                    color_theory = "Analogous"
                    color_rationale = "Warm neutrals and earth tones work harmoniously together for a cohesive, inviting space."
                else:
                    swatches = [{"hex": c, "description": "Palette color"} for c in palette_colors]
                    primary = swatches[:2] or [{"hex": "#E8E4DE", "description": "Light neutral"}]
                    secondary = swatches[2:4] or [{"hex": "#B8AFA6", "description": "Mid-tone neutral"}]
                    accent = swatches[4:5] or [{"hex": "#6B5B4F", "description": "Dark accent"}]
                    space_summary = f"Color guidance for a {space_type} based on the selected palette."
                    color_theory = "Analogous"
                    color_rationale = "Palette tones are adjacent and cohesive."

                assignments = [
                    {
                        "element": "Walls",
                        "color_hex": primary[0]["hex"],
                        "color_name": primary[0]["description"],
                        "finish": "matte",
                        "notes": "Use for dominant wall surfaces.",
                    },
                    {
                        "element": "Textiles",
                        "color_hex": (secondary[0]["hex"] if secondary else primary[0]["hex"]),
                        "color_name": (secondary[0]["description"] if secondary else "Secondary color"),
                        "finish": None,
                        "notes": "Apply to curtains, bedding, or rugs.",
                    },
                    {
                        "element": "Furniture",
                        "color_hex": (primary[1]["hex"] if len(primary) > 1 else primary[0]["hex"]),
                        "color_name": (primary[1]["description"] if len(primary) > 1 else "Furniture color"),
                        "finish": "satin",
                        "notes": "For larger furniture pieces.",
                    },
                    {
                        "element": "Accents",
                        "color_hex": (accent[0]["hex"] if accent else primary[0]["hex"]),
                        "color_name": (accent[0]["description"] if accent else "Accent color"),
                        "finish": None,
                        "notes": "Use for decor and small accessories.",
                    },
                ]
                return {
                    "space_summary": space_summary,
                    "primary_colors": primary,
                    "secondary_colors": secondary,
                    "accent_colors": accent,
                    "color_theory_approach": color_theory,
                    "color_theory_rationale": color_rationale,
                    "color_assignments": assignments,
                    "lighting_notes": "Consider lighting temperature when evaluating final tones.",
                    "cohesion_tips": "Repeat key hues across adjacent spaces for continuity.",
                    "personalization_suggestions": "Rotate accent textiles seasonally for variety.",
                    "palette_adaptations": "AI-generated palette for optimal room aesthetics." if let_ai_decide else None,
                }

            try:
                payload = load_json_payload(response.text)
                print(f"📋 Color Agent raw payload keys: {list(payload.keys())}")
                print(f"📋 Color Agent raw primary_colors: {payload.get('primary_colors', 'NOT FOUND')}")
                print(f"📋 Color Agent raw color_selection: {payload.get('color_selection', 'NOT FOUND')}")
                try:
                    result = ColorAnalysis.model_validate(payload)
                    print(f"✅ Color Agent analysis complete (direct validation)")
                except Exception as direct_err:
                    print(f"⚠️ Direct validation failed: {direct_err}, trying normalization...")
                    normalized = normalize_color_analysis_payload(payload)
                    print(f"📋 Normalized primary_colors: {normalized.get('primary_colors', [])}")
                    print(f"📋 Normalized color_assignments: {normalized.get('color_assignments', [])}")
                    result = ColorAnalysis.model_validate(normalized)
                    print(f"✅ Color Agent analysis complete (after normalization)")
                return result.model_dump()
            except Exception as parse_err:
                print(f"❌ Failed to parse Color Agent response: {parse_err}")
                print(f"Raw response (first 1000 chars): {response.text[:1000]}...")
                print(f"📋 Using fallback color analysis. let_ai_decide={let_ai_decide}, palette_colors={palette_colors}")
                fallback = build_fallback_color_analysis()
                print(f"📋 Fallback primary_colors: {fallback.get('primary_colors', [])}")
                print(f"📋 Fallback color_assignments: {[a.get('color_hex') for a in fallback.get('color_assignments', [])]}")
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
        model: str = os.getenv("GEMINI_MODEL", "gemini-3-flash-preview"),  # Gemini 3 Flash
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
                # VAPO-optimized prompt (2026-02-07)
                # Guidelines applied: Voodoo, Context, Schema, FewShot
                style_context = """### CREATIVE STYLE RECOMMENDATION TASK
Analyze this room and recommend a specific, creative design style with justification.

### INSTRUCTIONS
1. Analyze the room's architecture, lighting, size, and character from the image.
2. Select or create a design style that best suits the space. Be creative and specific.
3. You are not limited to common styles. Consider for inspiration:
   - Trending Styles: "Quiet Luxury", "Dopamine Decor", "Soft Brutalism", "Organic Modern"
   - Fusion Styles: "Japandi", "Modern Bohemian", "Coastal Grandmother", "Eclectic Maximalism"
   - Regional Styles: "Mediterranean Revival", "Desert Modern", "Pacific Northwest", "Parisian Chic"
4. The goal is a unique and tailored recommendation.

### OUTPUT
Provide the style name and justification explaining how it complements the room's features.

### EXAMPLE
For a small attic bedroom with exposed dark wood beams and soft diffused light:
- Style: "Wabi-Sabi Cottage"
- Justification: The exposed beams and old floors align with Wabi-Sabi's appreciation for natural imperfection, fused with Cottage coziness."""
            else:
                style_context = f"""The user has selected the \"{style_name}\" style.
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
        product_images: Optional[List[Dict[str, str]]] = None,
    ) -> str:
        """
        Generate a redesigned room image based on inspiration
        using Gemini 3 Pro Image (Nano Banana Pro)

        Args:
            original_room_image_path: Path to the original room image
            prompt: The generation prompt
            product_images: Optional list of dicts with 'image_url' and 'title' for trending products
        """
        try:
            print(f"🎨 Generating room redesign...")

            # Load room image
            original_room_image = Image.open(original_room_image_path)

            # Download product images if provided
            downloaded_product_images = []
            product_titles = []
            if product_images:
                for product in product_images:
                    img = self._download_image(product.get("image_url", ""))
                    if img:
                        downloaded_product_images.append(img)
                        product_titles.append(product.get("title", "product"))

                if downloaded_product_images:
                    print(f"📦 Downloaded {len(downloaded_product_images)} product reference images")

            # Primary and fallback models for image generation
            primary_model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")
            fallback_model = "gemini-2.5-flash-image"  # Stable fallback for 503 errors

            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                temperature=0.3,  # Low temperature for structure preservation
            )

            # Add product reference instruction if we have product images
            product_reference_text = ""
            if downloaded_product_images:
                product_reference_text = f"""

### PRODUCT REFERENCE IMAGES (CRITICAL)
The following {len(downloaded_product_images)} product reference images are provided. You MUST incorporate these EXACT products into the room:
{chr(10).join([f"- {title}" for title in product_titles])}

MATCH THE PRODUCTS EXACTLY:
- The furniture in the generated image MUST match the exact color shown in the product reference images
- Match the exact texture, pattern, and material appearance from the reference
- Match the exact shape, proportions, and design details
- DO NOT improvise or change any aspect of the product appearance
- Use the product images as authoritative reference for how these items should look"""

            # Add technical requirement for aspect ratio
            final_prompt = f"{prompt}{product_reference_text}\n\nTechnical Requirement: Generate the image with a 1:1 Square Aspect Ratio."

            # Prepare contents: Image FIRST for structure preservation, then prompt, then product images
            contents = [original_room_image, final_prompt] + downloaded_product_images

            # Retry logic: Try primary model multiple times, then fallback
            import time
            max_retries = 3
            retry_delay = 5  # seconds between retries
            generated_image_b64 = None
            model_used = None
            last_error = None

            # Try primary model with retries
            for attempt in range(max_retries):
                try:
                    print(f"🚀 Attempt {attempt + 1}/{max_retries}: Sending request to {primary_model}...")
                    response = self.client.models.generate_content(
                        model=primary_model,
                        contents=contents,
                        config=config,
                    )

                    # Extract image from response
                    for part in response.parts:
                        if part.inline_data:
                            generated_image_b64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                            model_used = primary_model
                            print(f"✅ Successfully generated redesign image with {primary_model}")
                            break

                    if generated_image_b64:
                        break  # Success!

                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    # Check if it's a retryable error (503/overloaded)
                    if "503" in error_str or "overloaded" in error_str or "unavailable" in error_str:
                        if attempt < max_retries - 1:
                            print(f"⚠️ {primary_model} overloaded (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                            continue
                        else:
                            print(f"⚠️ {primary_model} still overloaded after {max_retries} attempts, trying fallback...")
                    else:
                        # Non-recoverable error, raise immediately
                        raise e

            # If primary failed, try fallback model once
            if not generated_image_b64:
                print(f"❌ GEMINI 3 ERROR: {primary_model} failed with: {last_error}")
                try:
                    print(f"🔄 Falling back to {fallback_model}...")
                    response = self.client.models.generate_content(
                        model=fallback_model,
                        contents=contents,
                        config=config,
                    )

                    for part in response.parts:
                        if part.inline_data:
                            generated_image_b64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                            model_used = fallback_model
                            print(f"⚠️ WARNING: Using FALLBACK model {fallback_model} instead of primary {primary_model}")
                            print(f"✅ Successfully generated redesign image with {fallback_model} (fallback)")
                            break

                except Exception as fallback_error:
                    print(f"❌ Fallback model also failed: {fallback_error}")
                    # Raise the original error from primary model
                    if last_error:
                        raise last_error
                    raise fallback_error

            if not generated_image_b64:
                if last_error:
                    raise last_error
                raise ValueError("No image generated in response")

            return generated_image_b64, model_used

        except Exception as e:
            print(f"❌ Error generating room redesign: {e}")
            traceback.print_exc()
            raise e

    def edit_room_with_feedback(
        self,
        generated_image_base64: str,
        user_feedback: str,
    ) -> tuple[str, str]:
        """
        Edit an existing generated room image based on user feedback.

        This is a SURGICAL EDIT operation - preserves the image and only
        modifies what the user specifically requests.

        Args:
            generated_image_base64: Base64 encoded image to edit
            user_feedback: User's modification request (e.g., "remove the lamp")

        Returns:
            Tuple of (edited_image_base64, model_used)
        """
        import time

        try:
            print(f"✏️ Editing room image with user feedback: '{user_feedback[:100]}...'")

            # Decode base64 to PIL Image
            image_bytes = base64.b64decode(generated_image_base64)
            input_image = Image.open(BytesIO(image_bytes))

            # VAPO-optimized prompt v2 (2026-02-07)
            # Guidelines applied: Structure, Underspecified, Reasoning, FewShot
            # Enhanced with interior design principles for proper placement/grounding
            edit_prompt = f"""You are an expert interior designer AND professional photo editor.

### TASK
Edit this room image based on the user's request. This is a SURGICAL EDIT with INTERIOR DESIGN EXPERTISE - you must preserve the original image while making changes that look professionally designed and realistic.

### USER REQUEST
{user_feedback}

### INTERIOR DESIGN PRINCIPLES - CRITICAL
When adding or repositioning items, apply professional design knowledge:

1. **PROPER GROUNDING**: All furniture and decor MUST sit realistically on the floor or appropriate surface
   - Plants must be in pots that sit flat on the floor - never floating or elevated
   - Floor lamps must stand on the floor with visible base
   - Objects must respect gravity and physics

2. **SCALE & PROPORTION**: Items must be appropriately sized for the room
   - Large plants should be 4-6 feet tall for bedrooms/living rooms
   - Floor lamps should be 5-6 feet tall
   - Scale must match existing furniture in the room

3. **PLACEMENT & BALANCE**: Position items where a professional designer would
   - Corner positions for large plants and floor lamps
   - Consider sight lines and room flow
   - Create visual balance with existing furniture
   - Leave appropriate walking space

4. **STYLE COHESION**: New items must match the room's aesthetic
   - Match the existing color palette and materials
   - Complement the design style (modern, traditional, etc.)
   - Coordinate with existing furniture finishes

### IMAGE PRESERVATION CONSTRAINTS
- MAINTAIN original camera angle, perspective, and framing
- MAINTAIN original lighting direction and shadows (new items should cast appropriate shadows)
- NO structural changes to walls, floors, ceiling, windows, doors
- PRESERVE all furniture/decor NOT mentioned in the request

### PHOTOREALISTIC OUTPUT REQUIREMENTS
- The edit must look like a real photograph, not AI-generated
- New items must have realistic shadows matching the room's lighting
- Edges must blend naturally with the environment
- Materials and textures must look authentic

### DESIGN PLANNING (Think step-by-step)
Before generating, plan your edit:
1. What specific changes does the user want?
2. Where exactly should new items be placed (consider design principles)?
3. What style/color should match the existing room?
4. How will shadows and lighting affect new items?

### OUTPUT
Generate the edited room image with professionally designed placement of requested changes.

Technical Requirement: Generate the image with a 1:1 Square Aspect Ratio."""

            # Model configuration
            primary_model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")
            fallback_model = "gemini-2.5-flash-image"

            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                temperature=0.2,  # Very low temperature for maximum fidelity to original
            )

            # Contents: Image FIRST for reference, then edit prompt
            contents = [input_image, edit_prompt]

            # Retry logic
            max_retries = 3
            retry_delay = 5
            edited_image_b64 = None
            model_used = None
            last_error = None

            # Try primary model with retries
            for attempt in range(max_retries):
                try:
                    print(f"🚀 Edit attempt {attempt + 1}/{max_retries}: Sending request to {primary_model}...")
                    response = self.client.models.generate_content(
                        model=primary_model,
                        contents=contents,
                        config=config,
                    )

                    # Extract image from response
                    for part in response.parts:
                        if part.inline_data:
                            edited_image_b64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                            model_used = primary_model
                            print(f"✅ Successfully edited image with {primary_model}")
                            break

                    if edited_image_b64:
                        break

                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    if "503" in error_str or "overloaded" in error_str or "unavailable" in error_str:
                        if attempt < max_retries - 1:
                            print(f"⚠️ {primary_model} overloaded (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                            continue
                        else:
                            print(f"⚠️ {primary_model} still overloaded after {max_retries} attempts, trying fallback...")
                    else:
                        raise e

            # Try fallback model if primary failed
            if not edited_image_b64:
                print(f"❌ GEMINI 3 ERROR: {primary_model} failed with: {last_error}")
                try:
                    print(f"🔄 Falling back to {fallback_model}...")
                    response = self.client.models.generate_content(
                        model=fallback_model,
                        contents=contents,
                        config=config,
                    )

                    for part in response.parts:
                        if part.inline_data:
                            edited_image_b64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                            model_used = fallback_model
                            print(f"⚠️ WARNING: Using FALLBACK model {fallback_model} instead of primary {primary_model}")
                            print(f"✅ Successfully edited image with {fallback_model} (fallback)")
                            break

                except Exception as fallback_error:
                    print(f"❌ Fallback model also failed: {fallback_error}")
                    if last_error:
                        raise last_error
                    raise fallback_error

            if not edited_image_b64:
                if last_error:
                    raise last_error
                raise ValueError("No edited image generated in response")

            return edited_image_b64, model_used, edit_prompt

        except Exception as e:
            print(f"❌ Error editing room image: {e}")
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
        improvement_mode: Optional[str] = None,
        trending_products: list = None,
    ) -> Tuple[str, str, str]:
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

            # Create prompt based on improvement mode
            if improvement_mode == "iterative":
                # Use iterative/surgical prompt for targeted improvements with additional styling
                print(f"🔧 Using ITERATIVE prompt (enhanced surgical edits with {len(trending_products or [])} trending products)")
                generation_prompt = self._create_iterative_prompt(
                    selected_products=selected_products,
                    marker_locations=marker_locations or [],
                    trending_products=trending_products,
                    style_analysis=design_style,
                    color_scheme=color_scheme,
                )
            else:
                # Use revamp prompt for complete redesign (default)
                print(f"🎨 Using REVAMP prompt (full redesign)")
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
            # Lower temperature = more adherent to input structure (reduces "creative" reinterpretation)
            primary_model = os.getenv("GEMINI_IMAGE_MODEL", "gemini-3-pro-image-preview")
            fallback_model = "gemini-2.5-flash-image"  # Stable fallback for 503 errors

            config = types.GenerateContentConfig(
                response_modalities=["IMAGE"],
                temperature=0.3,  # Low temperature for structure preservation
            )

            # Add aspect ratio instruction
            final_prompt = f"{generation_prompt}\n\nTechnical Requirement: Generate the image with a 1:1 Square Aspect Ratio."

            # Prepare contents: Image FIRST for structure preservation, then prompt, then product images
            # Order matters: putting original room image first forces model to preserve its structure
            contents = [original_room_image, final_prompt] + product_images

            # Retry logic: Try primary model multiple times, then fallback
            import time
            max_retries = 3
            retry_delay = 5  # seconds between retries
            generated_image_b64 = None
            model_used = None
            last_error = None

            # Try primary model with retries
            for attempt in range(max_retries):
                try:
                    print(f"🚀 Attempt {attempt + 1}/{max_retries}: Sending request to {primary_model} with {len(product_images)} product images...")
                    response = self.client.models.generate_content(
                        model=primary_model,
                        contents=contents,
                        config=config,
                    )

                    # Extract image from response
                    for part in response.parts:
                        if part.inline_data:
                            generated_image_b64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                            model_used = primary_model
                            print(f"✅ Successfully generated image with {primary_model}")
                            break

                    if generated_image_b64:
                        break  # Success!

                except Exception as e:
                    last_error = e
                    error_str = str(e).lower()
                    # Check if it's a retryable error (503/overloaded)
                    if "503" in error_str or "overloaded" in error_str or "unavailable" in error_str:
                        if attempt < max_retries - 1:
                            print(f"⚠️ {primary_model} overloaded (attempt {attempt + 1}/{max_retries}), retrying in {retry_delay}s...")
                            time.sleep(retry_delay)
                            continue
                        else:
                            print(f"⚠️ {primary_model} still overloaded after {max_retries} attempts, trying fallback...")
                    else:
                        # Non-recoverable error, raise immediately
                        raise e

            # If primary failed, try fallback model once
            if not generated_image_b64:
                print(f"❌ GEMINI 3 ERROR: {primary_model} failed with: {last_error}")
                try:
                    print(f"🔄 Falling back to {fallback_model}...")
                    response = self.client.models.generate_content(
                        model=fallback_model,
                        contents=contents,
                        config=config,
                    )

                    for part in response.parts:
                        if part.inline_data:
                            generated_image_b64 = base64.b64encode(part.inline_data.data).decode('utf-8')
                            model_used = fallback_model
                            print(f"⚠️ WARNING: Using FALLBACK model {fallback_model} instead of primary {primary_model}")
                            print(f"✅ Successfully generated image with {fallback_model} (fallback)")
                            break

                except Exception as fallback_error:
                    print(f"❌ Fallback model also failed: {fallback_error}")
                    # Raise the original error from primary model
                    if last_error:
                        raise last_error
                    raise fallback_error

            if not generated_image_b64:
                if last_error:
                    raise last_error
                raise ValueError("No image generated in response")

            return generated_image_b64, generation_prompt, model_used

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
        """Create an improved prompt for Elite Interior Design Visualization"""

        # Build dynamic context from inputs
        titles_str = ", ".join(product_titles) if product_titles else "new furniture items"

        # Extract style information
        style_name = "professionally-designed, harmonious"
        style_overview = ""
        materials_list = ""
        if design_style:
            style_name = design_style.get("style_name", "Modern")
            style_overview = design_style.get("style_overview", "")
            materials = design_style.get("materials", [])
            if materials:
                materials_list = ", ".join(materials[:7])

        # Extract color palette
        color_list = ""
        if color_scheme:
            # Handle both old format (colors list) and new format (primary/secondary/accent)
            if "colors" in color_scheme:
                color_list = ", ".join(color_scheme.get("colors", []))
            else:
                colors = []
                for key in ["primary_colors", "secondary_colors", "accent_colors"]:
                    for c in color_scheme.get(key, []):
                        if isinstance(c, dict):
                            colors.append(f"{c.get('hex', '')} ({c.get('description', '')})")
                        else:
                            colors.append(str(c))
                color_list = ", ".join(colors[:6])

        # Build marker descriptions
        marker_descriptions = ""
        if marker_locations:
            markers = []
            for i, m in enumerate(marker_locations):
                if hasattr(m, 'description'):
                    markers.append(f"- Marker {i+1}: {m.description}")
                elif isinstance(m, dict) and 'description' in m:
                    markers.append(f"- Marker {i+1}: {m['description']}")
            if markers:
                marker_descriptions = "\n".join(markers)

        # User custom request
        user_request = custom_prompt if custom_prompt else ""

        # THE COMPLETE REVAMP / INTEGRATION PROMPT
        prompt = f"""### ROLE & OBJECTIVE
You are an Elite Interior Design Visualizer and Architectural Photographer.
Your task is to digitally stage the PROVIDED ROOM PHOTO by EDITING IT (not re-generating a new camera view).
Goal: a hyper-realistic "After" photo that looks like the user bought new furniture and took another photo from the same spot.

### PRIORITY ORDER (HARD RULES)
If any instructions conflict, follow this order:
1) CAMERA/GEOMETRY LOCK
2) LIGHTING/EXPOSURE/WHITE BALANCE LOCK
3) MARKERS + USER REQUEST (what to replace)
4) PRODUCT REFERENCE MATCHING
5) STYLE + STYLING ADDITIONS

### 1) THE "IMMUTABLE WORLD" (STRICT CONSTRAINTS)
You are a decorator, not a builder. You are EDITING the original photograph — NOT creating a new room.

**CAMERA & FRAMING LOCK (ABSOLUTE)**
- Do NOT change camera position, angle, focal length, field of view, crop, rotation, or perspective.
- Do NOT "recompose" the scene.
- The output must align with the original photo's background edges (wall corners, baseboards, outlets) with no drift.
- Maintain the exact lens focal length, camera angle, horizon line, and field of view of the original photo.
- The vanishing points and perspective lines must align precisely with the original.
FAIL CONDITION: If framing/perspective changes, the output is INVALID.

**STRUCTURAL LOCKDOWN (ABSOLUTE — NO EXCEPTIONS)**
The following elements are LOCKED and must appear IDENTICAL to the original photo:
- Wall positions, angles, colors, and textures
- Ceiling height and features
- Window frames, sizes, positions, and COUNT — do NOT add or remove windows
- Door locations, sizes, and frames — do NOT add or remove doors
- Flooring material, pattern, and boundaries
- Electrical outlets, switches, baseboards, moldings, and trim
- Room dimensions and geometry — the room must be the SAME SIZE
CRITICAL: Do NOT invent, add, or hallucinate any structural element not visible in the original photo. If the original has 1 window, the output has 1 window. If a wall is blank, it stays blank unless a marker explicitly says to add wall decor.

**LIGHTING**
- Do NOT change time of day, shadow direction/hardness, exposure, or white balance.
- Any flash/harsh shadows/noise in the original must remain consistent.

**BACKGROUND OBJECTS**
- Do NOT remove background clutter (cords, bottles, random items) unless a marker explicitly says to remove.

### 2) DESIGN INTELLIGENCE (Apply {style_name})
You are designing, not just pasting.

**Cohesion (FULL REVAMP)**
- Replace key furniture and decor as needed to achieve a complete revamp, while keeping the room shell identical.
- Automatically generate cohesive supporting pieces (e.g., nightstands, lamps, rug, pillows, throw, wall art) that match the style and palette.

**Styling (Make it feel real)**
- Bedding must look heavy, soft, and lived-in (wrinkles, weight, layers).
- Add subtle "real-life" props (e.g., 1 book + 1 small object) ONLY where physically plausible.

**Palette discipline**
- Strictly adhere to the Target Palette. Use it primarily in textiles + accents; keep large surfaces calm and {style_name}.

### 3) EXECUTION PLAN (Step-by-Step)
**Step A: Anchor replacements (Markers + User Selections)**
- Replace the items indicated by markers.
- If product reference images exist, match their silhouette, materials, and color very closely.

**Step B: Full revamp fill-in (AI design)**
- Add only what's needed to create a complete, cohesive {style_name} room:
  - rug if appropriate
  - coordinated lamps
  - pillows/throw layering
  - minimal wall decor if walls are bare
Keep it uncluttered.

**Step C: Reality pass (Render physics)**
- Occlusion: objects must block background correctly.
- Contact shadows: strong, realistic ambient occlusion at the floor/wall.
- Cast shadows: match original direction and hardness.
- Sensor match: match grain/noise and focus blur so new items do not look pasted.

### 4) INPUT DATA CONTEXT
- Space Type: {space_type}
- Design Style: {style_name} - {style_overview}
- Key Materials: {materials_list}
- Target Palette (HEX): {color_list}
- Specific Changes (Markers):
{marker_descriptions}
- Product References: {titles_str}
- User Request: {user_request}

### SPATIAL VERIFICATION (Self-Check Before Output)
Before finalizing, verify against the original photo:
- Does the room appear the same physical size?
- Are all walls in the same positions and at the same angles?
- Is the window count and door count identical to the original?
- Do vanishing points and perspective lines match?
- Would a person of average height fit the same way in both images?

### OUTPUT REQUIREMENT
- Output a 1:1 square image.
- Must look like a mundane, realistic phone photo of the SAME ROOM, same camera, same lighting.
- Preserve original ISO grain + color cast across inserted items.

### NEGATIVE INSTRUCTIONS (ANTI-FAIL)
- Do NOT move the bed to a "better" spot.
- Do NOT change camera angle, crop, or widen the room.
- Do NOT clean the room or remove clutter unless told.
- Do NOT produce studio lighting or showroom perfection.
- Do NOT add walls, windows, doors, arches, columns, or any architectural element not in the original.
- Do NOT change room dimensions or make the room appear larger or smaller.
- Do NOT assume or infer structural features — only what is VISIBLE in the photo exists."""

        return prompt

    def _create_iterative_prompt(
        self,
        selected_products: list,
        marker_locations: list,
        trending_products: list = None,
        style_analysis: dict = None,
        color_scheme: dict = None,
    ) -> str:
        """Create a surgical/iterative prompt for targeted furniture replacement.

        This prompt focuses on small, precise changes - replacing specific items
        and adding a few complementary styling pieces to enhance the room.

        Args:
            selected_products: User-selected products to insert
            marker_locations: Markers indicating what to change
            trending_products: Additional trending products for styling suggestions
            style_analysis: Design style context (materials, characteristics)
            color_scheme: Color palette context (primary, secondary, accent colors)
        """

        # 1. Format the specific changes from markers
        changes_list = []
        for i, m in enumerate(marker_locations):
            if hasattr(m, 'description'):
                desc = m.description
                pos = f"({m.position.x:.2f}, {m.position.y:.2f})" if hasattr(m, 'position') else "marked area"
            elif isinstance(m, dict):
                desc = m.get('description', 'Replace item')
                pos_data = m.get('position', {})
                pos = f"({pos_data.get('x', 0):.2f}, {pos_data.get('y', 0):.2f})"
            else:
                desc = "Replace item"
                pos = "marked area"
            changes_list.append(f"TARGET AREA {i+1}: At position {pos}, remove existing item and {desc}.")
        changes_str = "\n".join(changes_list) if changes_list else "No specific markers provided."

        # 2. Format the specific products (user-selected)
        product_details = []
        for p in selected_products:
            title = p.get('title', 'Unknown product')
            store = p.get('store', 'Unknown')
            product_details.append(f"- INSERT ITEM: {title} (Source: {store})")
        products_str = "\n".join(product_details) if product_details else "No products specified."

        # 3. Format additional recommendations (trending + complementary)
        additional_recommendations = []

        # Add trending products as styling suggestions
        if trending_products:
            for tp in trending_products[:2]:  # Max 2 trending products
                title = tp.get('title', 'Unknown')
                additional_recommendations.append(f"- TRENDING: {title}")

        # Add AI-suggested complementary items based on style/color
        if style_analysis:
            style_name = style_analysis.get('style_name', '')
            materials = style_analysis.get('materials', [])
            if style_name:
                additional_recommendations.append(f"- STYLE SUGGESTION: Add a {style_name}-inspired accent piece (throw pillow, small vase, or decorative object)")
            if materials:
                mat_str = ", ".join(materials[:2]) if isinstance(materials, list) else str(materials)
                additional_recommendations.append(f"- MATERIAL SUGGESTION: Incorporate {mat_str} textures in props")

        if color_scheme:
            accent_color = color_scheme.get('accent', {}).get('name', '')
            if accent_color:
                additional_recommendations.append(f"- COLOR SUGGESTION: Add a small accent in {accent_color} tone")

        additional_str = "\n".join(additional_recommendations) if additional_recommendations else "Use your design judgment to add 1-2 complementary styling props."

        # 4. The "Iterative / Enhanced Surgical" Prompt - SMALL CHANGES WITH STYLING
        prompt = f"""### ROLE & OBJECTIVE
You are a High-End Virtual Stager and Architectural Retoucher.
Your task is to perform an Enhanced Surgical Design Upgrade by EDITING the PROVIDED ROOM PHOTO (not re-generating a new view).
Goal: a polished "glow-up" that upgrades the room's value with targeted improvements and thoughtful styling additions.

### PRIORITY ORDER (HARD RULES)
If any instructions conflict, follow this order:
1) CAMERA/GEOMETRY LOCK
2) LIGHTING/EXPOSURE/WHITE BALANCE LOCK
3) MARKERS (what to change) + DELTA BUDGET (how much can change)
4) PRODUCT REFERENCE MATCHING
5) ADDITIONAL STYLING RECOMMENDATIONS
6) MICRO-STYLING PROTOCOL

### 1) CAMERA & GEOMETRY LOCK (ABSOLUTE PRIORITY)
- Pixel alignment required: walls/windows/ceiling/background edges must match the original photo.
- No zoom/crop/rotation/recompose.
- Maintain the exact lens focal length, camera angle, horizon line, and field of view of the original photo.
- The vanishing points and perspective lines must align precisely with the original.
FAIL CONDITION: Any visible framing/perspective drift makes the result INVALID.

### 2) STRUCTURAL LOCKDOWN (ABSOLUTE — NO EXCEPTIONS)
You are EDITING the original photograph — NOT creating a new room.
The following elements are LOCKED and must appear IDENTICAL to the original photo:
- Wall positions, angles, colors, and textures
- Ceiling height and features
- Window frames, sizes, positions, and COUNT — do NOT add or remove windows
- Door locations, sizes, and frames — do NOT add or remove doors
- Flooring material, pattern, and boundaries
- Electrical outlets, switches, baseboards, moldings, and trim
- Room dimensions and geometry — the room must be the SAME SIZE
CRITICAL: Do NOT invent, add, or hallucinate any structural element not visible in the original photo. If the original has 1 window, the output has 1 window. If a wall is blank, it stays blank unless a marker explicitly says to add wall decor.
- Do NOT paint walls, change flooring, or remove clutter unless markers explicitly instruct it.
- Do NOT change time-of-day or lighting style; match original exposure + shadow hardness.

### 3) ENHANCED ITERATIVE UPGRADE (EXPANDED DELTA BUDGET)
This is still NOT a full revamp, but allows for a more complete styling upgrade.

**DELTA BUDGET (EXPANDED)**
- You may change UP TO:
  - 2-3 small anchor items (e.g., bedding + throw pillows, OR nightstand + lamp, OR rug + accent chair)
  - Focus on items that work together as a cohesive upgrade
- You may add UP TO:
  - 3-4 styling props total (e.g., books, vases, plants, decorative objects)
  - Props should be placed naturally throughout the visible area, not just next to changed items
- You may NOT move large furniture positions (layout stays identical)
- You may NOT replace ALL furniture at once - keep 60-70% of the room unchanged

### 4) SURGICAL INTEGRATION (Physics)
- Contact shadows and ambient occlusion must match the existing floor.
- Cast shadows must match the existing direction/hardness.
- Match ISO grain/noise, blur, and white balance so edits don't look like stickers.

### 5) THE "GLOW UP" PROTOCOL (Micro-styling)
- If changing bedding: add layering (throw + pillows) within palette, keep it realistic and slightly wrinkled.
- If changing a nightstand: style with 1-2 small items on top.
- If changing a lamp: keep placement identical; upgrade lamp design/material only.
- Add subtle "real-life" touches: a book, small plant, or decorative object where appropriate.

### 6) INPUT DATA CONTEXT
**Step A: Remove & Replace (Markers)**
{changes_str}

**Step B: Insert User-Selected Products**
{products_str}
(Match materials/colors of these products exactly to their reference images.)

**Step C: Additional Styling Recommendations**
{additional_str}
(Use these suggestions to enhance the room with complementary styling. Pick 1-2 that work well with Step A and B.)

### SPATIAL VERIFICATION (Self-Check Before Output)
Before finalizing, verify against the original photo:
- Does the room appear the same physical size?
- Are all walls in the same positions and at the same angles?
- Is the window count and door count identical to the original?
- Do vanishing points and perspective lines match?
- Would a person of average height fit the same way in both images?

### OUTPUT REQUIREMENT
- Output a 1:1 square image.
- Must look like the SAME photo, same camera, same lighting—but noticeably improved with cohesive styling.
- Keep background clutter unless explicitly instructed.
- The result should feel like a professional stylist made targeted upgrades.

### NEGATIVE INSTRUCTIONS (ANTI-FAIL)
- Do NOT recompose, crop, zoom, rotate, or change perspective.
- Do NOT "upgrade" by moving the bed or changing layout.
- Do NOT do a full redesign; respect the expanded but limited delta budget.
- Do NOT exceed 3-4 styling props total.
- Do NOT add walls, windows, doors, arches, columns, or any architectural element not in the original.
- Do NOT change room dimensions or make the room appear larger or smaller.
- Do NOT assume or infer structural features — only what is VISIBLE in the photo exists."""

        return prompt

