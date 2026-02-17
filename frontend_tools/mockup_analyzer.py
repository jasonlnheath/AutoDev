"""
Mockup Analyzer Tool for VST Frontend AutoDev
Provides pixel measurement, color extraction, and layout analysis
"""

import sys
from PIL import Image
import json

def analyze_mockup(image_path: str) -> dict:
    """Get basic image information and color palette."""
    img = Image.open(image_path)
    width, height = img.size

    # Convert to RGB if needed
    if img.mode != 'RGB':
        img = img.convert('RGB')

    # Get dominant colors using simple sampling
    colors = {}
    for x in range(0, width, max(1, width // 50)):
        for y in range(0, height, max(1, height // 50)):
            pixel = img.getpixel((x, y))
            # Quantize to reduce color count
            quantized = tuple(c // 32 * 32 for c in pixel)
            colors[quantized] = colors.get(quantized, 0) + 1

    # Sort by frequency
    top_colors = sorted(colors.items(), key=lambda x: -x[1])[:10]

    return {
        "width": width,
        "height": height,
        "mode": img.mode,
        "top_colors": [
            {"rgb": c, "count": count, "hex": f"#{c[0]:02x}{c[1]:02x}{c[2]:02x}"}
            for c, count in top_colors
        ]
    }

def get_pixel_color(image_path: str, x: int, y: int) -> dict:
    """Get exact color at a specific pixel."""
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    if x < 0 or x >= img.width or y < 0 or y >= img.height:
        return {"error": f"Coordinates ({x}, {y}) out of bounds (0-{img.width-1}, 0-{img.height-1})"}

    pixel = img.getpixel((x, y))
    return {
        "x": x,
        "y": y,
        "rgb": pixel,
        "hex": f"#{pixel[0]:02x}{pixel[1]:02x}{pixel[2]:02x}"
    }

def measure_distance(image_path: str, x1: int, y1: int, x2: int, y2: int) -> dict:
    """Measure distance between two points."""
    import math
    dx = x2 - x1
    dy = y2 - y1
    distance = math.sqrt(dx*dx + dy*dy)

    return {
        "point1": {"x": x1, "y": y1},
        "point2": {"x": x2, "y": y2},
        "dx": dx,
        "dy": dy,
        "distance": distance
    }

def scan_horizontal(image_path: str, y: int, start_x: int = 0, end_x: int = None) -> dict:
    """Scan a horizontal line and detect color changes (edge detection)."""
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    if end_x is None:
        end_x = img.width

    edges = []
    prev_pixel = None
    for x in range(start_x, min(end_x, img.width)):
        pixel = img.getpixel((x, y))

        if prev_pixel is not None:
            # Calculate color difference
            diff = sum(abs(a - b) for a, b in zip(pixel, prev_pixel))
            if diff > 50:  # Threshold for "significant" change
                edges.append({
                    "x": x,
                    "color_before": prev_pixel,
                    "color_after": pixel,
                    "diff": diff
                })

        prev_pixel = pixel

    return {
        "y": y,
        "edges_found": len(edges),
        "edges": edges[:20]  # Limit output
    }

def scan_vertical(image_path: str, x: int, start_y: int = 0, end_y: int = None) -> dict:
    """Scan a vertical line and detect color changes (edge detection)."""
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    if end_y is None:
        end_y = img.height

    edges = []
    prev_pixel = None
    for y in range(start_y, min(end_y, img.height)):
        pixel = img.getpixel((x, y))

        if prev_pixel is not None:
            diff = sum(abs(a - b) for a, b in zip(pixel, prev_pixel))
            if diff > 50:
                edges.append({
                    "y": y,
                    "color_before": prev_pixel,
                    "color_after": pixel,
                    "diff": diff
                })

        prev_pixel = pixel

    return {
        "x": x,
        "edges_found": len(edges),
        "edges": edges[:20]
    }

def main():
    if len(sys.argv) < 3:
        print("Usage:")
        print("  python mockup_analyzer.py analyze <image_path>")
        print("  python mockup_analyzer.py pixel <image_path> <x> <y>")
        print("  python mockup_analyzer.py measure <image_path> <x1> <y1> <x2> <y2>")
        print("  python mockup_analyzer.py hscan <image_path> <y> [start_x] [end_x]")
        print("  python mockup_analyzer.py vscan <image_path> <x> [start_y] [end_y]")
        sys.exit(1)

    command = sys.argv[1]
    image_path = sys.argv[2]

    if command == "analyze":
        result = analyze_mockup(image_path)
    elif command == "pixel":
        if len(sys.argv) < 5:
            print("Usage: python mockup_analyzer.py pixel <image_path> <x> <y>")
            sys.exit(1)
        result = get_pixel_color(image_path, int(sys.argv[3]), int(sys.argv[4]))
    elif command == "measure":
        if len(sys.argv) < 7:
            print("Usage: python mockup_analyzer.py measure <image_path> <x1> <y1> <x2> <y2>")
            sys.exit(1)
        result = measure_distance(
            image_path,
            int(sys.argv[3]), int(sys.argv[4]),
            int(sys.argv[5]), int(sys.argv[6])
        )
    elif command == "hscan":
        y = int(sys.argv[3])
        start_x = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        end_x = int(sys.argv[5]) if len(sys.argv) > 5 else None
        result = scan_horizontal(image_path, y, start_x, end_x)
    elif command == "vscan":
        x = int(sys.argv[3])
        start_y = int(sys.argv[4]) if len(sys.argv) > 4 else 0
        end_y = int(sys.argv[5]) if len(sys.argv) > 5 else None
        result = scan_vertical(image_path, x, start_y, end_y)
    else:
        print(f"Unknown command: {command}")
        sys.exit(1)

    print(json.dumps(result, indent=2))

if __name__ == "__main__":
    main()
