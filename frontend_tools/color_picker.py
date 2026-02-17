"""
Color Picker Tool for GUI Development

Extract colors from mockup images to match design specifications.
Supports coordinate-based picking and region sampling.

Usage:
    from frontend_tools.color_picker import ColorPicker

    # Pick color at specific coordinates
    picker = ColorPicker("mockup.jpg")
    color = picker.pick(100, 50)
    print(color.to_hex())      # #1E1E1E
    print(color.to_css())      # rgb(30, 30, 30)

    # Sample region (average color)
    region = picker.sample_region(0, 0, 500, 50)  # top 50px of toolbar
    print(region.to_hex())

    # Generate CSS variables from sampled colors
    picker.generate_css_vars({
        'toolbar_bg': (0, 0, 500, 50),
        'panel_bg': (0, 50, 500, 300),
        'accent': (250, 25, 50, 50)
    })
"""

from PIL import Image
import numpy as np
from typing import Tuple, List, Dict, Optional
from dataclasses import dataclass
import json


@dataclass
class Color:
    """Represents a color with conversion utilities."""

    r: int
    g: int
    b: int

    def __post_init__(self):
        """Clamp values to valid RGB range."""
        self.r = max(0, min(255, self.r))
        self.g = max(0, min(255, self.g))
        self.b = max(0, min(255, self.b))

    @property
    def rgb(self) -> Tuple[int, int, int]:
        return (self.r, self.g, self.b)

    def to_hex(self) -> str:
        """Convert to hex color code (e.g., '#1E1E1E')."""
        return f"#{self.r:02X}{self.g:02X}{self.b:02X}"

    def to_css_rgb(self) -> str:
        """Convert to CSS rgb() format."""
        return f"rgb({self.r}, {self.g}, {self.b})"

    def to_css_rgba(self, alpha: float = 1.0) -> str:
        """Convert to CSS rgba() format."""
        return f"rgba({self.r}, {self.g}, {self.b}, {alpha:.2f})"

    def to_hsl(self) -> Tuple[float, float, float]:
        """Convert to HSL (hue, saturation, lightness)."""
        r, g, b = self.r / 255, self.g / 255, self.b / 255
        max_val = max(r, g, b)
        min_val = min(r, g, b)
        delta = max_val - min_val

        # Lightness
        l = (max_val + min_val) / 2

        # Saturation
        if delta == 0:
            s = 0
        else:
            s = delta / (2 - max_val - min_val) if l > 0.5 else delta / (max_val + min_val)

        # Hue
        if delta == 0:
            h = 0
        elif max_val == r:
            h = ((g - b) / delta) % 6
        elif max_val == g:
            h = (b - r) / delta + 2
        else:
            h = (r - g) / delta + 4
        h = round(h * 60)
        if h < 0:
            h += 360

        return (h, round(s * 100, 1), round(l * 100, 1))

    def to_css_hsl(self) -> str:
        """Convert to CSS hsl() format."""
        h, s, l = self.to_hsl()
        return f"hsl({h}, {s}%, {l}%)"

    def brightness(self) -> float:
        """Calculate perceived brightness (0-255)."""
        return (self.r * 299 + self.g * 587 + self.b * 114) / 1000

    def is_dark(self) -> bool:
        """Check if color is dark (brightness < 128)."""
        return self.brightness() < 128

    def contrast_color(self) -> 'Color':
        """Return black or white for best contrast."""
        return Color(255, 255, 255) if self.is_dark() else Color(0, 0, 0)

    def __str__(self) -> str:
        return self.to_hex()

    def __repr__(self) -> str:
        return f"Color({self.to_hex()}, rgb={self.rgb})"


class ColorPicker:
    """Extract colors from images for GUI design matching."""

    def __init__(self, image_path: str):
        """
        Initialize with an image path.

        Args:
            image_path: Path to the mockup/screenshot image
        """
        self.image_path = image_path
        self.image = Image.open(image_path)
        if self.image.mode != 'RGB':
            self.image = self.image.convert('RGB')
        self.array = np.array(self.image)

    @property
    def width(self) -> int:
        return self.image.width

    @property
    def height(self) -> int:
        return self.image.height

    def pick(self, x: int, y: int) -> Color:
        """
        Pick the color at a specific coordinate.

        Args:
            x: X coordinate (0-based, left=0)
            y: Y coordinate (0-based, top=0)

        Returns:
            Color object for the pixel at (x, y)
        """
        if 0 <= x < self.width and 0 <= y < self.height:
            r, g, b = self.array[y, x]
            return Color(int(r), int(g), int(b))
        raise ValueError(f"Coordinates ({x}, {y}) out of bounds for image {self.width}x{self.height}")

    def sample_region(
        self,
        x: int, y: int,
        width: int, height: int,
        method: str = 'average'
    ) -> Color:
        """
        Sample a region of the image.

        Args:
            x, y: Top-left corner of region
            width, height: Size of region
            method: 'average', 'median', or 'dominant'

        Returns:
            Color representing the region
        """
        # Extract region
        x2 = min(x + width, self.width)
        y2 = min(y + height, self.height)
        region = self.array[y:y2, x:x2]

        if method == 'average':
            rgb = region.mean(axis=(0, 1)).astype(int)
        elif method == 'median':
            rgb = np.median(region.reshape(-1, 3), axis=0).astype(int)
        elif method == 'dominant':
            # Find most common color
            pixels = region.reshape(-1, 3)
            unique, counts = np.unique(pixels, axis=0, return_counts=True)
            rgb = unique[np.argmax(counts)]
        else:
            raise ValueError(f"Unknown method: {method}")

        return Color(int(rgb[0]), int(rgb[1]), int(rgb[2]))

    def extract_palette(
        self,
        num_colors: int = 5,
        sample_points: Optional[List[Tuple[int, int]]] = None
    ) -> List[Color]:
        """
        Extract a palette of dominant colors from the image.

        Args:
            num_colors: Number of colors to extract
            sample_points: Optional specific points to sample

        Returns:
            List of Color objects, sorted by dominance
        """
        if sample_points:
            colors = [self.pick(x, y) for x, y in sample_points]
        else:
            # Use k-means clustering for dominant colors
            from sklearn.cluster import KMeans

            pixels = self.array.reshape(-1, 3)
            # Sample pixels for speed (max 10000)
            if len(pixels) > 10000:
                indices = np.random.choice(len(pixels), 10000, replace=False)
                pixels = pixels[indices]

            kmeans = KMeans(n_clusters=num_colors, random_state=42, n_init=10)
            kmeans.fit(pixels)

            # Sort by cluster size
            colors = []
            for center in kmeans.cluster_centers_:
                colors.append(Color(int(center[0]), int(center[1]), int(center[2])))

            # Sort by dominance
            colors.sort(key=lambda c: -c.brightness())

        return colors

    def generate_css_vars(
        self,
        regions: Dict[str, Tuple[int, int, int, int]],
        output_format: str = 'css'
    ) -> str:
        """
        Generate CSS variables from sampled regions.

        Args:
            regions: Dict mapping variable names to (x, y, w, h) regions
            output_format: 'css', 'json', or 'yaml'

        Returns:
            Formatted string of color definitions
        """
        colors = {}
        for name, (x, y, w, h) in regions.items():
            colors[name] = self.sample_region(x, y, w, h)

        if output_format == 'css':
            lines = [":root {"]
            for name, color in colors.items():
                lines.append(f"    --{name}: {color.to_hex()};")
                lines.append(f"    --{name}-rgb: {color.to_css_rgb()};")
            lines.append("}")
            return "\n".join(lines)

        elif output_format == 'json':
            data = {name: color.to_hex() for name, color in colors.items()}
            return json.dumps(data, indent=2)

        elif output_format == 'yaml':
            lines = ["# Color Palette from Mockup"]
            for name, color in colors.items():
                lines.append(f"{name}: {color.to_hex()}  # {color.to_css_rgb()}")
            return "\n".join(lines)

    def scan_horizontal(
        self,
        y: int,
        start_x: int = 0,
        end_x: Optional[int] = None
    ) -> List[Tuple[int, Color]]:
        """
        Scan a horizontal line and return color changes.

        Useful for identifying borders, shadows, gradients.

        Args:
            y: Y coordinate to scan
            start_x: Starting X position
            end_x: Ending X position (None = image width)

        Returns:
            List of (x, Color) tuples where color changes
        """
        if end_x is None:
            end_x = self.width

        end_x = min(end_x, self.width)
        prev_color = None
        changes = []

        for x in range(start_x, end_x):
            color = self.pick(x, y)
            if prev_color is None or color.rgb != prev_color.rgb:
                changes.append((x, color))
                prev_color = color

        return changes

    def scan_vertical(
        self,
        x: int,
        start_y: int = 0,
        end_y: Optional[int] = None
    ) -> List[Tuple[int, Color]]:
        """
        Scan a vertical line and return color changes.

        Args:
            x: X coordinate to scan
            start_y: Starting Y position
            end_y: Ending Y position (None = image height)

        Returns:
            List of (y, Color) tuples where color changes
        """
        if end_y is None:
            end_y = self.height

        end_y = min(end_y, self.height)
        prev_color = None
        changes = []

        for y in range(start_y, end_y):
            color = self.pick(x, y)
            if prev_color is None or color.rgb != prev_color.rgb:
                changes.append((y, color))
                prev_color = color

        return changes

    def find_border(
        self,
        search_color: Color,
        tolerance: int = 10,
        direction: str = 'inward'
    ) -> Dict[str, int]:
        """
        Find the borders of a colored region.

        Args:
            search_color: Color to search for
            tolerance: Color matching tolerance (0-255)
            direction: 'inward' or 'outward'

        Returns:
            Dict with 'top', 'bottom', 'left', 'right' positions
        """
        top, bottom, left, right = None, None, None, None

        # Search from top
        for y in range(self.height):
            if any(self._color_match(self.pick(x, y), search_color, tolerance)
                   for x in range(self.width)):
                top = y
                break

        # Search from bottom
        for y in range(self.height - 1, -1, -1):
            if any(self._color_match(self.pick(x, y), search_color, tolerance)
                   for x in range(self.width)):
                bottom = y
                break

        # Search from left
        for x in range(self.width):
            if any(self._color_match(self.pick(x, y), search_color, tolerance)
                   for y in range(self.height)):
                left = x
                break

        # Search from right
        for x in range(self.width - 1, -1, -1):
            if any(self._color_match(self.pick(x, y), search_color, tolerance)
                   for y in range(self.height)):
                right = x
                break

        return {'top': top, 'bottom': bottom, 'left': left, 'right': right}

    def _color_match(self, c1: Color, c2: Color, tolerance: int) -> bool:
        """Check if two colors match within tolerance."""
        return (
            abs(c1.r - c2.r) <= tolerance and
            abs(c1.g - c2.g) <= tolerance and
            abs(c1.b - c2.b) <= tolerance
        )

    def compare_colors(self, other: 'ColorPicker') -> Dict[str, float]:
        """
        Compare color distribution with another image.

        Args:
            other: Another ColorPicker instance

        Returns:
            Dict with similarity metrics
        """
        # Simple histogram comparison
        hist1 = self._get_histogram()
        hist2 = other._get_histogram()

        # Calculate correlation
        correlation = np.corrcoef(
            hist1.flatten(),
            hist2.flatten()
        )[0, 1]

        return {'correlation': float(correlation)}

    def _get_histogram(self) -> np.ndarray:
        """Get color histogram."""
        return np.histogramdd(
            self.array.reshape(-1, 3),
            bins=(32, 32, 32),
            range=((0, 256), (0, 256), (0, 256))
        )[0]


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    import argparse
    import sys

    parser = argparse.ArgumentParser(
        description='Color Picker for GUI Development'
    )
    parser.add_argument('image', help='Path to image file')
    parser.add_argument('--pick', nargs=2, type=int, metavar=('X', 'Y'),
                       help='Pick color at coordinates')
    parser.add_argument('--region', nargs=4, type=int,
                       metavar=('X', 'Y', 'W', 'H'),
                       help='Sample average color from region')
    parser.add_argument('--css-vars', help='Generate CSS vars from JSON spec file')
    parser.add_argument('--scan-h', type=int, metavar='Y',
                       help='Scan horizontal line at Y')
    parser.add_argument('--scan-v', type=int, metavar='X',
                       help='Scan vertical line at X')
    parser.add_argument('--palette', type=int, default=5, metavar='N',
                       help='Extract N dominant colors')
    parser.add_argument('--format', choices=['hex', 'rgb', 'hsl'],
                       default='hex', help='Output format')

    args = parser.parse_args()

    picker = ColorPicker(args.image)

    if args.pick:
        x, y = args.pick
        color = picker.pick(x, y)
        if args.format == 'hex':
            print(color.to_hex())
        elif args.format == 'rgb':
            print(color.to_css_rgb())
        elif args.format == 'hsl':
            print(color.to_css_hsl())

    elif args.region:
        x, y, w, h = args.region
        color = picker.sample_region(x, y, w, h)
        print(f"Average color: {color.to_hex()}  # {color.to_css_rgb()}")

    elif args.scan_h:
        changes = picker.scan_horizontal(args.scan_h)
        print(f"Horizontal scan at y={args.scan_h}:")
        for x, color in changes:
            print(f"  x={x:4d}: {color.to_hex()}")

    elif args.scan_v:
        changes = picker.scan_vertical(args.scan_v)
        print(f"Vertical scan at x={args.scan_v}:")
        for y, color in changes:
            print(f"  y={y:4d}: {color.to_hex()}")

    elif args.palette:
        colors = picker.extract_palette(args.palette)
        print(f"Top {args.palette} colors:")
        for i, color in enumerate(colors, 1):
            print(f"  {i}. {color.to_hex()}  # {color.to_css_rgb()}")

    else:
        # Default: show basic info
        print(f"Image: {args.image}")
        print(f"Size: {picker.width} x {picker.height}")
        print(f"Center pixel: {picker.pick(picker.width//2, picker.height//2).to_hex()}")


if __name__ == '__main__':
    main()
