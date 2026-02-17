"""
Plugin Screenshot Tool - Win32 Window Capture

Captures ONLY the plugin window (not full screen) with optional grid overlay.

Usage:
    from frontend.screenshot import PluginScreenshot

    screenshot = PluginScreenshot()
    img = screenshot.capture("DryWetMixerDemo", grid=True)
    img.save("output.png")

Features:
- Find window by title (e.g., "DryWetMixerDemo")
- Capture only that window (not full screen)
- Optional 10px grid overlay for measurement
- Save at true 1:1 pixel size
"""

import ctypes
import ctypes.wintypes
import psutil
from PIL import Image, ImageDraw, ImageGrab
from typing import Optional, Tuple, List


class PluginScreenshot:
    """Capture plugin window with measurement grid."""

    # Win32 API structures
    class RECT(ctypes.Structure):
        _fields_ = [
            ("left", ctypes.c_long),
            ("top", ctypes.c_long),
            ("right", ctypes.c_long),
            ("bottom", ctypes.c_long),
        ]

        @property
        def width(self):
            return self.right - self.left

        @property
        def height(self):
            return self.bottom - self.top

    def __init__(self):
        """Initialize Win32 APIs."""
        # Enable DPI awareness FIRST (critical for correct coordinates on scaled displays)
        # This makes GetWindowRect return actual pixel coordinates
        try:
            ctypes.windll.shcore.SetProcessDpiAwareness(2)  # PROCESS_PER_MONITOR_DPI_AWARE
        except (AttributeError, OSError):
            pass  # Fallback for older Windows versions

        self.user32 = ctypes.windll.user32

        # Define function signatures
        self.user32.FindWindowW.restype = ctypes.wintypes.HWND
        self.user32.FindWindowW.argtypes = [
            ctypes.wintypes.LPCWSTR,
            ctypes.wintypes.LPCWSTR
        ]

        self.user32.GetWindowRect.restype = ctypes.wintypes.BOOL
        self.user32.GetWindowRect.argtypes = [
            ctypes.wintypes.HWND,
            ctypes.POINTER(self.RECT)
        ]

        self.user32.GetWindowTextLengthW.restype = ctypes.c_int
        self.user32.GetWindowTextLengthW.argtypes = [ctypes.wintypes.HWND]

        self.user32.GetWindowTextW.restype = ctypes.c_int
        self.user32.GetWindowTextW.argtypes = [
            ctypes.wintypes.HWND,
            ctypes.wintypes.LPWSTR,
            ctypes.c_int
        ]

        self.user32.IsWindowVisible.restype = ctypes.wintypes.BOOL
        self.user32.IsWindowVisible.argtypes = [ctypes.wintypes.HWND]

        self.user32.EnumWindows.restype = ctypes.wintypes.BOOL
        # EnumWindows callback is set up when called

        self.user32.ShowWindow.restype = ctypes.wintypes.BOOL
        self.user32.ShowWindow.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]

        self.user32.SetForegroundWindow.restype = ctypes.wintypes.BOOL
        self.user32.SetForegroundWindow.argtypes = [ctypes.wintypes.HWND]

        self.user32.GetWindowThreadProcessId.restype = ctypes.c_ulong
        self.user32.GetWindowThreadProcessId.argtypes = [
            ctypes.wintypes.HWND,
            ctypes.POINTER(ctypes.c_ulong)
        ]

        self.user32.GetWindowLongPtrW.restype = ctypes.c_ulonglong
        self.user32.GetWindowLongPtrW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]

        # GWL_EXSTYLE = -20
        # WS_EX_APPWINDOW = 0x00040000

        # For checking window style (has title bar)
        self.user32.GetWindowLongW.restype = ctypes.c_ulong
        self.user32.GetWindowLongW.argtypes = [ctypes.wintypes.HWND, ctypes.c_int]

        # WS_CAPTION = 0x00C00000  # Title bar
        # WS_THICKFRAME = 0x00040000  # Resizable border

    def _get_window_pid(self, hwnd: int) -> int:
        """
        Get process ID for a window.

        Args:
            hwnd: Window handle

        Returns:
            Process ID
        """
        pid = ctypes.c_ulong()
        self.user32.GetWindowThreadProcessId(hwnd, ctypes.byref(pid))
        return pid.value

    def _get_process_name(self, pid: int) -> str:
        """
        Get process name from process ID.

        Args:
            pid: Process ID

        Returns:
            Process executable name
        """
        try:
            proc = psutil.Process(pid)
            return proc.name()
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            return "unknown"

    def find_all_matches(self, title: str) -> List[Tuple[str, int, str]]:
        """
        Find all windows matching title with their process names.

        Args:
            title: Window title to search for (partial match)

        Returns:
            List of (window_title, hwnd, process_name) tuples
        """
        matches = []

        def enum_proc(hwnd, lParam):
            if self.user32.IsWindowVisible(hwnd):
                length = self.user32.GetWindowTextLengthW(hwnd) + 1
                if length > 1:
                    buffer = ctypes.create_unicode_buffer(length)
                    self.user32.GetWindowTextW(hwnd, buffer, length)
                    window_title = buffer.value

                    if title.lower() in window_title.lower():
                        pid = self._get_window_pid(hwnd)
                        proc_name = self._get_process_name(pid)
                        matches.append((window_title, hwnd, proc_name))
            return 1

        callback_type = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL,
            ctypes.wintypes.HWND,
            ctypes.wintypes.LPARAM
        )
        callback = callback_type(enum_proc)
        self.user32.EnumWindows(callback, 0)

        return matches

    def _find_window(self, title: str, process_name: str = None) -> int:
        """
        Find window by title with optional process name verification.
        Prefers windows WITH TITLE BARS (WS_CAPTION) - main windows only.

        Args:
            title: Window title (e.g., "DryWetMixerDemo")
            process_name: Optional process executable name (e.g., "DryWetMixerDemo.exe")

        Returns:
            Window handle (HWND)

        Raises:
            RuntimeError: If window not found or multiple matches found
        """
        WS_CAPTION = 0x00C00000  # Has title bar

        # Collect all matching windows with their styles
        matches = []

        def enum_windows_proc(hwnd, lParam):
            try:
                if self.user32.IsWindowVisible(hwnd):
                    length = self.user32.GetWindowTextLengthW(hwnd) + 1
                    if length > 1:
                        buffer = ctypes.create_unicode_buffer(length)
                        self.user32.GetWindowTextW(hwnd, buffer, length)
                        window_title = buffer.value

                        if title.lower() in window_title.lower():
                            # Get window style to check for title bar
                            style = self.user32.GetWindowLongW(hwnd, -16)  # GWL_STYLE
                            has_title_bar = bool(style & WS_CAPTION)

                            rect = self.RECT()
                            self.user32.GetWindowRect(hwnd, ctypes.byref(rect))
                            area = rect.width * rect.height

                            if process_name is None:
                                matches.append((hwnd, window_title, None, area, has_title_bar))
                            else:
                                pid = self._get_window_pid(hwnd)
                                actual_proc_name = self._get_process_name(pid)
                                if actual_proc_name == process_name or actual_proc_name.lower() == process_name.lower():
                                    matches.append((hwnd, window_title, actual_proc_name, area, has_title_bar))
            except Exception as e:
                # Don't let exceptions in enumeration break the whole process
                pass
            return 1

        callback_type = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL,
            ctypes.wintypes.HWND,
            ctypes.wintypes.LPARAM
        )
        callback = callback_type(enum_windows_proc)
        self.user32.EnumWindows(callback, 0)

        if len(matches) == 0:
            raise RuntimeError(
                f"Window '{title}' not found. "
                f"Use list_windows() to see available windows."
            )

        # Separate windows with and without title bars
        with_title_bar = [m for m in matches if m[4]]
        without_title_bar = [m for m in matches if not m[4]]

        # Prefer windows WITH title bars
        if with_title_bar:
            matches = with_title_bar
            selection_criteria = "with title bar"
        else:
            matches = without_title_bar
            selection_criteria = "without title bar (fallback)"

        # Sort by area (largest first) within selected group
        matches.sort(key=lambda x: x[3], reverse=True)

        if len(matches) > 1:
            print(f"Multiple windows found matching '{title}' ({selection_criteria}):")
            for i, (hwnd, window_title, proc_name, area, has_title) in enumerate(matches):
                title_info = " [TITLE BAR]" if has_title else " [NO TITLE BAR]"
                proc_info = f" ({proc_name})" if proc_name else ""
                print(f"  [{i}] {window_title}{proc_info}{title_info} - {area} px²")

        best_hwnd = matches[0][0]
        best_title = matches[0][1]
        best_proc = matches[0][2]
        has_title = matches[0][4]

        print(f"Selected: {best_title} ({best_proc}) - Has title bar: {has_title}")

        return best_hwnd

    def _get_window_rect(self, hwnd: int) -> RECT:
        """
        Get window rectangle.

        Args:
            hwnd: Window handle

        Returns:
            RECT with window dimensions
        """
        rect = self.RECT()
        if not self.user32.GetWindowRect(hwnd, ctypes.byref(rect)):
            raise RuntimeError("Failed to get window rectangle")
        return rect

    def _capture_window(self, hwnd: int) -> Image.Image:
        """
        Capture window content to PIL Image.

        Args:
            hwnd: Window handle

        Returns:
            PIL Image of window
        """
        rect = self._get_window_rect(hwnd)

        # Bring window to front for clean capture
        self.user32.ShowWindow(hwnd, 9)  # SW_RESTORE
        self.user32.SetForegroundWindow(hwnd)

        # Small delay to let window repaint
        import time
        time.sleep(0.1)

        # Use PIL's ImageGrab with bounding box
        # bbox is (left, top, right, bottom)
        img = ImageGrab.grab(bbox=(rect.left, rect.top, rect.right, rect.bottom))

        return img

    def _add_grid(self, img: Image.Image, spacing: int = 10,
                  color: Tuple[int, int, int, int] = (100, 100, 100, 128)) -> Image.Image:
        """
        Add measurement grid overlay to image.

        Args:
            img: Input image
            spacing: Grid spacing in pixels
            color: Grid color (R, G, B, A)

        Returns:
            Image with grid overlay
        """
        img_copy = img.copy()
        draw = ImageDraw.Draw(img_copy, 'RGBA')

        width, height = img.size

        # Create semi-transparent color
        r, g, b, a = color
        grid_color = (r, g, b, a)

        # Vertical lines
        for x in range(0, width, spacing):
            draw.line([(x, 0), (x, height)], fill=grid_color)

        # Horizontal lines
        for y in range(0, height, spacing):
            draw.line([(0, y), (width, y)], fill=grid_color)

        # Add border
        draw.rectangle([0, 0, width - 1, height - 1], outline=(255, 0, 0, 255))

        return img_copy

    def capture(self, window_title: str, process_name: str = None,
                grid: bool = False, grid_spacing: int = 10) -> Image.Image:
        """
        Capture plugin window.

        Args:
            window_title: Window title (e.g., "DryWetMixerDemo")
            process_name: Optional process executable name (e.g., "DryWetMixerDemo.exe")
            grid: Whether to add measurement grid overlay
            grid_spacing: Grid spacing in pixels

        Returns:
            PIL Image of window

        Raises:
            RuntimeError: If window not found or capture fails
        """
        hwnd = self._find_window(window_title, process_name)
        rect = self._get_window_rect(hwnd)

        # Get process info for logging
        pid = self._get_window_pid(hwnd)
        proc_name = self._get_process_name(pid)

        print(f"Found window: {window_title}")
        print(f"  Process: {proc_name} (PID: {pid})")
        print(f"  Position: ({rect.left}, {rect.top})")
        print(f"  Size: {rect.width} x {rect.height}")

        img = self._capture_window(hwnd)

        if grid:
            img = self._add_grid(img, spacing=grid_spacing)
            print(f"  Added {grid_spacing}px grid overlay")

        return img

    def capture_and_save(self, window_title: str, output_path: str,
                        process_name: str = None, grid: bool = False,
                        grid_spacing: int = 10, quality: int = 95) -> str:
        """
        Capture window and save as JPG (smaller file size).

        Args:
            window_title: Window title to capture
            output_path: Save path (will use .jpg extension)
            process_name: Optional process executable name for verification
            grid: Add grid overlay (default: False)
            grid_spacing: Grid spacing in pixels
            quality: JPEG quality (1-100, default 95)

        Returns:
            Path to saved file
        """
        img = self.capture(window_title, process_name=process_name, grid=grid, grid_spacing=grid_spacing)

        # Ensure .jpg extension
        if not output_path.lower().endswith('.jpg') and not output_path.lower().endswith('.jpeg'):
            output_path = output_path.rsplit('.', 1)[0] + '.jpg'

        img.save(output_path, 'JPEG', quality=quality)
        print(f"Saved to: {output_path}")
        return output_path

    def measure_distance(self, p1: Tuple[int, int],
                        p2: Tuple[int, int]) -> int:
        """
        Measure pixel distance between two points.

        Args:
            p1: First point (x, y)
            p2: Second point (x, y)

        Returns:
            Distance in pixels
        """
        return int(((p2[0] - p1[0])**2 + (p2[1] - p1[1])**2)**0.5)

    def list_windows(self, filter_str: str = "") -> list:
        """
        List all visible windows with process names (for debugging).

        Args:
            filter_str: Optional filter substring

        Returns:
            List of (title, handle, process_name) tuples
        """
        windows = []

        def enum_proc(hwnd, lParam):
            if self.user32.IsWindowVisible(hwnd):
                length = self.user32.GetWindowTextLengthW(hwnd) + 1
                if length > 1:
                    buffer = ctypes.create_unicode_buffer(length)
                    self.user32.GetWindowTextW(hwnd, buffer, length)
                    title = buffer.value
                    if not filter_str or filter_str.lower() in title.lower():
                        pid = self._get_window_pid(hwnd)
                        proc_name = self._get_process_name(pid)
                        windows.append((title, hwnd, proc_name))
            return 1

        callback_type = ctypes.WINFUNCTYPE(
            ctypes.wintypes.BOOL,
            ctypes.wintypes.HWND,
            ctypes.wintypes.LPARAM
        )
        callback = callback_type(enum_proc)
        self.user32.EnumWindows(callback, 0)

        return windows


# Convenience function for quick capture
def capture_plugin(window_title: str, output_path: str = None,
                   process_name: str = None, grid: bool = False,
                   quality: int = 95) -> Image.Image:
    """
    Quick capture function (saves as JPG).

    Args:
        window_title: Window title to capture
        output_path: Optional save path (defaults to JPG)
        process_name: Optional process executable name for verification
        grid: Add grid overlay
        quality: JPEG quality (1-100, default 95)

    Returns:
        PIL Image
    """
    screenshot = PluginScreenshot()
    img = screenshot.capture(window_title, process_name=process_name, grid=grid)

    if output_path:
        # Ensure JPG extension
        if not output_path.lower().endswith('.jpg') and not output_path.lower().endswith('.jpeg'):
            output_path = output_path.rsplit('.', 1)[0] + '.jpg'
        img.save(output_path, 'JPEG', quality=quality)
        print(f"Saved to: {output_path}")

    return img


if __name__ == "__main__":
    import sys
    import argparse

    # Set UTF-8 encoding for output
    if sys.platform == "win32":
        import io
        sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8', errors='replace')
        sys.stderr = io.TextIOWrapper(sys.stderr.buffer, encoding='utf-8', errors='replace')

    parser = argparse.ArgumentParser(
        description='Capture plugin window as JPG (DPI-aware)',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python screenshot.py "HeathAudioPluginTemplate"
  python screenshot.py "MyPlugin" output.jpg
  python screenshot.py "MyPlugin" output.jpg --grid
  python screenshot.py "MyPlugin" output.jpg --quality 75
  python screenshot.py --list
'''
    )
    parser.add_argument('window_title', nargs='?', help='Window title to capture')
    parser.add_argument('output', nargs='?', help='Output JPG path (default: <window_title>.jpg)')
    parser.add_argument('--process', '-p', help='Process name for verification (e.g., Plugin.exe)')
    parser.add_argument('--quality', '-q', type=int, default=85, help='JPEG quality 1-100 (default: 85)')
    parser.add_argument('--grid', '-g', action='store_true', help='Add measurement grid overlay')
    parser.add_argument('--list', '-l', action='store_true', help='List available windows')

    args = parser.parse_args()

    screenshot = PluginScreenshot()

    # List mode
    if args.list:
        print("=== Available Windows ===")
        windows = screenshot.list_windows()
        for title, hwnd, proc_name in windows[:50]:
            safe_title = title.encode('ascii', 'replace').decode('ascii')
            print(f"  {safe_title} ({proc_name})")
        sys.exit(0)

    # Require window title for capture
    if not args.window_title:
        parser.print_help()
        sys.exit(1)

    # Determine output path
    if args.output:
        output_path = args.output
    else:
        # Default: window_title.jpg
        safe_name = args.window_title.replace(' ', '_').replace('/', '_').replace('\\', '_')
        output_path = f"{safe_name}.jpg"

    try:
        output_path = screenshot.capture_and_save(
            args.window_title,
            output_path,
            process_name=args.process,
            grid=args.grid,
            quality=args.quality
        )
        print(f"\nCaptured: {output_path}")
    except RuntimeError as e:
        print(f"\nError: {e}")
        print("\nTip: Use --list to see available windows")
        sys.exit(1)
