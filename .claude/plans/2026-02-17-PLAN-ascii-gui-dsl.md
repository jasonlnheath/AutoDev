# ASCII GUI DSL System - Implementation Plan

**Created:** 2025-02-17
**Status:** Planning Phase
**Goal:** Eliminate vision model dependency for GUI development

---

## Overview

A text-based GUI design system where:
1. You write ASCII art with measurements
2. Browser shows live, interactive preview
3. No plugin rebuild during design
4. Generate final code once when done

**Key Innovation:** ASCII DSL as source of truth, browser preview for verification.

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│                        WORKFLOW                                     │
├─────────────────────────────────────────────────────────────────────┤
│                                                                     │
│  ┌──────────────┐    ┌──────────────┐    ┌──────────────┐         │
│  │   Edit       │    │   Preview    │    │   Generate   │         │
│  │ ASCII DSL    │───▶│ in Browser   │───▶│ Plugin Code  │         │
│  │              │    │ (instant)    │    │ (once when   │         │
│  │ gui_design   │    │ (interactive)│    │  done)       │         │
│  └──────────────┘    └──────────────┘    └──────────────┘         │
│         ↑                   │                                      │
│         │                   │                                      │
│    Component Library  ──────┘                                      │
│    (browse & select)                                                │
│                                                                     │
└─────────────────────────────────────────────────────────────────────┘
```

---

## ASCII DSL Syntax

### File Format: `gui_design.txt`

```ascii
# Comment: Plugin description
NAME: HeathAudioPluginTemplate
SIZE: 500x340
SCALE: 1.0

# Global styles
COLORS:
  toolbar_bg: #414141
  panel_bg: #303430
  accent: #a0e0e0

# Header section
SECTION header HEIGHT:50 Y:0 BG:toolbar_bg
  ┌──────────────────────────────────────────────────────────────┐
  │ [knob:input] X:10 Y:10 SIZE:56 LABEL:"IN"                    │
  │ [dropdown:preset] X:80 Y:15 WIDTH:100 LABEL:"PRESET"         │
  │ [logo:heath] X:CENTER Y:5                                     │
  │ [dropdown:os] X:600 Y:15 LABEL:"OS"                          │
  │ [dropdown:zoom] X:700 Y:15 LABEL:"ZOOM"                      │
  │ [knob:output] X:850 Y:10 SIZE:56 LABEL:"OUT"                 │
  └──────────────────────────────────────────────────────────────┘

# Main section
SECTION main Y:50 HEIGHT:290 BG:panel_bg
  ┌──────────────────────────────────────────────────────────────┐
  │ [meter:input] X:10 Y:10 WIDTH:12 HEIGHT:270 COLOR:accent    │
  │                                                              │
  │  [panel:center] X:50 Y:10 WIDTH:400 HEIGHT:270             │
  │  ╔════════════════════════════════════════════════════════╗  │
  │  ║                                                        ║  │
  │  ║  <!-- Plugin-specific content -->                      ║  │
  │  ║                                                        ║  │
  │  ╚════════════════════════════════════════════════════════╝  │
  │                                                              │
  │ [meter:output] X:878 Y:10 WIDTH:12 HEIGHT:270 COLOR:accent │
  └──────────────────────────────────────────────────────────────┘
```

### Component Syntax

```
[component_type:id] PROPERTY:value PROPERTY:value ...

Common Properties:
  X, Y          - Position (supports CENTER, LEFT, RIGHT)
  WIDTH, HEIGHT - Size
  SIZE          - For square/circular items
  LABEL         - Text label
  VALUE         - Initial value (0-1)
  COLOR         - Color reference or hex
  BG            - Background color
```

---

## Component Library

### Library Structure

```
frontend_tools/
├── components/
│   ├── __init__.py
│   ├── base.py              # Base component class
│   ├── controls/
│   │   ├── knob.py          # Rotary knob (canvas)
│   │   ├── slider.py        # Linear slider
│   │   ├── button.py        # Click button
│   │   ├── dropdown.py      # Dropdown menu
│   │   └── toggle.py        # Toggle switch
│   ├── displays/
│   │   ├── meter.py         # Vertical meter
│   │   ├── label.py         # Text label
│   │   ├── led.py           # LED indicator
│   │   ├── waveform.py      # Waveform display
│   │   └── spectrum.py      # Spectrum analyzer
│   ├── containers/
│   │   ├── panel.py         # Container with border
│   │   ├── group.py         # Group box
│   │   └── tabs.py          # Tab container
│   └── media/
│       ├── logo.py          # Image/logo
│       └── icon.py          # Icon
├── catalog/
│   ├── index.html           # Component catalog viewer
│   └── showcase.html        # Interactive showcase
└── ascii_dsl/
    ├── parser.py            # Parse ASCII DSL
    ├── generator.py         # Generate HTML/CSS/JS
    └── preview_server.py    # Live preview server
```

### Viewing Components

**Method 1: Component Catalog (HTML)**
```
http://localhost:8000/catalog/

Shows all components with:
- Visual preview (rendered)
- ASCII syntax example
- Available properties
- Live demo
```

**Method 2: CLI List**
```bash
$ python frontend_tools/ascii_dsl.py list-components

Controls:
  knob          - Rotary control (canvas-based)
  slider        - Linear slider
  button        - Click button
  dropdown      - Dropdown menu
  toggle        - Toggle switch

Displays:
  meter         - Vertical level meter
  label         - Text label
  led           - LED indicator
  waveform      - Waveform display

Containers:
  panel         - Bordered container
  group         - Group box
  tabs          - Tab container

Media:
  logo          - Image/logo
  icon          - Icon

Usage: python frontend_tools/ascii_dsl.py show <component>
```

**Method 3: Inline Documentation**
```bash
$ python frontend_tools/ascii_dsl.py show knob

=== COMPONENT: knob ===

Type: Control
Description: Rotary knob control (canvas-based rendering)

ASCII Syntax:
  [knob:id] X:10 Y:10 SIZE:56 VALUE:0.5 LABEL:"Gain"

Properties:
  X, Y          - Position (required)
  SIZE          - Diameter in pixels (default: 50)
  VALUE         - Initial value 0-1 (default: 0)
  LABEL         - Text label below knob
  MIN           - Minimum value (default: 0)
  MAX           - Maximum value (default: 1)
  COLOR         - Knob color (default: from theme)
  INDICATOR     - Indicator style: line/dot (default: line)

Live Preview: http://localhost:8000/show/knob

Example Output:
  <canvas class="knob" id="knob_id" width="56" height="56"></canvas>
  <span class="knob-label">Gain</span>
```

---

## Component Catalog UI

### Catalog Viewer: `frontend_tools/catalog/index.html`

**Layout:**
```
┌─────────────────────────────────────────────────────────────────┐
│                    Component Catalog                             │
├─────────────────────────────────────────────────────────────────┤
│  Search: [______________]  Filter: [All ▼]                       │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐             │
│  │    KNOB     │  │   METER     │  │  DROPDOWN   │             │
│  │   ( ○ )     │  │   ████▓     │  │ [ PRESET ▼] │             │
│  │             │  │             │  │             │             │
│  │ [View Demo] │  │ [View Demo] │  │ [View Demo] │             │
│  └─────────────┘  └─────────────┘  └─────────────┘             │
│                                                                   │
│  Click component for details →                                    │
└─────────────────────────────────────────────────────────────────┘
```

### Component Detail Page

```
┌─────────────────────────────────────────────────────────────────┐
│  ← Back to Catalog                                               │
├─────────────────────────────────────────────────────────────────┤
│                                                                   │
│  ┌─────────────────────────────────────────────────────────┐    │
│  │                    Component: knob                        │    │
│  ├─────────────────────────────────────────────────────────┤    │
│  │                                                           │    │
│  │  ┌─────────────┐                                          │    │
│  │  │      ●      │  Live Preview (try dragging it!)       │    │
│  │  │             │  Value: 0.50                            │    │
│  │  │    GAIN     │                                          │    │
│  │  └─────────────┘                                          │    │
│  │                                                           │    │
│  │  ASCII Syntax:                                            │    │
│  │  [knob:gain] X:100 Y:50 SIZE:56 VALUE:0.5 LABEL:"GAIN"   │    │
│  │                                                           │    │
│  │  Properties:                                              │    │
│  │  • X, Y (required) - Position                             │    │
│  │  • SIZE (default: 50) - Diameter in pixels               │    │
│  │  • VALUE (default: 0) - Initial value 0-1                 │    │
│  │  • LABEL - Text label below                               │    │
│  │  • MIN, MAX - Value range                                 │    │
│  │  • INDICATOR - line/dot style                             │    │
│  │                                                           │    │
│  │  Generated Code: [HTML] [CSS] [JS]                        │    │
│  │                                                           │    │
│  └─────────────────────────────────────────────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
```

---

## Component Development Workflow

### When You Need a New Component

**1. Identify the Gap**
```
You: "I need a circular VU meter that goes around the outside of a knob"
```

**2. We Discuss Requirements**
```
Me: "Ok, let's define the component:
- Name: vu_meter_ring
- Renders as arc around a knob
- Properties: VALUE (0-1), COLOR, THICKNESS, DIRECTION
- ASCII: [vu_ring:id] X:50 Y:50 SIZE:60 VALUE:0.7 THICKNESS:3
"
```

**3. I Implement It**
```
File: frontend_tools/components/displays/vu_ring.py

class VURingComponent(Component):
    def render(self):
        # Canvas drawing for arc meter
        pass

    def to_ascii_example(self):
        return "[vu_ring:master] X:100 Y:100 SIZE:80 VALUE:0.8"
```

**4. Register in Catalog**
```python
# frontend_tools/components/__init__.py

COMPONENT_REGISTRY = {
    'knob': KnobComponent,
    'meter': MeterComponent,
    'vu_ring': VURingComponent,  # New!
    ...
}
```

**5. Available Immediately**
```
# You can now use it in ASCII DSL!
[vu_ring:master] X:200 Y:100 SIZE:70 VALUE:0.7 THICKNESS:4

# Preview server auto-reloads
# Catalog shows new component
```

### Component Template

```python
# frontend_tools/components/base.py

class Component:
    """Base class for all components."""

    type: str          # Component type name
    category: str      # controls/displays/containers/media
    name: str          # Human-readable name
    description: str   # What it does

    # Required properties
    required_props = ['x', 'y']

    # Optional properties with defaults
    optional_props = {
        'width': 50,
        'height': 50,
        'value': 0,
        'label': '',
    }

    def __init__(self, id: str, props: dict):
        self.id = id
        self.props = self.parse_props(props)

    def parse_props(self, props: dict) -> dict:
        """Parse and validate properties."""
        merged = {**self.optional_props, **props}
        # Validate required props
        return merged

    def render_html(self) -> str:
        """Generate HTML for this component."""
        raise NotImplementedError

    def render_css(self) -> str:
        """Generate CSS for this component."""
        raise NotImplementedError

    def render_js(self) -> str:
        """Generate JavaScript for this component."""
        raise NotImplementedError

    def get_catalog_entry(self) -> dict:
        """Return catalog information."""
        return {
            'type': self.type,
            'name': self.name,
            'description': self.description,
            'category': self.category,
            'required_props': self.required_props,
            'optional_props': self.optional_props,
            'example': self.get_example_ascii(),
        }
```

---

## Development Workflow

### Setup

```bash
# 1. Install dependencies
pip install flask watchdog

# 2. Start preview server
cd frontend_tools
python ascii_dsl/preview_server.py watch ../gui_design.txt

# 3. Open catalog in browser
open http://localhost:8000/catalog
```

### Design Phase

```bash
# You edit ASCII file
vim gui_design.txt

# Browser auto-reloads (hot reload!)
# Drag knobs, test dropdowns
# No plugin rebuild needed!

# Iterate until happy
# Edit → See result → Repeat
```

### When Component Missing

```bash
# 1. Check catalog
open http://localhost:8000/catalog

# 2. If not found, request it
# You: "I need X component"

# 3. I implement it
# (Behind the scenes - you don't wait)

# 4. Browser refresh shows new component
# 5. You can use it immediately
```

### Code Generation

```bash
# When design is final

# Generate plugin UI files
python ascii_dsl/generate.py gui_design.txt \
    --output ../templates/HeathAudioPluginTemplate/Source/ui/public/

# This creates:
# - index.html (with your layout)
# - styles.css (with your colors)
# - app.js (with working controls)
```

---

## Implementation Phases

### Phase 1: Core Infrastructure (Foundation)
- [ ] ASCII DSL parser
- [ ] Component base class
- [ ] HTML/CSS/JS generator
- [ ] Preview server (basic)

### Phase 2: Component Library (Essential Components)
- [ ] knob (rotary control)
- [ ] meter (vertical level meter)
- [ ] dropdown (menu)
- [ ] label (text)
- [ ] panel (container)
- [ ] led (indicator)

### Phase 3: Catalog & Discovery
- [ ] Catalog viewer HTML
- [ ] Component showcase page
- [ ] CLI list command
- [ ] Search functionality

### Phase 4: Advanced Components
- [ ] slider (linear control)
- [ ] button (click)
- [ ] waveform display
- [ ] spectrum analyzer
- [ ] vu_ring (circular meter)

### Phase 5: Polish & Integration
- [ ] Hot reload (file watcher)
- [ ] Round-trip editing (browser → ASCII)
- [ ] Theme system
- [ ] Animation/transition support

---

## File Structure Summary

```
AutoDev/
├── frontend_tools/
│   ├── components/
│   │   ├── __init__.py           # Component registry
│   │   ├── base.py               # Base component class
│   │   ├── controls/             # Interactive controls
│   │   │   ├── knob.py
│   │   │   ├── slider.py
│   │   │   ├── dropdown.py
│   │   │   └── button.py
│   │   ├── displays/             # Information displays
│   │   │   ├── meter.py
│   │   │   ├── label.py
│   │   │   ├── led.py
│   │   │   └── waveform.py
│   │   └── containers/           # Layout containers
│   │       ├── panel.py
│   │       └── group.py
│   ├── catalog/
│   │   ├── index.html            # Component catalog
│   │   ├── showcase.html         # Interactive demos
│   │   └── assets/
│   │       ├── css/
│   │       └── js/
│   └── ascii_dsl/
│       ├── parser.py             # Parse ASCII DSL
│       ├── generator.py          # Generate HTML/CSS/JS
│       ├── preview_server.py     # Live preview server
│       └── cli.py                # Command-line interface
│
├── gui_design.txt                # Your ASCII design
└── .claude/plans/
    └── 2026-02-17-PLAN-ascii-gui-dsl.md  # This file
```

---

## Example Session

```bash
# Terminal 1: Start preview server
$ python frontend_tools/ascii_dsl/preview_server.py watch gui_design.txt
Serving preview at http://localhost:8000
Watching gui_design.txt for changes...

# Terminal 2: You edit design
$ vim gui_design.txt

# Browser: Auto-updates, shows interactive preview
# You drag knobs, test dropdowns - everything works!

# You: "I need a toggle switch"
$ python frontend_tools/ascii_dsl.py request-component toggle

# (I implement toggle component)
# (Browser auto-reloads with new component)

# You add to design:
[toggle:bypass] X:400 Y:100 LABEL:"BYPASS" STATE:off

# Browser: Shows toggle immediately!

# When done:
$ python frontend_tools/ascii_dsl.py generate gui_design.txt \
    --output ../templates/HeathAudioPluginTemplate/Source/ui/public/

Generated:
  index.html (124 lines)
  styles.css (89 lines)
  app.js (234 lines)
```

---

## Success Criteria

**For the system:**
- ✅ ASCII DSL is human-readable and writable
- ✅ Preview updates within 1 second of file save
- ✅ All controls are interactive in preview
- ✅ Generated code works in JUCE plugin
- ✅ Component catalog is browsable

**For you:**
- ✅ Can view all available components
- ✅ Can see examples of how to use each component
- ✅ Can request new components and get them quickly
- ✅ Design without rebuilding plugin
- ✅ Iterate faster (seconds vs minutes)

---

## Next Steps

1. **Review this plan** - Does it address your needs?
2. **Approve Phase 1** - Start building core infrastructure
3. **Define initial components** - What do you need first?
4. **Set up workflow** - How do you want to work with this?

---

**Questions for Discussion:**

1. **Component Priority** - Which components do you need first?
   - knob, meter, dropdown, label, panel, led?

2. **Catalog Format** - How do you want to browse components?
   - Web page? CLI output? Both?

3. **New Component Workflow** - When you need something new:
   - Create issue in tracker?
   - Just tell me in chat?
   - Write stub in ASCII and I implement it?

4. **Round-trip Editing** - Do you need browser → ASCII editing?
   - Or is ASCII → browser enough?

---

## Skills to Build

### `/newcomp` - Request New Component

**Purpose:** Streamlined workflow for requesting new GUI components

**Usage:**
```
/newcomp
```

**What it does:**
- Prompts for component requirements
- Captures: type, name, properties, example usage
- Creates task in development queue
- Returns estimated implementation time

**Example interaction:**
```
You: /newcomp

Assistant: Let's create a new component. What do you need?

You: A circular LED ring around knobs

Assistant: Got it. Define the component:
  Name: vu_ring
  Category: displays
  Properties: VALUE, SIZE, THICKNESS, COLOR
  ASCII: [vu_ring:id] SIZE:60 VALUE:0.7 THICKNESS:3

  Creating component... Estimated 5 minutes.
  [Creates vu_ring.py]
  [Registers in catalog]
  [Adds demo page]
  Done! Preview: http://localhost:8000/show/vu_ring
```

---

## Session Notes: 2025-02-17

### Accomplishments Today
1. ✅ Created color picker tool (`color_picker.py`)
2. ✅ Created layout analyzer (`layout_analyzer.py`)
3. ✅ Created spec generator (`spec_generator.py`)
4. ✅ Fixed template title bar to match mockup (#414141 background)
5. ✅ Designed ASCII GUI DSL system architecture

### Key Decisions
- ASCII DSL as source of truth (not vision models)
- Browser preview for instant iteration
- Component catalog for discoverability
- `/newcomp` skill for streamlined component requests

### Current Template Status
- HeathAudioPluginTemplate with WebView2 GUI
- Title bar: #414141 (matches mockup)
- Colors: toolbar_bg #414141, panel_bg #303430
- Missing: Peak LEDs above meters, some labels
- Knobs: Need to remove center dot

### Tools Available
```bash
# Screenshot (DPI-aware)
python frontend/screenshot.py "PluginName" "output.jpg"

# Color extraction
python frontend_tools/color_picker.py mockup.jpg --pick 100 50
python frontend_tools/color_picker.py mockup.jpg --palette 8

# Layout analysis
python frontend_tools/layout_analyzer.py mockup.jpg --measure 100 50
python frontend_tools/layout_analyzer.py mockup.jpg --find-color "#C0C0C0"

# Spec generation
python frontend_tools/spec_generator.py mockup.jpg --output spec.yaml
```

### Next Session Priorities
1. Build Phase 1 of ASCII GUI DSL system
2. Create `/newcomp` skill
3. Implement initial components (knob, meter, dropdown, label)
4. Set up preview server with hot reload

---

**Great progress today! The ASCII GUI DSL system will eliminate vision model dependency for GUI development.**
