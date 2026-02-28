# Rotating Hint Pill - How It Works

## Overview

The `_RotatingHintPill` widget on the Dream Space screen cycles between two hint messages so users discover both swipe and tap interactions.

## Hints

| # | Icon | Message |
|---|------|---------|
| 1 | `swipe_outlined` | "Swipe to see original" |
| 2 | `touch_app_outlined` | "Tap any item to find products" |

## Flow

1. Widget mounts and starts a `Timer.periodic` with a **3.5s interval**.
2. Each tick increments `_index` (wrapping via modulo), triggering `setState`.
3. `AnimatedSwitcher` detects the new `ValueKey<int>(_index)` on the child container and crossfades between the old and new hint.
4. The transition combines a **fade** (`FadeTransition`) with a subtle **slide up** (`SlideTransition`, 15% vertical offset).
5. When the widget is disposed (e.g. user navigates away), `_timer.cancel()` runs to prevent leaks.

## Key Classes

- **`_HintConfig`** - Data class holding `IconData icon` and `String text`.
- **`_RotatingHintPill`** - `StatefulWidget` that owns the timer and renders the animated pill.

## Where It's Used

- **Page 0** (generated dream space) uses `const _RotatingHintPill()`.
- **Page 1** (original image) still uses the static `_buildSwipeHint('Swipe back to interact')`.
