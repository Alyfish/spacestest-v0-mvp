from models import BatchFurnitureAnalysisRequest, BatchFurnitureAnalysisResponse
from supabase_data_manager import SupabaseDataManager


def _dm() -> SupabaseDataManager:
    # Bypass __init__ to avoid real Supabase setup in unit tests.
    return SupabaseDataManager.__new__(SupabaseDataManager)


def test_normalize_clip_text_value_handles_dict_and_scalar_inputs():
    dm = _dm()

    assert dm._normalize_clip_text_value({"name": "mid-century modern"}) == "mid-century modern"
    assert dm._normalize_clip_text_value({"label": "walnut"}) == "walnut"
    assert dm._normalize_clip_text_value("  table lamp ") == "table lamp"
    assert dm._normalize_clip_text_value({"unknown": "value"}, default="fallback") == "fallback"


def test_build_items_validate_against_batch_response_schema():
    dm = _dm()

    ok_item = dm._build_furniture_analysis_item(
        selection_id="sel_ok",
        label="accent chair",
        confidence=0.91,
        style="modern",
        material="wood",
        color="black",
        search_query="accent chair buy online",
        products=[
            {
                "title": "Chair",
                "url": "https://example.com/chair",
                "image_url": "https://example.com/chair.jpg",
            }
        ],
        is_bed=False,
        click_x=0.42,
        click_y=0.31,
    )
    error_item = dm._build_furniture_analysis_item(
        selection_id="sel_err",
        label="unknown",
        confidence=0.0,
        style="",
        material="",
        color="",
        search_query="furniture buy online",
        products=[],
        is_bed=False,
        click_x=0.11,
        click_y=0.77,
        error="spatial detector timeout",
    )

    payload = {
        "project_id": "project_123",
        "selections": [ok_item, error_item],
        "overall_analysis": "",
        "total_items": 2,
        "status": "success",
        "message": "Analyzed 2 furniture items",
    }

    validated = BatchFurnitureAnalysisResponse.model_validate(payload)

    assert validated.total_items == 2
    assert validated.selections[0].id == "sel_ok"
    assert validated.selections[0].furniture_type == "accent chair"
    assert validated.selections[1].id == "sel_err"
    assert validated.selections[1].furniture_type == "unknown"


def test_normalize_spatial_detection_supports_current_shape():
    dm = _dm()

    normalized = dm._normalize_spatial_detection(
        {
            "label": "bed frame",
            "bbox_normalized": [0.2, 0.1, 0.8, 0.9],
            "attributes": {"color": "white", "material": "wood", "style": "modern"},
            "search_query": "white modern bed frame",
            "confidence": 0.93,
            "additional_items": [
                {
                    "label": "pillow",
                    "bbox_normalized": [0.45, 0.35, 0.62, 0.58],
                    "color": "ivory",
                    "material": "cotton",
                }
            ],
        },
        click_x=0.5,
        click_y=0.5,
    )

    assert normalized is not None
    assert normalized["label"] == "bed frame"
    assert normalized["bbox_normalized"] == [0.2, 0.1, 0.8, 0.9]
    assert normalized["attributes"]["material"] == "wood"
    assert normalized["additional_items"][0]["label"] == "pillow"


def test_normalize_spatial_detection_supports_legacy_shape():
    dm = _dm()

    normalized = dm._normalize_spatial_detection(
        {
            "primary_item": {
                "label": "table lamp",
                "bounding_box": {"x1": 0.4, "y1": 0.2, "x2": 0.6, "y2": 0.7},
                "color": "gold",
                "material": "metal",
                "style": "modern",
                "search_query": "gold table lamp",
            },
            "additional_items": [
                {
                    "label": "nightstand",
                    "bounding_box": {"x1": 0.35, "y1": 0.6, "x2": 0.7, "y2": 0.95},
                    "color": "brown",
                    "material": "wood",
                }
            ],
        },
        click_x=0.5,
        click_y=0.5,
    )

    assert normalized is not None
    assert normalized["label"] == "table lamp"
    assert normalized["bbox_normalized"] == [0.2, 0.4, 0.7, 0.6]
    assert normalized["search_query"] == "gold table lamp"
    assert normalized["additional_items"][0]["label"] == "nightstand"


def test_extract_clip_confidence_prefers_nested_payload():
    dm = _dm()

    assert dm._extract_clip_confidence(
        {"furniture_type": {"name": "bed", "confidence": 0.86}}
    ) == 0.86
    assert dm._extract_clip_confidence({"confidence": 0.61}) == 0.61
    assert dm._extract_clip_confidence(
        {"furniture_type": {"name": "chair", "confidence": 0.42}, "confidence": 0.77}
    ) == 0.77


def test_flatten_bed_components_backfills_top_level_products():
    dm = _dm()

    flattened = dm._flatten_bed_component_products(
        {
            "bed_frame": [
                {"title": "Walnut Frame", "url": "https://example.com/frame"},
            ],
            "pillows": [
                {"title": "Ivory Pillow", "url": "https://example.com/pillow"},
                {"title": "Ivory Pillow", "url": "https://example.com/pillow"},
            ],
        },
        max_items=12,
    )

    assert len(flattened) == 2
    urls = [item.get("url") for item in flattened]
    assert "https://example.com/frame" in urls
    assert "https://example.com/pillow" in urls


def test_batch_request_mode_defaults_to_full():
    req = BatchFurnitureAnalysisRequest(
        selections=[{"id": "sel_1", "x": 0.4, "y": 0.5}],
        image_type="product",
    )
    assert req.mode == "full"


def test_batch_request_mode_accepts_legacy_click():
    req = BatchFurnitureAnalysisRequest(
        selections=[{"id": "sel_1", "x": 0.4, "y": 0.5}],
        image_type="product",
        mode="click",
    )
    assert req.mode == "click"
