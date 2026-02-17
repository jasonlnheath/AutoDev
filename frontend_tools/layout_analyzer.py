"""
Layout Analyzer - Measure positions, sizes, and spacing from mockup images

Usage:
    from frontend_tools.layout_analyzer import LayoutAnalyzer

    analyzer = LayoutAnalyzer("mockup.jpg")

    # Measure a component
    knob = analyzer.measure_component(100, 50, 80, 80)
    print(f"Knob size: {knob.width}x{knob.height}")

    # Find all components by color
    knobs = analyzer.find_by_color("#C0C0C0", tolerance=20)
    for knob in knobs:
        print(f"Knob at ({knob.x}, {knob.y}): {knob.width}x{knob.height}")

    # Analyze spacing
    spacing = analyzer.measure_spacing(knobs[0], knobs[1])
    print(f"Horizontal gap: {spacing.horizontal}px")
"""

from PIL import Image, ImageDraw, ImageFont
import numpy as np
from typing import List, Tuple, Dict, Optional
from dataclasses import dataclass
import json


@dataclass
class Component:
    """A detected UI component with position and size."""
    x: int
    y: int
    width: int
    height: int
    color: Tuple[int, int, int]
    label: str = ""

    @property
    def center_x(self) -> int:
        return self.x + self.width // 2

    @property
    def center_y(self) -> int:
        return self.y + self.height // 2

    @property
    def right(self) -> int:
        return self.x + self.width

    @property
    def bottom(self) -> int:
        return self.y + self.height

    def to_dict(self) -> dict:
        return {
            'x': self.x, 'y': self.y,
            'width': self.width, 'height': self.height,
            'center_x': self.center_x, 'center_y': self.center_y,
            'color': f"#{self.color[0]:02X}{self.color[1]:02X}{self.color[2]:02X}",
            'label': self.label
        }


@dataclass
class Spacing:
    """Spacing measurements between components."""
    horizontal: int  # Horizontal gap
    vertical: int    # Vertical gap
    edge_to_edge: bool  # True = edge-to-edge, False = center-to-center


class LayoutAnalyzer:
    """Analyze layout from mockup images."""

    def __init__(self, image_path: str, scale_factor: float = 1.0):
        """
        Initialize with an image path.

        Args:
            image_path: Path to the mockup/screenshot image
            scale_factor: If mockup is scaled (e.g., 1.85 for 185% DPI), divide coordinates by this
        """
        self.image_path = image_path
        self.scale_factor = scale_factor
        self.image = Image.open(image_path)
        if self.image.mode != 'RGB':
            self.image = self.image.convert('RGB')
        self.array = np.array(self.image)

    def scale(self, value: int) -> int:
        """Scale a coordinate/size to actual GUI pixels."""
        return int(value / self.scale_factor)

    def unscale(self, value: int) -> int:
        """Convert actual GUI pixels to image coordinates."""
        return int(value * self.scale_factor)

    @property
    def width(self) -> int:
        return int(self.image.width / self.scale_factor)

    @property
    def height(self) -> int:
        return int(self.image.height / self.scale_factor)

    def measure_component(
        self,
        x: int, y: int,
        sample_mode: str = 'expand'
    ) -> Component:
        """
        Measure a component starting from a seed point.

        Args:
            x, y: Starting coordinates (in image pixels, will be scaled)
            sample_mode: 'expand' (grow from seed) or 'box' (fixed size around seed)

        Returns:
            Component with measured bounds
        """
        # Get color at seed point
        seed_color = self._get_color(x, y)

        if sample_mode == 'expand':
            # Expand outward until we hit different colors
            bounds = self._expand_bounds(x, y, seed_color)
        else:
            # Use a fixed box around the seed
            bounds = (x - 20, y - 20, 40, 40)

        cx, cy, cw, ch = bounds
        return Component(
            x=self.scale(cx),
            y=self.scale(cy),
            width=self.scale(cw),
            height=self.scale(ch),
            color=seed_color
        )

    def _get_color(self, x: int, y: int) -> Tuple[int, int, int]:
        """Get color at coordinates."""
        x = max(0, min(x, self.image.width - 1))
        y = max(0, min(y, self.image.height - 1))
        r, g, b = self.array[y, x]
        return (int(r), int(g), int(b))

    def _expand_bounds(
        self,
        start_x: int, start_y: int,
        target_color: Tuple[int, int, int],
        tolerance: int = 30
    ) -> Tuple[int, int, int, int]:
        """Expand from seed point to find component bounds."""
        # Simple expansion - grow in each direction until color changes
        left = start_x
        right = start_x
        top = start_y
        bottom = start_y

        # Grow left
        for x in range(start_x - 1, -1, -1):
            if not self._color_match(self._get_color(x, start_y), target_color, tolerance):
                break
            left = x

        # Grow right
        for x in range(start_x + 1, self.image.width):
            if not self._color_match(self._get_color(x, start_y), target_color, tolerance):
                break
            right = x

        # Grow up
        for y in range(start_y - 1, -1, -1):
            if not self._color_match(self._get_color(start_x, y), target_color, tolerance):
                break
            top = y

        # Grow down
        for y in range(start_y + 1, self.image.height):
            if not self._color_match(self._get_color(start_x, y), target_color, tolerance):
                break
            bottom = y

        return (left, top, right - left + 1, bottom - top + 1)

    def _color_match(
        self,
        c1: Tuple[int, int, int],
        c2: Tuple[int, int, int],
        tolerance: int
    ) -> bool:
        """Check if two colors match within tolerance."""
        return (
            abs(c1[0] - c2[0]) <= tolerance and
            abs(c1[1] - c2[1]) <= tolerance and
            abs(c1[2] - c2[2]) <= tolerance
        )

    def find_by_color(
        self,
        color: str,
        tolerance: int = 20,
        min_size: int = 10
    ) -> List[Component]:
        """
        Find all components matching a color.

        Args:
            color: Hex color (e.g., "#C0C0C0")
            tolerance: Color matching tolerance
            min_size: Minimum component size

        Returns:
            List of Components
        """
        # Parse hex color
        target_color = tuple(int(color[i:i+2], 16) for i in (1, 3, 5))

        # Find connected components of similar color
        visited = set()
        components = []

        for y in range(0, self.image.height, 5):  # Sample every 5 pixels
            for x in range(0, self.image.width, 5):
                if (x, y) in visited:
                    continue

                pixel_color = self._get_color(x, y)
                if self._color_match(pixel_color, target_color, tolerance):
                    # Found a matching pixel, find the full component
                    bounds = self._expand_bounds(x, y, target_color, tolerance)
                    cx, cy, cw, ch = bounds

                    if cw >= min_size and ch >= min_size:
                        comp = Component(
                            x=self.scale(cx),
                            y=self.scale(cy),
                            width=self.scale(cw),
                            height=self.scale(ch),
                            color=pixel_color
                        )
                        components.append(comp)

                        # Mark visited (simplified)
                        for vy in range(cy, cy + ch, 5):
                            for vx in range(cx, cx + cw, 5):
                                visited.add((vx, vy))

        return components

    def find_circular_components(
        self,
        min_radius: int = 10,
        max_radius: int = 50
    ) -> List[Component]:
        """
        Find circular components (knobs, LEDs).

        Uses gradient-based edge detection to find circles.
        """
        from skimage.feature import canny
        from skimage.transform import hough_circle
        from skimage.feature import peak_local_max

        # Convert to grayscale
        gray = np.array(self.image.convert('L'))

        # Detect edges
        edges = canny(gray, sigma=2, low_threshold=20, high_threshold=50)

        # Find circles
        hough_radii = np.arange(min_radius, max_radius, 2)
        hough_res = hough_circle(edges, hough_radii)

        # Find peaks
        _, cx, cy, radii = peak_local_max(
            hough_res,
            min_distance=30,
            threshold_rel=0.3
        )

        components = []
        for x, y, r in zip(cx, cy, radii):
            color = self._get_color(int(x), int(y))
            comp = Component(
                x=self.scale(int(x - r)),
                y=self.scale(int(y - r)),
                width=self.scale(int(r * 2)),
                height=self.scale(int(r * 2)),
                color=color
            )
            components.append(comp)

        return components

    def measure_spacing(
        self,
        comp1: Component,
        comp2: Component
    ) -> Spacing:
        """Measure spacing between two components."""
        if comp2.x > comp1.x:
            # Horizontal spacing
            h_gap = comp2.x - comp1.right
        else:
            h_gap = comp1.x - comp2.right

        if comp2.y > comp1.y:
            # Vertical spacing
            v_gap = comp2.y - comp1.bottom
        else:
            v_gap = comp1.y - comp2.bottom

        return Spacing(horizontal=h_gap, vertical=v_gap, edge_to_edge=True)

    def measure_text_height(
        self,
        y: int,
        sample_x: int = 100
    ) -> int:
        """
        Measure the height of text at a given Y position.

        Scans vertically to find text boundaries.
        """
        # Find top of text
        top = y
        for y_check in range(y, max(0, y - 50), -1):
            color_before = self._get_color(sample_x, y_check)
            color_after = self._get_color(sample_x, y_check + 1)
            if abs(color_before[0] - color_after[0]) > 10:
                top = y_check
                break

        # Find bottom of text
        bottom = y
        for y_check in range(y, min(self.image.height, y + 50)):
            color_before = self._get_color(sample_x, y_check)
            color_after = self._get_color(sample_x, y_check + 1)
            if abs(color_before[0] - color_after[0]) > 10:
                bottom = y_check
                break

        return self.scale(bottom - top)

    def detect_labels(self) -> List[Component]:
        """
        Detect text labels in the image.

        Uses OCR to find text regions.
        """
        try:
            import pytesseract
            from PIL import ImageFilter

            # Enhance contrast for better OCR
            enhanced = self.image.filter(ImageFilter.SHARPEN)

            # Get OCR data with bounding boxes
            data = pytesseract.image_to_data(
                enhanced,
                output_type=pytesseract.Output.DICT
            )

            labels = []
            for i, text in enumerate(data['text']):
                text = text.strip()
                if not text:
                    continue

                x = data['left'][i]
                y = data['top'][i]
                w = data['width'][i]
                h = data['height'][i]

                if w < 5 or h < 5:  # Skip tiny detections
                    continue

                # Get background color
                color = self._get_color(x + w//2, y + h//2)

                comp = Component(
                    x=self.scale(x),
                    y=self.scale(y),
                    width=self.scale(w),
                    height=self.scale(h),
                    color=color,
                    label=text
                )
                labels.append(comp)

            return labels

        except ImportError:
            print("Warning: pytesseract not available, skipping label detection")
            return []

    def analyze_layout(self) -> dict:
        """
        Perform comprehensive layout analysis.

        Returns:
            Dict with detected components, spacing, labels
        """
        return {
            'labels': [l.to_dict() for l in self.detect_labels()],
            'image_size': {'width': self.width, 'height': self.height},
            'scale_factor': self.scale_factor
        }

    def generate_spec(self, output_path: str = None) -> str:
        """
        Generate YAML specification from mockup analysis.

        Args:
            output_path: Optional file path to write the spec

        Returns:
            YAML specification string
        """
        analysis = self.analyze_layout()

        yaml_lines = [
            "# Generated from mockup analysis",
            f"# Image: {self.image_path}",
            f"# Scale factor: {self.scale_factor}",
            "",
            "gui:",
            f"  width: {self.width}",
            f"  height: {self.height}",
            "",
            "  sections:",
            "    - name: header",
            "      height: 50",
            "      components:",
        ]

        # Add detected labels as components
        for label in analysis['labels']:
            yaml_lines.append(f"        - type: label")
            yaml_lines.append(f"          text: \"{label['label']}\"")
            yaml_lines.append(f"          x: {label['x']}")
            yaml_lines.append(f"          y: {label['y']}")
            yaml_lines.append(f"          width: {label['width']}")
            yaml_lines.append(f"          height: {label['height']}")

        yaml_content = "\n".join(yaml_lines)

        if output_path:
            with open(output_path, 'w') as f:
                f.write(yaml_content)

        return yaml_content

    def visualize_analysis(
        self,
        components: List[Component] = None,
        output_path: str = None
    ) -> Image.Image:
        """
        Create a visualization of detected components.

        Args:
            components: List of components to draw (auto-detect if None)
            output_path: Optional path to save the visualization

        Returns:
            PIL Image with overlaid annotations
        """
        # Create a copy for drawing
        vis = self.image.copy()
        draw = ImageDraw.Draw(vis)

        # Auto-detect if no components provided
        if components is None:
            components = []
            # Try to detect labels
            for label in self.detect_labels():
                components.append(label)

        # Draw each component
        for comp in components:
            # Scale back to image coordinates
            x = self.unscale(comp.x)
            y = self.unscale(comp.y)
            w = self.unscale(comp.width)
            h = self.unscale(comp.height)

            # Draw bounding box
            draw.rectangle([x, y, x + w, y + h], outline=(0, 255, 0), width=2)

            # Draw label if present
            if comp.label:
                try:
                    font = ImageFont.truetype("arial.ttf", 12)
                except:
                    font = ImageFont.load_default()
                draw.text((x, y - 15), comp.label, fill=(0, 255, 0), font=font)

        if output_path:
            vis.save(output_path)

        return vis


# ============================================================================
# CLI Interface
# ============================================================================

def main():
    import argparse

    parser = argparse.ArgumentParser(
        description='Analyze GUI layout from mockup images'
    )
    parser.add_argument('image', help='Path to mockup image')
    parser.add_argument('--scale', type=float, default=1.0,
                       help='Scale factor (e.g., 1.85 for 185%% DPI)')
    parser.add_argument('--measure', nargs=2, type=int, metavar=('X', 'Y'),
                       help='Measure component at coordinates')
    parser.add_argument('--find-color', metavar='HEX',
                       help='Find components by color')
    parser.add_argument('--detect-labels', action='store_true',
                       help='Detect text labels using OCR')
    parser.add_argument('--spec', metavar='OUTPUT.yaml',
                       help='Generate YAML specification')
    parser.add_argument('--visualize', metavar='OUTPUT.png',
                       help='Create visualization with detected components')

    args = parser.parse_args()

    analyzer = LayoutAnalyzer(args.image, scale_factor=args.scale)

    if args.measure:
        x, y = args.measure
        comp = analyzer.measure_component(x, y)
        print(f"Component at ({x}, {y}):")
        print(f"  Position: ({comp.x}, {comp.y})")
        print(f"  Size: {comp.width} x {comp.height}")
        print(f"  Color: {comp.color}")

    elif args.find_color:
        components = analyzer.find_by_color(args.find_color)
        print(f"Found {len(components)} components matching {args.find_color}:")
        for i, comp in enumerate(components, 1):
            print(f"  {i}. ({comp.x}, {comp.y}) - {comp.width}x{comp.height}")

    elif args.detect_labels:
        labels = analyzer.detect_labels()
        print(f"Detected {len(labels)} labels:")
        for label in labels:
            print(f"  \"{label.label}\" at ({label.x}, {label.y})")

    elif args.spec:
        yaml = analyzer.generate_spec(args.spec)
        print(f"Generated spec: {args.spec}")

    elif args.visualize:
        vis = analyzer.visualize_analysis(output_path=args.visualize)
        print(f"Saved visualization to {args.visualize}")

    else:
        # Default: basic info
        print(f"Image: {args.image}")
        print(f"Size (scaled): {analyzer.width} x {analyzer.height}")
        print(f"Scale factor: {args.scale}")


if __name__ == '__main__':
    main()
