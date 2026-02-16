# How the Code Works

## Dream Space Cover Mode & Hotspot System

### Image Display Pipeline

`InteractiveImageWidget` (`lib/widgets/interactive_image_widget.dart`) handles rendering a room image with interactive hotspot markers. It uses Flutter's `BoxFit` system (defaulting to `BoxFit.cover`) to fill the available space.

**Key functions:**

- `calculateImageDisplayBounds()` — Computes the rendered image size and offset within the container for any `BoxFit` mode. Under `cover`, the image overflows the container (negative offsets); under `contain`, it letterboxes.

- `mapHotspotToRenderedImageTopLeft()` — Converts a hotspot's normalized `(0-1)` coordinates to screen-space pixel positions for marker placement. When `visibleSize` is provided (cover mode), the marker center is clamped to the visible container edge minus `kClampInset` so markers remain partially visible even when the hotspot falls in a cropped region.

### kClampInset constant

`kClampInset` (12.0 logical pixels) is the minimum distance from the container edge that a clamped marker center can reach. It is defined as a top-level constant in `interactive_image_widget.dart` and referenced by both the implementation and tests, so changes to the inset value propagate automatically without hardcoded magic numbers.

### Hotspot Tap Correctness

In `dream_space_screen.dart`, the `onTap` closure in the hotspot marker captures the original `ProductHotspot` object directly from the `.map()` iterator. The clamped screen position is only used for `Positioned(left:, top:)` layout — it is never reverse-mapped to determine which hotspot was tapped. This means marker clamping has no effect on tap identity.

### Full-Screen Layout Constraints

The dream space screen uses `Scaffold > SafeArea(bottom: false) > Column > Expanded > PageView > Stack(StackFit.expand)`. The `InteractiveImageWidget` uses `SizedBox(width/height: double.infinity)` inside `ClipRect`. No `AspectRatio` or `Padding` surrounds the image, so it fills the full available area. Both original and generated image pages use identical widget paths.

---

## Create Flow Screen — Async Pipeline

`CreateFlowScreen` (`lib/screens/create_flow_screen.dart`) manages the full redesign flow as a state machine using `CreateFlowStep` enum values.

### Precache Strategy

Before transitioning to `DreamSpaceScreen`, the generated image bytes (already in memory from the API response) are pre-decoded via `precacheImage(MemoryImage(...))` with a **500ms timeout**. This is sufficient for codec decoding of an in-memory image. If decoding takes longer (very large image), we proceed anyway — `gaplessPlayback: true` on the `Image` widget prevents a blank flash.

### Mounted Guards

All async work callbacks in the analyzing screens use `if (!mounted) return;` guards after every `await` before any subsequent `context` usage. This prevents `use_build_context_synchronously` lint violations and avoids accessing a stale `BuildContext` if the user navigates away during async work. Specific guard locations:

- **Analyzing (product pipeline):** After `ensurePreferredStoresSynced` completes, before `ensureRecommendationsLoaded(context)`. Inside the polling loop, before `refreshProductSuggestionsSnapshot(context)` / `preloadTrendingProducts(context)`.
- **Improvements analyzing:** After deferred saves complete (`Future.wait(safeFutures)`), before `ensureRecommendationsLoaded(context)`.

### Analyzing Phase Summary

1. **Phase 1** — Sync preferred stores (5s timeout)
2. **Phase 2** — Ensure recommendations loaded (15s timeout, likely already done)
3. **Phase 3** — Kick off search job (fire-and-forget)
4. **Phase 4** — Poll for image-backed product suggestions (45s max, 2s interval)
5. **Phase 5** — Pre-cache top 8 product images (5s timeout)

---

## Test Coverage

`test/widgets/interactive_image_widget_fit_test.dart` — 8 tests covering:

- `calculateImageDisplayBounds`: contain (letterbox), cover (crop), portrait-in-landscape, landscape-in-portrait
- `mapHotspotToRenderedImageTopLeft`: round-trip accuracy, left-edge clamping, right-edge clamping, unclamped passthrough
- Clamp tests use the `kClampInset` constant directly rather than hardcoded values
