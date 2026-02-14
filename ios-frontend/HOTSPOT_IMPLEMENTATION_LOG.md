# Dream Space Hotspots Implementation Log

Date: 2026-02-14
Scope: Ready-first hotspot loading, robust empty-hotspot fallback, marker alignment, and product/price cleanup.

## What Was Implemented

- Added ready-first hotspot preparation after image generation and retry:
  - Fast prefetch + seeded placeholder cache entries for all detected hotspots.
  - Bounded robust prewarm for empty hotspots (up to 10 seconds), then continue in background.
- Added robust hotspot fallback APIs in provider:
  - `ensureHotspotProductsReady(...)`
  - `runRobustHotspotAnalysis(...)`
  - Per-hotspot in-flight dedupe to prevent duplicate backend calls.
  - Robust image-type fallback path: `inspiration -> product`.
- Moved click-time waiting off normal marker taps:
  - Auto hotspots use prefetched cache first.
  - Loader appears only when hotspot is still empty and fallback must run.
  - Manual `tap_*` hotspots continue on-demand full analysis.
- Fixed marker alignment:
  - Marker placement now uses rendered image bounds (`displaySize` + `displayOffset`) from `InteractiveImageWidget`.
  - Added testable mapping function for deterministic validation.
- Product cleanup/ranking:
  - Parse and support both numeric `price` and `price_str`.
  - Normalize retailer-prefixed titles.
  - Rank products by hotspot relevance (token matching across title/description/category).
- Price UI cleanup:
  - Show `Price unavailable` when no valid price exists (instead of fake `$0.00`).

## Key Files Updated

- `lib/providers/project_provider.dart`
- `lib/screens/choose_products_screen.dart`
- `lib/screens/dream_space_screen.dart`
- `lib/widgets/interactive_image_widget.dart`
- `lib/models/shop_product.dart`
- `lib/widgets/shop_product_card.dart`

## Test Coverage Added/Updated

- `test/providers/project_provider_furniture_prefetch_test.dart`
  - Empty-hotspot robust fallback trigger.
  - In-flight dedupe for repeated fallback requests.
  - Bounded generation wait behavior.
- `test/screens/choose_products_screen_test.dart`
  - Empty prefetched hotspot fallback behavior.
  - Empty-success UI when fallback still returns no products.
  - `Price unavailable` rendering.
  - Relevance ranking + title normalization.
- `test/screens/dream_to_choose_flow_smoke_test.dart`
  - Warm-path auto hotspot opens products immediately.
  - Empty hotspot path shows fallback loading then products.
- `test/screens/dream_space_marker_alignment_test.dart`
  - Marker mapping uses rendered-image bounds, not full container bounds.
- `test/models/shop_product_model_test.dart`
  - `price_str` parsing and `displayPrice` behavior.

## Verification Run

- Passed targeted tests:
  - `flutter test test/providers/project_provider_furniture_prefetch_test.dart test/screens/choose_products_screen_test.dart test/screens/dream_to_choose_flow_smoke_test.dart test/screens/dream_space_marker_alignment_test.dart test/models/shop_product_model_test.dart`
- Passed full suite:
  - `flutter test`
- Sanity checks:
  - `flutter analyze lib/screens/dream_space_screen.dart test/screens/choose_products_screen_test.dart` -> no issues.
