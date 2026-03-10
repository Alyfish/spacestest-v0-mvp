/// Feature flags for marker accuracy improvements.
/// All default to `false` (off) for safe incremental rollout.

/// When true, renders the generated image with BoxFit.contain instead of
/// BoxFit.cover, and clamps markers to the imageRect rather than the
/// container bounds.
const bool kDreamSpaceUseContainFit = false;

/// When true and a bbox is present on the hotspot, use the bbox center
/// (bboxX + bboxW/2, bboxY + bboxH/2) for marker placement.
const bool kUseBboxCenterIfPresent = true;

/// When true and correctedClickX/Y are present on the hotspot, use them
/// for marker placement instead of the original x/y.
const bool kUseCorrectedClickIfPresent = true;

/// Debug-only: draw imageRect border and marker dot outlines on the
/// Dream Space screen.
const bool kShowMarkerDebugOverlay = false;
