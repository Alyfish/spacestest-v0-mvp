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

---

## RevenueCat + Mock Billing Runtime Notes (Local iOS)

- Flutter reads RevenueCat keys from compile-time `--dart-define` values (`RC_API_KEY` or `REVENUECAT_PUBLIC_KEY`), not directly from `backend/.env`.
- `scripts/run_ios_device.sh` can load `backend/.env` for local convenience and forward the **public** RevenueCat key into Flutter.
- `DEV_IAP_ENABLED=true` (Flutter dart-define) enables mock billing mode (`MockBillingService`) for local E2E credits testing via `/dev/grant-*` endpoints.
- RevenueCat SDK calls are guarded so missing configuration no longer crashes post-login subscription sync.
- RevenueCat secret keys remain backend-only and must never be passed into Flutter.

---

## Production Readiness Fixes (Pre-Launch)

### P0-A: Integration/Complete Revamp Prompt Parity with Iterative

**Problem:** `_create_integration_prompt` in `gemini_client.py` manually extracted only 3 of 7 style fields and used a simple `color_scheme` list. It never called `_build_color_direction()` (full 60-30-10 palette with hex codes, descriptions, element assignments) or `_build_style_direction()` (all 7 fields: style_name, overview, materials, furniture_characteristics, patterns_textures, decor_accessories, anchor_pieces). This made Complete Revamp produce generic results compared to Iterative.

**Fix:**
- `gemini_client.py:1373` — Added `color_analysis: Dict[str, Any] = None` parameter. Replaced manual color/style extraction with calls to `_build_color_direction(color_analysis, color_scheme)` and `_build_style_direction(design_style)`. Added a `### COLOR & STYLE DESIGN DIRECTION` section to the prompt template using the same pattern as the iterative prompt.
- `supabase_data_manager.py:3233-3242` — Passes `color_analysis=context.color_analysis` to the integration prompt caller.

Both prompts now use identical design intelligence helpers.

### P0-B: Trending Products End-to-End Wiring

**Problem:** The backend endpoint `POST /projects/{id}/selected-trending-products`, the data manager method `set_selected_trending_products`, and the model `SelectedTrendingProduct` all existed — but the Flutter app never called them. When `LikeTheseScreen` returned selected product objects, `ImprovementsScreen` stored only display text; the rich product data (`{url, title, store, image_url}`) was discarded.

**Fix (frontend data capture):**
- `improvements_screen.dart` — Added `_selectedProductItems` map to store raw product objects from `LikeTheseScreen` keyed by actionId. In `_openLikeThese`, the `selectedItemsRaw` list is parsed into `productItems` and stored. In `_handleContinue`, all accumulated product items are collected with category/url/title/image_url/store/price_str fields and passed to the `onImprove` callback.

**Fix (frontend API wiring):**
- `api_constants.dart` — `selectedTrendingProducts` endpoint constant.
- `api_service.dart` — `setSelectedTrendingProducts(projectId, authToken, products)` POST method.
- `project_provider.dart` — `saveSelectedTrendingProducts(context, items)` wrapping the API call.

**Fix (deferred save):**
- `create_flow_screen.dart` — `_pendingTrendingItems` field captures trending items from the `onImprove` callback. In the `improvementsAnalyzing` deferred saves block, a `trending_products` save operation calls `provider.saveSelectedTrendingProducts()` with first-pass + retry pattern. `_pendingTrendingItems` is reset to `null` after saves complete.

**Fix (backend prompt consumption):**
- `supabase_data_manager.py:3219-3231` — Trending products are the highest-priority product source for the integration prompt. Falls back to `selected_products`, then `selected_recommendations`.
- `supabase_data_manager.py:3279-3280` — Trending product images used as Gemini visual reference when no other product images are available.
- `supabase_data_manager.py:3211` — Trending products passed to iterative prompt via `trending_products=context.selected_trending_products or []`.

**Fix (validation gate):**
- `models.py:702,714` — `has_selected_trending` added to `is_ready_for_inspiration_redesign()` so projects with only trending products pass the readiness check.

### P0-C: Iterative Prompt Trending Products Parameter

**Problem:** `_create_iterative_prompt` had a `trending_products` parameter that was formatted into the prompt (lines 1585-1588), but the caller at `supabase_data_manager.py:3208` never passed it.

**Fix:** `supabase_data_manager.py:3211` — Passes `trending_products=context.selected_trending_products or []` to the iterative prompt.

### P1-A: Color/Style Save Deferred to Analyzing Phase

**Problem:** `ColorPaletteSelectionScreen` and `ChooseStyleScreen` called `saveColorPalette()`/`saveDesignStyle()` with blocking `background: false`, showing a spinner for 1-3 seconds on the Continue button. The blocking save was an intentional race condition fix (documented in commit `68d7c71`): fire-and-forget saves created a race between UI selection and backend persistence. Simply switching to `background: true` would re-introduce this race.

**Fix — defer actual palette data, not the save decision:**
- `improvements_screen.dart` — `ColorPaletteSelectionScreen._handleContinue` is now synchronous. It returns palette data (`{id, name, hexColors, letAiDecide}`) via `Navigator.pop()` without calling the backend. No spinner. `ChooseStyleScreen._handleContinue` does the same, returning `{id, name, letAiDecide}`. `ImprovementsScreen` stores this data in `_pendingColorPalette` and `_pendingStyleData` fields.
- `improvements_screen.dart` — `onImprove` callback signature changed from `(List<String>, bool needsColorSave, bool needsStyleSave, List<Map>)` to `(List<String>, Map? pendingColorPalette, Map? pendingStyleData, List<Map>)`. When no palette/style was selected and none previously existed, defaults to `{id: 'ai_decide', ...}`.
- `create_flow_screen.dart` — `_pendingColorPalette` and `_pendingStyleData` replace the old `_pendingNeedsColorSave`/`_pendingNeedsStyleSave` booleans. The deferred save block in `improvementsAnalyzing` uses the actual palette/style data maps to call `saveColorPalette()`/`saveDesignStyle()` behind the analyzing animation with first-pass + retry. This preserves the race fix (save completes before generation starts) while eliminating the user-facing spinner.

### P0-D: Paywall Context Fix for Non-Home Tabs

**Problem:** `main_navigation_screen.dart:71` — `ensureCanGenerate(source: ...)` was missing `context: context`. When triggered from the center FAB on non-Home tabs (e.g., Profile), it fell back to `_lastContext` which could be a disposed HomeScreen context, causing the paywall to silently fail.

**Fix:** `main_navigation_screen.dart:71` — Added `context: context` so it uses the live `MainNavigationScreen` context.

### P1-B: Login Sync + Release Logging Fixes

**Problem 1:** `login_screen.dart:131` — `_syncSubscriptionIdentity` had `catch (_) {}` which silently swallowed RevenueCat/subscription sync errors after login.

**Fix:** Replaced with `catch (e) { AppLogger.error('Subscription identity sync failed: $e'); }`. Added `import '../../utils/logger.dart'`.

**Problem 2:** `subscription_provider.dart:166` — `ensureCanGenerate` error logging was guarded by `kDebugMode`, so errors were invisible in release builds.

**Fix:** Removed `if (kDebugMode)` guard so `AppLogger.error('ensureCanGenerate error: $e')` runs in all builds.

---

## Launch Hardening (Pre-App Store)

Security and production-readiness fixes applied before initial App Store submission.

### C1: RevenueCat Webhook Auth Guard
**File:** `backend/main.py` (lifespan startup)
**Fix:** Added startup warning that logs loudly if `REVENUECAT_WEBHOOK_AUTH` env var is empty when `RAILWAY_ENVIRONMENT` is set. Without this, the `/webhooks/revenuecat` endpoint accepts unauthenticated POSTs, allowing fake purchase events.

### C2: DEV_IAP_ENABLED Default
**File:** `backend/main.py:155`
**Fix:** Changed default from `not os.getenv("RAILWAY_ENVIRONMENT")` to `False`. Dev IAP endpoints (`/dev/grant-annual`, `/dev/grant-credits`) now require explicit opt-in via `DEV_IAP_ENABLED=true` env var, preventing accidental exposure if `RAILWAY_ENVIRONMENT` is unset.

### C3: App Transport Security Lockdown
**File:** `ios/Runner/Info.plist`
**Fix:** Removed `NSAllowsArbitraryLoads` and `NSAllowsLocalNetworking`. Added `NSExceptionDomains` with localhost-only exception for local dev. Production API URL is always HTTPS (set via `--dart-define=API_BASE_URL`).

### W1: Bare `except:` Blocks
**File:** `backend/data_manager.py` (link validation helper)
**Fix:** Changed 3 bare `except:` to `except Exception:` so `KeyboardInterrupt` and `SystemExit` propagate correctly.

### W2: Release-Mode Debug Logging
**File:** `lib/main.dart` (`_AuthGate`)
**Fix:** Gated `debugPrint('[AUTH_GATE] session=...')` behind `kDebugMode` so it doesn't appear in release logs.

### W3: Conditional Hot-Reload
**File:** `backend/main.py` (`__main__` block)
**Fix:** Changed `reload=True` to `reload=os.getenv("RAILWAY_ENVIRONMENT") is None` so hot-reload is only active in local dev. Production uses the Railway start command which doesn't hit `__main__`.

---

## Redesign Flow Fixes (Stale Cache, Color Nullification, Image Fallback, Black Bars)

Five bugs discovered during real-device iPhone testing after the previous deploy. All caused by state management gaps across project restarts and "Let AI Decide" code paths.

### Bug 1: Stale Cache Causes 400 Error on Restart (CRITICAL)

**Root cause:** `ProjectProvider.createProject()` (`project_provider.dart:~948`) did NOT reset flow state fields (`_productRecommendations`, `_selectedRecommendations`, `_markers`, `_recommendationsCompleter`, `_generateDesignFuture`, etc.) when creating a new project. When the user tapped Restart, these fields retained stale data from the OLD project. `ensureRecommendationsLoaded()` checked `_productRecommendations.isNotEmpty` → true (stale!) → returned immediately without fetching from backend. The backend saw the new project (empty context) and returned 400.

**Fix:** Call `clearProject()` at the start of `createProject()` before setting `_currentProject` from the API response. Also hardened `clearProject()` itself by adding 6 previously missing fields: `_generateDesignFuture`, `_generationRetrying`, `_rescueHotspotCompleters`, `_userTappedHotspots`, `_lastCompletedJobId`, `_dreamSpaceImageVersion`.

**Files:** `lib/providers/project_provider.dart:953` (call site), `lib/providers/project_provider.dart:1696-1735` (clearProject method)

### Bug 2: `let_ai_decide` Nullifies Color/Style Data (CRITICAL)

**Root cause (two destructive code paths):**

1. **Skip methods** — `skip_color_analysis()` (`supabase_data_manager.py:850`) set `color_analysis = None, color_scheme = None` alongside `color_analysis_skipped = True`. Same for `skip_style_analysis()` which set `style_analysis = None, design_style = None`. These methods are called both from the "Let AI Decide" fast path and from `_fetchProductRecommendationsWithToken` prerequisites.

2. **Prompt builder** — With `color_analysis=None` and `style_analysis=None`, `_build_color_direction()` and `_build_style_direction()` in `gemini_client.py` returned empty strings `""`. Gemini received ZERO color/style guidance → produced generic output.

**Fix (Part A — preserve existing data):** Removed `color_analysis: None`, `color_scheme: None` from `skip_color_analysis()` and `style_analysis: None`, `design_style: None` from `skip_style_analysis()`. These methods now only set the `_skipped` flag, which is all that's needed to unblock the marker recommendations pipeline (checked at `supabase_data_manager.py:527-528`). Any existing analysis data from prior runs or explicit user selection is preserved.

**Files:** `backend/supabase_data_manager.py:850-854, 863-866`

**Fix (Part B — prompt fallbacks for genuinely missing data):** For first-time flows where no analysis was ever run, `_build_color_direction()` now returns a professional-judgment fallback string (60-30-10 color rule guidance) instead of `""`. `_build_style_direction()` returns a cohesive-style fallback. This ensures Gemini always gets meaningful design direction.

**Files:** `backend/gemini_client.py:1769-1770, 1846-1847`

### Bug 3: "Original Not Available" in DreamSpace (IMPORTANT)

**Root cause:** `getProjectImageProvider()` (`project_provider.dart:1731-1736`) only checked `localProjectImage` (a `File?` reference). When the local file reference was lost (navigation, app lifecycle), the original image couldn't be shown — DreamSpace displayed "Original not available".

**Fix:** Added a URL fallback — if `localProjectImage` is null, try loading from `metadata['context']['base_image']` (the backend's stored image URL). The `metadata` map is populated by `Project.fromJson` which copies `context` into it at parse time.

**File:** `lib/providers/project_provider.dart:1734-1742`

### Bug 4: Black Bars / Image Cropping in DreamSpace (VISUAL)

**Root cause:** `_dreamSpaceFit()` (`dream_space_screen.dart:210-213`) returned `BoxFit.contain`, which preserves full image bounds but creates black letterbox bars when the image aspect ratio doesn't match the display area. The `Container(color: Colors.black)` background made these bars visible.

**Why safe to change:** `InteractiveImageWidget` already supports `BoxFit.cover` as its default. `mapHotspotToRenderedImageTopLeft()` clamps markers to the visible edge via its `visibleSize` parameter in cover mode. Tests exist for cover-mode clamping in `test/widgets/interactive_image_widget_fit_test.dart`.

**Fix:** Changed `_dreamSpaceFit()` from `BoxFit.contain` to `BoxFit.cover`. Updated test in `dream_to_choose_flow_smoke_test.dart` to assert `BoxFit.cover`.

**Files:** `lib/screens/dream_space_screen.dart:210-213`, `test/screens/dream_to_choose_flow_smoke_test.dart:75,99`

### clearProject() Complete Field Coverage

After this fix, `clearProject()` resets all project-scoped state. Fields intentionally NOT reset (session-scoped):
- `_uuid` — utility instance, not project-specific
- `_roomWidth/Height/Length` — room dimension inputs, reset by UI
- `_lastErrorTransient` — transient error flag
- `_imageUrlSetAt` — handled by `_updateGeneratedImageUrl(null)`

### Test Results
- Flutter: 80/80 pass
- Backend: 83/83 pass
