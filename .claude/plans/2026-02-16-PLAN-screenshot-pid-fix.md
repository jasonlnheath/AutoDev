# Fix Screenshot Tool - Process ID Matching

## Context

The screenshot tool is capturing the WRONG window. When capturing "HeathAudioPluginTemplate", it returned a window showing "popup eq- currer" instead of the actual plugin window. This happens because `FindWindow()` may match multiple windows with similar titles.

**Root Cause:** Partial title matching without verifying the window belongs to the expected process.

## Solution

Add process ID verification to ensure we capture the window belonging to the specific executable we launched.

## Implementation

### 1. Add psutil dependency
```bash
pip install psutil
```

### 2. Modify `PluginScreenshot._find_window()` to:
- Accept optional `process_name` parameter
- Match windows by title AND process ID
- Return multiple matches for user selection if ambiguous
- Add `_find_window_by_process()` method for exact matching

### 3. Add new methods:
- `_find_window_by_process(title, process_name)` - Main method with PID verification
- `get_window_process_name(hwnd)` - Get executable name from window handle
- `find_all_matches(title)` - Return all matching windows with their process names

### 4. Update `capture()` method signature:
```python
def capture(self, window_title: str, process_name: str = None, grid: bool = False)
```

## Files to Modify

- `C:\dev\AutoDev\frontend\screenshot.py` - Add PID verification logic

## Verification

1. Start HeathAudioPluginTemplate standalone
2. Use screenshot tool with `process_name="HeathAudioPluginTemplate.exe"`
3. Verify correct window is captured (should show header bar, meters, not "popup eq")
4. Test with multiple windows open to ensure correct selection

## Expected Outcome

Screenshot captures the ACTUAL plugin window, not random windows with similar titles.
