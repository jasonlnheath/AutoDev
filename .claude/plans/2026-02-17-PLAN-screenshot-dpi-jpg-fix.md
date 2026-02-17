# Screenshot Tool Enhancement - DPI Fix & JPG Optimization

## Context

**Problem:** The screenshot tool partially finds the plugin window but captures mostly the desktop instead of the actual plugin content. This is a **DPI scaling mismatch** issue.

**Root Cause:** Monitor is scaled at 185%. Win32 `GetWindowRect()` returns virtualized (scaled) coordinates, but PIL `ImageGrab` expects unscaled pixel coordinates. This causes the capture region to be offset/wrong size.

**Goal:** Create a reliable, fast screenshot tool that:
1. Correctly captures plugin windows regardless of DPI scaling
2. Outputs JPG format for token efficiency
3. Works as a simple CLI command

---

## Solution Architecture

### DPI Awareness Fix (Critical)

The process needs to be **DPI-aware** so Win32 coordinates match actual pixels.

```python
# Set DPI awareness at process start
import ctypes
ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
```

This makes `GetWindowRect()` return actual pixel coordinates that match what `ImageGrab` expects.

---

## Implementation Plan

### Step 1: Add DPI Awareness

**File:** `frontend/screenshot.py`

Add DPI awareness initialization at class initialization:

```python
def __init__(self):
    # Enable DPI awareness FIRST (before any window operations)
    try:
        ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
    except Exception:
        pass  # Fallback for older Windows versions

    # ... rest of existing init
```

### Step 2: Optimize for JPG CLI Workflow

Add a new CLI entry point that defaults to JPG:

```python
def quick_capture(window_title: str, output_path: str = None,
                  quality: int = 85, grid: bool = False) -> str:
    """
    Fast capture optimized for JPG output.

    Args:
        window_title: Window title to find
        output_path: Output path (defaults to <window_title>.jpg)
        quality: JPEG quality 1-100 (default 85 - good compression/quality balance)
        grid: Add measurement grid (default: False)

    Returns:
        Path to saved JPG file
    """
```

### Step 3: Update __main__ Block

Make the CLI interface cleaner:

```python
if __name__ == "__main__":
    # Usage: python screenshot.py "WindowTitle" [output.jpg]
    # Defaults to JPG output at quality 85
```

### Step 4: Remove Gridlines from Default Workflow

Grid should be opt-in (slows down capture, increases file size).

---

## Files to Modify

| File | Changes |
|------|---------|
| `frontend/screenshot.py` | Add DPI awareness, optimize CLI, default to JPG |

---

## CLI Usage (Final)

```bash
# Basic capture (outputs to WindowTitle.jpg)
python frontend/screenshot.py "HeathAudioPluginTemplate"

# Specify output path
python frontend/screenshot.py "HeathAudioPluginTemplate" output.jpg

# With grid overlay
python frontend/screenshot.py "HeathAudioPluginTemplate" output.jpg --grid

# Adjust quality (lower = smaller file)
python frontend/screenshot.py "HeathAudioPluginTemplate" output.jpg --quality 75
```

---

## Verification

1. Start a standalone plugin (e.g., HeathAudioPluginTemplate.exe)
2. Run: `python frontend/screenshot.py "HeathAudioPluginTemplate"`
3. Check output JPG shows **only** the plugin window content
4. Verify correct dimensions (no desktop bleeding in)
5. Check file size is reasonable (should be <100KB for typical plugin at quality 85)

---

## Expected Outcome

- Plugin window captured correctly regardless of monitor scaling
- JPG output by default (smaller files for token efficiency)
- Simple CLI: just window title, everything else has sensible defaults
- Quality 85 provides good balance of file size vs clarity
