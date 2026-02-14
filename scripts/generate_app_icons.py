#!/usr/bin/env python3
"""Generate iOS app icons with larger 'Spaces.' text for better readability."""

from PIL import Image, ImageDraw, ImageFont
import os

# Output directory
ICON_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "ios-frontend",
    "ios",
    "Runner",
    "Assets.xcassets",
    "AppIcon.appiconset",
)

# All required icon sizes (filename -> pixel size)
ICON_SIZES = {
    "Icon-App-20x20@1x.png": 20,
    "Icon-App-20x20@2x.png": 40,
    "Icon-App-20x20@3x.png": 60,
    "Icon-App-29x29@1x.png": 29,
    "Icon-App-29x29@2x.png": 58,
    "Icon-App-29x29@3x.png": 87,
    "Icon-App-40x40@1x.png": 40,
    "Icon-App-40x40@2x.png": 80,
    "Icon-App-40x40@3x.png": 120,
    "Icon-App-60x60@2x.png": 120,
    "Icon-App-60x60@3x.png": 180,
    "Icon-App-76x76@1x.png": 76,
    "Icon-App-76x76@2x.png": 152,
    "Icon-App-83.5x83.5@2x.png": 167,
    "Icon-App-1024x1024@1x.png": 1024,
}

# Design parameters
BG_COLOR = (255, 255, 255)
TEXT_COLOR = (0, 0, 0)  # Pure black for maximum contrast at small sizes
TEXT = "Spaces."
TARGET_WIDTH_RATIO = 0.90  # Text fills 90% of icon width
SUPERSAMPLE_FACTOR = 4  # Render at 4x then downscale for crisp anti-aliasing

# Font: SF Pro (variable font) set to Black weight for maximum boldness
FONT_PATH = "/System/Library/Fonts/SFNS.ttf"


def _load_font(font_size: int) -> ImageFont.FreeTypeFont:
    """Load SF NS font at Black weight (1000)."""
    font = ImageFont.truetype(FONT_PATH, font_size)
    # Set variable font axes: Weight=1000 (Black), Width=100 (normal)
    font.set_variation_by_axes([100, 28, 400, 1000])
    return font


def generate_icon(size: int, output_path: str) -> None:
    """Generate a single icon at the given pixel size."""
    # Supersample: render at higher resolution then downscale for crisp edges
    render_size = size * SUPERSAMPLE_FACTOR if size < 512 else size

    img = Image.new("RGB", (render_size, render_size), BG_COLOR)
    draw = ImageDraw.Draw(img)

    target_text_width = render_size * TARGET_WIDTH_RATIO

    # Binary search for the right font size to fill target width
    lo, hi = 1, render_size
    best_font_size = 1
    while lo <= hi:
        mid = (lo + hi) // 2
        font = _load_font(mid)
        bbox = draw.textbbox((0, 0), TEXT, font=font)
        text_width = bbox[2] - bbox[0]
        if text_width <= target_text_width:
            best_font_size = mid
            lo = mid + 1
        else:
            hi = mid - 1

    font = _load_font(best_font_size)
    bbox = draw.textbbox((0, 0), TEXT, font=font)
    text_width = bbox[2] - bbox[0]
    text_height = bbox[3] - bbox[1]

    # Center text in the icon
    x = (render_size - text_width) / 2 - bbox[0]
    y = (render_size - text_height) / 2 - bbox[1]

    draw.text((x, y), TEXT, fill=TEXT_COLOR, font=font)

    # Downscale to target size with high-quality resampling
    if render_size != size:
        img = img.resize((size, size), Image.LANCZOS)

    img.save(output_path, "PNG")


def main():
    os.makedirs(ICON_DIR, exist_ok=True)

    for filename, pixel_size in ICON_SIZES.items():
        output_path = os.path.join(ICON_DIR, filename)
        generate_icon(pixel_size, output_path)
        print(f"Generated {filename} ({pixel_size}x{pixel_size}px)")

    print(f"\nAll {len(ICON_SIZES)} icons generated in {ICON_DIR}")


if __name__ == "__main__":
    main()
