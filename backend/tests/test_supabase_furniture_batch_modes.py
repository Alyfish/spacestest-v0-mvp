import logging
import time
from io import BytesIO

from PIL import Image

from models import BatchFurnitureAnalysisResponse, ProjectContext
from supabase_data_manager import SupabaseDataManager


class _LensSerpClient:
    def __init__(self, delay_s: float = 0.0):
        self.delay_s = delay_s

    def reverse_image_search(self, image_url: str, num_results: int = 10):
        if self.delay_s:
            time.sleep(self.delay_s)
        return [
            {
                "title": "Sample Product",
                "link": "https://example.com/product",
                "thumbnail": "https://example.com/image.jpg",
                "source": "Example",
            }
        ]


class _FailingExaClient:
    def search_and_analyze_products(self, **kwargs):
        raise RuntimeError("simulated exa failure")


class _ClipClient:
    def is_available(self) -> bool:
        return True

    def analyze_furniture_region(self, crop, crop_ratio=1.0):
        return {
            "furniture_type": {"name": "sofa", "confidence": 0.8},
            "style": "modern",
            "material": "fabric",
            "color": "beige",
            "search_query": "modern beige sofa",
        }


def _build_dm() -> SupabaseDataManager:
    dm = SupabaseDataManager.__new__(SupabaseDataManager)
    dm.logger = logging.getLogger("test.supabase.batch_modes")
    dm._get_project_row = lambda project_id: {"id": project_id}
    dm._get_project_context = (
        lambda project_id: ProjectContext.model_validate({"space_type": "living_room"})
    )

    image = Image.new("RGB", (1200, 800), color="white")
    image_buf = BytesIO()
    image.save(image_buf, format="JPEG")
    raw_bytes = image_buf.getvalue()

    dm._get_pil_image_from_storage = lambda project_id, storage_type: (image, raw_bytes)
    dm._prepare_crop_for_search = lambda crop, target_size=512: crop
    dm.upload_image_to_imgbb = lambda image_b64: "https://example.com/crop.jpg"
    dm._detect_bed_sub_components = lambda crop_b64: {}
    dm._search_bed_components = lambda *args, **kwargs: {}
    dm._validate_product_pages_with_exa = lambda products, max_validate=8: products
    dm.gemini_client = None
    dm.clip_client = None
    dm.serp_client = None
    dm.exa_client = None
    return dm


def _selection_payload():
    return [{"id": "sel_1", "x": 0.5, "y": 0.5, "label": "Sofa"}]


def _validate_batch_schema(payload):
    BatchFurnitureAnalysisResponse.model_validate(
        {
            "project_id": payload["project_id"],
            "selections": payload["selections"],
            "overall_analysis": payload.get("overall_analysis", ""),
            "total_items": len(payload["selections"]),
            "status": payload.get("status", "success"),
            "message": "ok",
        }
    )


def test_fast_prefetch_skips_exa_query_expansion():
    dm = _build_dm()
    dm.serp_client = _LensSerpClient()
    dm.exa_client = object()
    dm._generate_multi_queries = lambda *args, **kwargs: (_ for _ in ()).throw(
        AssertionError("fast_prefetch should skip Exa query generation")
    )

    result = dm.analyze_furniture_batch(
        "project_1",
        _selection_payload(),
        image_type="inspiration",
        mode="fast_prefetch",
    )

    assert len(result["selections"]) == 1
    assert result["selections"][0]["products"]
    _validate_batch_schema(result)


def test_lens_timeout_returns_schema_safe_partial_item():
    dm = _build_dm()
    dm.serp_client = _LensSerpClient(delay_s=1.0)

    base_profile_fn = dm._analysis_mode_profile
    dm._analysis_mode_profile = lambda mode: {
        **base_profile_fn(mode),
        "selection_budget_s": 1.0,
        "imgbb_timeout": 0.15,
        "lens_timeout": 0.15,
    }

    result = dm.analyze_furniture_batch(
        "project_1",
        _selection_payload(),
        image_type="inspiration",
        mode="fast_prefetch",
    )

    selection = result["selections"][0]
    assert selection["id"] == "sel_1"
    assert isinstance(selection["products"], list)
    _validate_batch_schema(result)


def test_full_mode_stays_schema_valid_on_partial_failures():
    dm = _build_dm()
    dm.serp_client = _LensSerpClient()
    dm.exa_client = _FailingExaClient()
    dm.clip_client = _ClipClient()
    dm._generate_multi_queries = lambda label, attrs: ["modern sofa"]

    result = dm.analyze_furniture_batch(
        "project_1",
        _selection_payload(),
        image_type="inspiration",
        mode="full",
    )

    selection = result["selections"][0]
    assert selection["furniture_type"]
    assert "search_query" in selection
    _validate_batch_schema(result)


def test_synthetic_sub_hotspots_added_for_single_large_box():
    dm = _build_dm()
    detections = [
        {
            "label": "sofa",
            "rect": {"x": 0.05, "y": 0.10, "width": 0.86, "height": 0.78},
            "center": {"x": 0.48, "y": 0.49},
            "confidence": 0.92,
            "source": "gemini",
        }
    ]

    output = dm._synthesize_sub_hotspots_for_large_box(detections)

    assert len(output) > 1
    assert any(d.get("source") == "synthetic_split" for d in output)


def test_auto_detect_active_resolves_to_inspiration_generated_when_generated_missing():
    dm = _build_dm()
    image = Image.new("RGB", (1200, 800), color="white")
    image_buf = BytesIO()
    image.save(image_buf, format="JPEG")
    raw_bytes = image_buf.getvalue()

    seen_storage_types = []

    def _get_pil(project_id: str, storage_type: str):
        seen_storage_types.append(storage_type)
        return image, raw_bytes

    dm._has_image_type = (
        lambda project_id, image_type: image_type == "inspiration_generated"
    )
    dm._get_pil_image_from_storage = _get_pil
    dm.gemini_client = None
    dm._auto_detect_with_yolo = lambda pil_img: []

    result = dm.auto_detect_furniture("project_1", image_type="active")

    assert seen_storage_types[0] == "inspiration_generated"
    assert result["resolved_image_type"] == "inspiration"
    assert len(result["detections"]) >= 5


def test_analyze_batch_active_resolves_generated_source_without_400_path():
    dm = _build_dm()
    image = Image.new("RGB", (1200, 800), color="white")
    image_buf = BytesIO()
    image.save(image_buf, format="JPEG")
    raw_bytes = image_buf.getvalue()

    seen_storage_types = []

    def _get_pil(project_id: str, storage_type: str):
        seen_storage_types.append(storage_type)
        return image, raw_bytes

    dm._has_image_type = (
        lambda project_id, image_type: image_type == "inspiration_generated"
    )
    dm._get_pil_image_from_storage = _get_pil
    dm.serp_client = _LensSerpClient()

    result = dm.analyze_furniture_batch(
        "project_1",
        _selection_payload(),
        image_type="active",
        mode="fast_prefetch",
    )

    assert seen_storage_types[0] == "inspiration_generated"
    assert result["resolved_image_type"] == "inspiration"
    assert len(result["selections"]) == 1


def test_min_hotspot_logic_returns_at_least_five_candidates():
    dm = _build_dm()

    output = dm._ensure_min_auto_hotspot_count([], min_count=5)

    assert len(output) >= 5
    assert any(d.get("source") == "synthetic_anchor" for d in output)


def test_synthetic_anchor_generation_obeys_overlap_and_distance_guards():
    dm = _build_dm()
    base = [
        {
            "label": "sofa",
            "rect": {"x": 0.12, "y": 0.20, "width": 0.18, "height": 0.14},
            "center": {"x": 0.21, "y": 0.27},
            "confidence": 0.9,
            "source": "gemini",
        }
    ]

    output = dm._ensure_min_auto_hotspot_count(base, min_count=5)
    synthetic = [d for d in output if d.get("source") == "synthetic_anchor"]

    assert len(output) >= 5
    assert synthetic
    for candidate in synthetic:
        for existing in output:
            if candidate is existing:
                continue
            assert dm._rect_iou(candidate, existing) < 0.55
            assert dm._center_distance(candidate, existing) >= 0.12


def test_aspect_normalization_preserves_base_aspect_ratio():
    dm = _build_dm()
    base_img = Image.new("RGB", (1200, 800), color="white")
    base_buf = BytesIO()
    base_img.save(base_buf, format="JPEG")
    base_bytes = base_buf.getvalue()

    dm._get_pil_image_from_storage = lambda project_id, storage_type: (
        base_img,
        base_bytes,
    )

    generated_img = Image.new("RGB", (1000, 1000), color="gray")
    generated_buf = BytesIO()
    generated_img.save(generated_buf, format="PNG")

    normalized, adjusted = dm._normalize_generated_image_aspect(
        "project_1",
        generated_buf.getvalue(),
    )
    output_img = Image.open(BytesIO(normalized))

    assert adjusted is True
    assert abs((output_img.width / output_img.height) - (1200 / 800)) < 0.01
    assert output_img.width >= generated_img.width
    assert output_img.height >= generated_img.height
