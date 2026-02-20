import logging
from io import BytesIO

from PIL import Image, ImageChops, ImageDraw

from data_manager import DataManager


def _png_bytes(image: Image.Image) -> bytes:
    buf = BytesIO()
    image.save(buf, format="PNG")
    return buf.getvalue()


def test_normalize_generated_image_aspect_pads_without_cropping_content():
    dm = DataManager.__new__(DataManager)
    dm.logger = logging.getLogger("test.data_manager.aspect_normalization")

    generated = Image.new("RGB", (100, 100), color="black")
    draw = ImageDraw.Draw(generated)
    draw.rectangle((0, 0, 49, 99), fill=(10, 120, 220))
    draw.rectangle((50, 0, 99, 99), fill=(220, 90, 10))

    normalized_bytes, adjusted = dm._normalize_generated_image_aspect(
        _png_bytes(generated),
        base_width=300,
        base_height=200,
    )
    normalized = Image.open(BytesIO(normalized_bytes))

    assert adjusted is True
    assert normalized.size == (150, 100)

    offset_x = (normalized.width - generated.width) // 2
    offset_y = (normalized.height - generated.height) // 2
    pasted_region = normalized.crop(
        (offset_x, offset_y, offset_x + generated.width, offset_y + generated.height)
    )
    assert ImageChops.difference(pasted_region, generated).getbbox() is None


def test_normalize_generated_image_aspect_skips_when_ratio_already_matches():
    dm = DataManager.__new__(DataManager)
    dm.logger = logging.getLogger("test.data_manager.aspect_normalization")

    generated = Image.new("RGB", (300, 200), color="gray")
    original_bytes = _png_bytes(generated)

    normalized_bytes, adjusted = dm._normalize_generated_image_aspect(
        original_bytes,
        base_width=1200,
        base_height=800,
    )

    assert adjusted is False
    assert normalized_bytes == original_bytes
