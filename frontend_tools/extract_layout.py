"""
Extract Layout from Mockup Image
Generates a YAML specification for the frontend
"""

import sys
import json
from PIL import Image

def extract_layout(image_path: str) -> dict:
    """Extract layout information from mockup."""
    img = Image.open(image_path)
    if img.mode != 'RGB':
        img = img.convert('RGB')

    width, height = img.size

    # Detect horizontal regions by scanning for significant color changes
    def find_horizontal_regions():
        regions = []
        prev_y = 0

        for y in range(height):
            # Sample a few pixels across the width
            colors = []
            for x in [464]:  # Center
                colors.append(img.getpixel((x, y)))

            # Check for significant brightness change
            if y > 0:
                curr_brightness = sum(colors[0]) / 3
                prev_colors = [img.getpixel((464, y-1))]
                prev_brightness = sum(prev_colors[0]) / 3

                if abs(curr_brightness - prev_brightness) > 30:
                    regions.append({"y": y, "brightness": curr_brightness})

        return regions

    # Find the cyan accent color positions
    def find_cyan_regions():
        cyan_regions = []
        for y in range(height):
            for x in range(width):
                r, g, b = img.getpixel((x, y))
                # Cyan detection: high green and blue, low red
                if g > 150 and b > 150 and r < 150 and g > r + 40 and b > r + 40:
                    cyan_regions.append({"x": x, "y": y})
                    break
            else:
                continue
            break  # Only first per row

        return cyan_regions

    # Detect knob-like circular regions
    def find_knobs():
        knobs = []

        # Sample regions that might contain knobs
        # Look for circular patterns of similar brightness
        potential_centers = [
            (80, 50, "IN"),      # Top left
            (850, 50, "OUT"),    # Top right
            (464, 350, "MIX"),   # Center
        ]

        for cx, cy, name in potential_centers:
            # Find approximate radius by scanning outward
            radius = estimate_knob_radius(img, cx, cy)
            if radius > 10:
                knobs.append({
                    "name": name,
                    "center_x": cx,
                    "center_y": cy,
                    "radius": radius,
                    "diameter": radius * 2
                })

        return knobs

    def estimate_knob_radius(img, cx, cy):
        """Estimate knob radius by finding edge."""
        # Scan horizontally from center
        radius = 0
        for dx in range(0, 100):
            x = cx + dx
            if x >= img.width:
                break
            pixel = img.getpixel((x, cy))
            brightness = sum(pixel) / 3

            # Look for significant edge
            if dx > 0:
                prev_pixel = img.getpixel((x-1, cy))
                prev_brightness = sum(prev_pixel) / 3
                if abs(brightness - prev_brightness) > 60:
                    radius = dx
                    break

        # Also check left side
        for dx in range(0, 100):
            x = cx - dx
            if x < 0:
                break
            pixel = img.getpixel((x, cy))
            brightness = sum(pixel) / 3

            if dx > 0:
                prev_pixel = img.getpixel((x+1, cy))
                prev_brightness = sum(prev_pixel) / 3
                if abs(brightness - prev_brightness) > 60:
                    left_radius = dx
                    radius = max(radius, left_radius)
                    break

        return radius

    knobs = find_knobs()
    cyan = find_cyan_regions()
    regions = find_horizontal_regions()

    return {
        "image_size": {"width": width, "height": height},
        "horizontal_regions": regions[:10],
        "cyan_accent_positions": cyan[:5],
        "detected_knobs": knobs
    }

def generate_spec(layout: dict, plugin_name: str = "ClassicSpringReverb") -> str:
    """Generate YAML specification from layout."""

    spec = f"""# {plugin_name} Frontend Specification
# Generated from mockup analysis

plugin:
  name: "{plugin_name}"
  size:
    width: {layout['image_size']['width']}
    height: {layout['image_size']['height']}

layout:
  # Title bar: y=0 to y=~30
  # Top control bar: y=~30 to y=~80
  # Main display: y=~80 to bottom

  title_bar:
    height: 30

  top_bar:
    height: 50
    controls:
      - name: "IN"
        type: "knob"
        position: {{ x: 80, y: 50 }}
"""

    for knob in layout.get('detected_knobs', []):
        spec += f"""      - name: "{knob['name']}"
        type: "knob"
        position: {{ x: {knob['center_x']}, y: {knob['center_y']} }}
        size: {{ diameter: {knob['diameter']} }}
"""

    spec += """
parameters:
  - id: "mix"
    type: "float"
    min: 0.0
    max: 1.0
    default: 0.5
    increment: 0.01
    label: "Mix"
    component: "knob"

  - id: "input_gain"
    type: "float"
    min: -60.0
    max: 6.0
    default: 0.0
    increment: 0.1
    unit: "dB"
    label: "IN"
    component: "knob"

  - id: "output_gain"
    type: "float"
    min: -60.0
    max: 6.0
    default: 0.0
    increment: 0.1
    unit: "dB"
    label: "OUT"
    component: "knob"

colors:
  background: "#202020"
  secondary: "#404040"
  tertiary: "#606060"
  accent: "#a0e0e0"
  accent_dark: "#204040"
  text: "#e0e0e0"
  text_muted: "#808080"
"""

    return spec

def main():
    if len(sys.argv) < 2:
        print("Usage: python extract_layout.py <image_path>")
        sys.exit(1)

    image_path = sys.argv[1]
    layout = extract_layout(image_path)

    print("=== Layout Analysis ===")
    print(json.dumps(layout, indent=2))
    print("\n=== Generated Specification ===")
    print(generate_spec(layout))

if __name__ == "__main__":
    main()
