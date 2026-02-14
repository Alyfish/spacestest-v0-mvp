#!/usr/bin/env python3
"""Optimize Color and Style Agent prompts using VAPO zero-shot."""
import sys
sys.path.insert(0, '/Users/aly/Desktop/newtest/backend')

from vapo.vapo_client import VAPOClient
import json

client = VAPOClient()

# Current Color Agent prompt (from gemini_client.py lines 263-280)
color_prompt = """You are a world-class interior designer with COMPLETE CREATIVE FREEDOM.
Analyze this space and create the PERFECT color palette from scratch.

IMPORTANT - BE BOLD AND CREATIVE:
- You can choose from MILLIONS of colors - use specific, unique hex codes
- Do NOT default to basic/safe colors like pure white (#FFFFFF), black (#000000), or generic beige
- Consider trending 2025-2026 interior design palettes and unexpected color combinations
- Mix warm and cool tones for visual interest
- Choose colors that would impress clients at a high-end design firm

RETURN EXACTLY 5 DISTINCT COLORS with specific hex codes like:
- Soft terracotta: #E8A87C
- Sage green: #85CDCA
- Dusty rose: #C38D9E
- Deep teal: #2C6E63
- Warm cream: #F5E6D3

Be specific, be creative, be bold - this room deserves a stunning, unique palette."""

# Current Style Agent prompt (from gemini_client.py lines 684-696)
style_prompt = """You are a world-class interior designer with COMPLETE CREATIVE FREEDOM.
Analyze this room and select the PERFECT design style that will transform this space.

IMPORTANT - CHOOSE ANY STYLE THAT FITS BEST:
- You are NOT limited to common styles like "Modern" or "Scandinavian"
- Consider trending 2025-2026 styles: "Quiet Luxury", "Dopamine Decor", "Soft Brutalism", "Organic Modern"
- Consider fusion styles: "Japandi", "Modern Bohemian", "Coastal Grandmother", "Eclectic Maximalism"
- Consider regional styles: "Mediterranean Revival", "Desert Modern", "Pacific Northwest", "Parisian Chic"
- You can even create a unique fusion of multiple styles tailored to this specific space
- Be specific and creative - the more unique and tailored to this room, the better

Look at the room's architecture, lighting, size, and character. What style would make it STUNNING?
Return the exact style name you recommend - it can be any style that exists or a creative fusion."""

print("=" * 60)
print("VAPO Zero-Shot Optimization for Agent Prompts")
print("=" * 60)

# Optimize Color Agent
print("\n🎨 Optimizing Color Agent prompt...")
color_result = client.optimize_zero_shot(color_prompt)
print(f"Success: {color_result['success']}")
if color_result['success']:
    print(f"Guidelines applied: {color_result['applicable_guidelines']}")
    print(f"\n📝 OPTIMIZED COLOR PROMPT:\n{color_result['suggested_prompt']}")
else:
    print(f"Error: {color_result.get('error', 'Unknown error')}")

# Optimize Style Agent
print("\n\n🏠 Optimizing Style Agent prompt...")
style_result = client.optimize_zero_shot(style_prompt)
print(f"Success: {style_result['success']}")
if style_result['success']:
    print(f"Guidelines applied: {style_result['applicable_guidelines']}")
    print(f"\n📝 OPTIMIZED STYLE PROMPT:\n{style_result['suggested_prompt']}")
else:
    print(f"Error: {style_result.get('error', 'Unknown error')}")

# Save results
results = {
    "color_agent": color_result,
    "style_agent": style_result
}
with open("/Users/aly/Desktop/newtest/backend/vapo_optimization_results.json", "w") as f:
    json.dump(results, f, indent=2)
print("\n\n✅ Results saved to vapo_optimization_results.json")
