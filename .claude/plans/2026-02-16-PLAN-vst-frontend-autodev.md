# Frontend AutoDev for VST Plugins - Implementation Plan

## Context

Building on the successful AutoDev OODA loop framework (which completed Mal Steps 7-A with 100% test coverage), this project extends autonomous development to **VST plugin frontend creation**.

**Assumption**: Backend DSP is COMPLETE before frontend development begins. All parameters, ranges, and audio processing are working.

**Problem**: Creating JUCE WebView frontends (HTML/CSS/JS) is manual, repetitive work. Each plugin needs:
- Visual UI matching design mockups
- Parameter binding to backend
- Testing that controls affect audio correctly
- Color/size validation against design

**Goal**: Automate frontend generation from:
1. **GUI mockup image** - True-to-life visual design
2. **Specification document** - All control names, min/max/increment values, endpoints
3. **Backend parameter list** - Auto-discovered from running plugin

**Key Insight**: The user provides both visual (image) AND semantic (spec) inputs. Vision extracts layout/colors, spec provides exact values and names.

---

## Proposed Solution: Frontend OODA Loop

```
OBSERVE → ORIENT → DECIDE → ACT
   ↓         ↓        ↓       ↓
  Image   Patterns  HTML/    Test
  +       +        CSS      +
 Params  Similar   JS       Screenshot
                  Code     Validate
                           → Repeat
```

### User Workflow:
1. **User provides**:
   - GUI mockup image (true-to-life, actual size, with all controls)
   - Specification document (control names, min/max/increment, endpoints)
   - Running plugin binary (for parameter discovery and audio testing)
2. **AutoDev runs autonomous loop** → Generates working frontend
3. **AutoDev validates**:
   - Takes screenshots of generated UI
   - Uses librosa "hands" to control each parameter
   - Captures audio to verify controls affect output
   - Measures color/size accuracy vs. mockup
4. **User reviews**: Screenshots, audio validation, test results
5. **Iterate** if needed (or accept result)

### Key Innovation: "Librosa Hands"
The system gets **programmatic control** of the plugin via OSC:
- Set any parameter to any value
- Inject test audio signals
- Capture processed output
- Verify control changes affect audio

This enables **autonomous testing** without manual intervention.

---

## Input Formats

### 1. GUI Mockup Image
- **Format**: PNG or JPG
- **Requirements**:
  - True-to-life rendering (not sketch)
  - Actual plugin size (1:1 pixel ratio)
  - All controls visible
  - Clear component boundaries
  - Color-accurate

### 2. Specification Document (YAML)
```yaml
plugin:
  name: "DryWetMixerDemo"
  size: { width: 400, height: 200 }

parameters:
  - id: "mix"
    type: "float"
    min: 0.0
    max: 1.0
    default: 0.5
    increment: 0.01
    unit: ""
    label: "Mix"
    component: "slider"  # or knob, switch, etc.

components:
  - id: "mix_slider"
    type: "slider"
    position: { x: 50, y: 80 }
    size: { width: 300, height: 40 }
    label: "Dry/Wet Mix"
    parameter: "mix"

colors:
  background: "#1a1a2e"
  foreground: "#eaeaea"
  accent: "#4a90d9"
  text: "#ffffff"
```

### 3. Backend Endpoints (Auto-discovered via OSC)
```python
# Auto-discovered from running plugin
parameters = osc.get_parameter_list()
# Returns: [{"id": "mix", "min": 0.0, "max": 1.0, ...}, ...]
```

---

## Tech Stack

| Component | Tool | Purpose |
|-----------|------|---------|
| **Vision Analysis** | GLM-4.6v (z.ai) | Extract layout, colors, components from GUI image |
| **Code Generation** | GLM-4.7 | Generate HTML/CSS/JS matching design |
| **Parameter Discovery** | OSC to JUCE plugin | Auto-discover all params (min/max/default) |
| **Audio Testing** | librosa osc_control | Set params, inject signal, capture output |
| **Screenshot Capture** | Python + Win32 APIs | Capture plugin window only (not full screen) |
| **Color Measurement** | PIL/Pillow + ColorMath | Pick colors, calculate ΔE for validation |
| **Pixel Measurement** | PIL + custom tools | Measure distances, detect alignment |
| **Visual Diff** | OpenCV + SSIM | Compare generated UI vs. design mockup |

---

## Custom Tools for AutoDev

### 1. Plugin Screenshot Tool
Captures ONLY the plugin window (not full screen) with optional grid overlay.

```python
class PluginScreenshot:
    """Capture plugin window with measurement grid."""

    def capture(self, window_title: str, grid: bool = True) -> Image:
        """
        Capture plugin window.

        Features:
        - Finds window by title (e.g., "DryWetMixerDemo")
        - Captures only that window (not full screen)
        - Optional 10px grid overlay for measurement
        - Saves at true 1:1 pixel size
        """
        hwnd = self._find_window(window_title)
        rect = self._get_window_rect(hwnd)

        # Capture window content
        img = self._capture_window(hwnd)

        # Add grid overlay if requested
        if grid:
            img = self._add_grid(img, spacing=10, color=(100,100,100,128))

        return img

    def measure_distance(self, p1: tuple, p2: tuple) -> int:
        """Measure pixel distance between two points."""
        return int(((p2[0]-p1[0])**2 + (p2[1]-p1[1])**2)**0.5)
```

### 2. Color Picker Tool
Pick colors from screenshots and compare to expected values.

```python
class ColorPicker:
    """Pick and validate colors from screenshots."""

    def pick(self, image: Image, x: int, y: int) -> str:
        """Pick color at position, return hex."""
        return image.getpixel((x, y))

    def pick_region_average(self, image: Image, rect: tuple) -> str:
        """Get average color of a region."""
        region = image.crop(rect)
        pixels = list(region.getdata())
        r = sum(p[0] for p in pixels) // len(pixels)
        g = sum(p[1] for p in pixels) // len(pixels)
        b = sum(p[2] for p in pixels) // len(pixels)
        return f"#{r:02x}{g:02x}{b:02x}"

    def delta_e(self, color1: str, color2: str) -> float:
        """Calculate color difference (ΔE). Lower = more similar."""
        # Uses CIEDE2000 formula
        pass
```

### 3. Pixel Measurement Tool
Measure distances, alignments, and component sizes.

```python
class PixelMeasurement:
    """Measure UI elements in pixels."""

    def measure_component(self, image: Image, component_id: str) -> dict:
        """Get component dimensions from screenshot."""
        # Uses edge detection to find component boundaries
        pass

    def check_alignment(self, components: list) -> dict:
        """Check if components are aligned (horizontal/vertical)."""
        pass

    def check_spacing(self, components: list, expected: int) -> bool:
        """Verify equal spacing between components."""
        pass
```

### 4. Librosa "Hands" - Plugin Control
Control plugin parameters programmatically via OSC.

```python
class LibrosaHands:
    """Programmatic control of plugin via OSC."""

    def set_parameter(self, param_id: str, value: float):
        """Set a parameter value."""
        self.osc.send(f"/param/{param_id}", value)

    def inject_signal(self, frequency: float, duration_ms: int):
        """Inject test signal into plugin."""
        self.osc.send("/signal/inject", [frequency, duration_ms])

    def capture_output(self, duration_ms: int) -> np.ndarray:
        """Capture plugin audio output."""
        self.osc.send("/capture/start", duration_ms)
        # Wait for capture complete
        return self._read_captured_audio()

    def test_parameter_affects_audio(
        self,
        param_id: str,
        values: list,
        frequency: float = 440.0
    ) -> dict:
        """
        Test that changing a parameter affects audio output.

        For each value:
        1. Set parameter
        2. Inject test signal
        3. Capture output
        4. Analyze (RMS, spectrum, etc.)
        5. Compare to previous

        Returns: {value: audio_metrics, changed: bool}
        """
        results = []
        for value in values:
            self.set_parameter(param_id, value)
            self.inject_signal(frequency, 1000)
            audio = self.capture_output(1000)
            metrics = self._analyze_audio(audio)
            results.append({"value": value, "metrics": metrics})

        # Check if audio changed across values
        changed = self._detect_change(results)
        return {"parameter": param_id, "results": results, "changed": changed}
```

---

## OODA Phase Breakdown

### OBSERVE Phase
- **Input**: GUI mockup image, spec document, plugin binary
- **Actions**:
  - **Image Analysis** (GLM-4.6v): Extract layout, colors, component positions
  - **Spec Parsing**: Read YAML spec for exact values/names
  - **Parameter Discovery** (OSC): Connect to running plugin, get all params
  - **Color Extraction**: K-means clustering for palette
  - **Reconciliation**: Match image components to spec params
- **Output**: Unified GUI specification + parameter list + color palette

### ORIENT Phase
- **Input**: GUI spec, parameter list
- **Actions**:
  - Query LocalContextTree for similar UI patterns
  - Match components to parameters by name/type
  - Check for gaps (parameters without UI, UI without params)
  - Retrieve working CSS/JS patterns from memory
  - Identify which component type fits each param (knob/slider/switch)
- **Output**: Component mapping + gap report + design suggestions

### DECIDE Phase
- **Input**: GUI spec, parameters, component mapping
- **Actions**:
  - Generate HTML structure with semantic markup
  - Generate CSS with exact colors from palette
  - Generate JavaScript for parameter binding (postMessage pattern)
  - Create test configuration for validation
- **Output**: Complete frontend code (HTML/CSS/JS)

### ACT Phase
- **Input**: Generated frontend code
- **Actions**:
  1. **Apply**: Write files to plugin resources, reload plugin
  2. **Screenshot**: Capture plugin window with grid
  3. **Visual Validation**:
     - Compare to design mockup (SSIM > 0.90)
     - Pick colors and measure ΔE (< 5.0)
     - Measure component positions/sizes
  4. **Audio Validation** (Librosa Hands):
     - For each parameter:
       - Set to min value, inject signal, capture output
       - Set to max value, inject signal, capture output
       - Verify audio changed (parameter affects output)
  5. **Report**: Generate validation report with metrics
- **Output**: Pass/fail + detailed metrics → Loop or complete

---

## File Structure

```
AutoDev/
├── frontend/                      # NEW: Frontend AutoDev module
│   ├── __init__.py
│   ├── observe.py                 # GUI analysis, param discovery
│   ├── orient.py                  # Pattern matching
│   ├── decide.py                  # HTML/CSS/JS generation
│   ├── act.py                     # Testing, validation
│   ├── image_analysis.py          # GLM-4.6v integration
│   ├── param_discovery.py         # OSC parameter reflection
│   ├── screenshot.py              # Win32 window capture
│   ├── measurement.py             # Color picker, pixel tools
│   ├── visual_diff.py             # SSIM comparison
│   └── templates/                 # Component templates
│       ├── knob.html
│       ├── slider.html
│       └── base.css
│
├── autodev_frontend.py            # NEW: Main entry point
├── config/frontend_config.json    # NEW: Frontend settings
└── (existing AutoDev files...)
```

---

## Critical Files to Create/Modify

### New Files:
1. **`frontend/image_analysis.py`** - GLM-4.6v vision API integration
2. **`frontend/param_discovery.py`** - OSC parameter discovery
3. **`frontend/screenshot.py`** - Windows window capture
4. **`frontend/measurement.py`** - Color picker, pixel measurement
5. **`frontend/visual_diff.py`** - SSIM comparison
6. **`autodev_frontend.py`** - Main entry point

### Modify Existing:
1. **`byterover/glm_client.py`** - Add vision API support (GLM-4v)
2. **`config/llm_settings.json`** - Add vision model config
3. **`byterover/local_context.py`** - Add frontend pattern storage

---

## Test Case: DryWetMixerDemo

**Location**: `C:\dev\HeathAudio\demo\DryWetMixerDemo\`

**Perfect for testing**:
- Single parameter: `mix` (0.0-1.0, default 0.5)
- Currently headless (400x200px with text only)
- Working DSP core (convolution reverb)
- Clean JUCE architecture

**Validation criteria**:
1. Generate slider/knob for "mix" parameter
2. Visual match to design mockup (user provides)
3. Audio validation: Changing mix affects dry/wet balance
4. Screenshot similarity > 90%
5. Color accuracy ΔE < 5.0

---

## Implementation Phases

### Phase 1: Foundation (Week 1)
- [ ] Create frontend module structure
- [ ] Integrate GLM-4.6v vision API to glm_client.py
- [ ] Implement basic image analysis (colors, layout)
- [ ] Create component templates (knob, slider, switch)

### Phase 2: Parameter Discovery (Week 1-2)
- [ ] Implement OSC parameter discovery
- [ ] Test with DryWetMixerDemo (single param)
- [ ] Create parameter-to-component mapping
- [ ] Add type inference (knob vs slider vs switch)

### Phase 3: Screenshot & Measurement (Week 2)
- [ ] Implement Win32 window capture (plugin only)
- [ ] Add color picker tool with ΔE calculation
- [ ] Add pixel measurement tool
- [ ] Implement SSIM visual diff

### Phase 4: Code Generation (Week 2-3)
- [ ] Implement HTML generation from GUI spec
- [ ] Implement CSS generation with exact colors
- [ ] Implement JavaScript parameter binding
- [ ] Add JUCE WebView boilerplate

### Phase 5: Audio Testing (Week 3)
- [ ] Integrate librosa osc_control for param sweep
- [ ] Implement audio validation (verify output changes)
- [ ] Add test result analysis
- [ ] Create test report generation

### Phase 6: OODA Integration (Week 3-4)
- [ ] Assemble full OODA loop
- [ ] Add frontend-specific iteration logging
- [ ] Implement pattern learning in context tree
- [ ] Add progress monitoring

### Phase 7: End-to-End Validation (Week 4)
- [ ] Test with DryWetMixerDemo (simple case)
- [ ] Test with AmpBender (complex case)
- [ ] Performance optimization
- [ ] Documentation

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| Visual Similarity | > 90% | SSIM score vs. design mockup |
| Color Accuracy | ΔE < 5.0 | Delta-E from design palette |
| Parameter Coverage | 100% | All parameters functional |
| Audio Validation | 100% | All params affect output |
| Generation Time | < 5 min | Full OODA loop |
| Max Iterations | < 5 | Convergence to acceptable result |

---

## Usage Example

```bash
# Generate frontend from GUI mockup
python autodev_frontend.py \
  --gui-image path/to/mockup.png \
  --plugin-binary path/to/plugin.exe \
  --plugin-name "DryWetMixerDemo"

# User provides:
# 1. GUI mockup image (shows design)
# 2. Backend endpoint list (manual or auto-discovered)

# AutoDev returns:
# 1. HTML/CSS/JS frontend files
# 2. Screenshot comparison
# 3. Audio validation report
# 4. Color accuracy metrics
```

---

## Gap Analysis

### What We Have (Existing)
| Component | Status | Location |
|-----------|--------|----------|
| OODA Loop Framework | ✅ Complete | `AutoDev/ooda/` |
| GLM Client | ✅ Working | `AutoDev/byterover/glm_client.py` |
| Context Memory | ✅ Working | `AutoDev/byterover/local_context.py` |
| Vision API (GLM-4v) | ⚠️ Available | Via MCP tool `mcp__4_5v_mcp__analyze_image` |
| JUCE WebView Pattern | ✅ Reference | `HeathAudio/plugins/AmpBender/` |
| OSC Control | ✅ Exists | `librosa/librosa_test/osc_control.py` |

### What We Need (Gaps)
| Component | Effort | Priority |
|-----------|--------|----------|
| Screenshot Tool (Win32) | Medium | HIGH - Core for validation |
| Color Picker + ΔE | Low | HIGH - Color accuracy |
| Pixel Measurement | Low | MEDIUM - Layout validation |
| YAML Spec Parser | Low | HIGH - Input processing |
| Frontend Code Generator | High | HIGH - Core functionality |
| Audio Validation Logic | Medium | HIGH - Verify controls work |
| Visual Diff (SSIM) | Medium | MEDIUM - Visual validation |
| Component Templates | Medium | MEDIUM - Knobs, sliders, etc. |

### Critical Path
```
Screenshot Tool → Color Picker → YAML Parser → Code Generator → Audio Validation
     ↓                ↓              ↓               ↓                 ↓
   Week 2          Week 2         Week 1         Week 2-3          Week 3
```

### Risk: OSC Plugin Control
**Concern**: Can we actually control the plugin via OSC while it's running in a DAW?

**Mitigation Options**:
1. **JUCE Standalone** - Run plugin as standalone app with OSC enabled
2. **Plugin Host** - Use a lightweight host that exposes OSC
3. **Direct Parameter Access** - Some hosts allow external parameter control
4. **Reaper's OSC** - Reaper DAW has full OSC support for plugin control

**Recommendation**: Test OSC control path FIRST before building rest of system.

---

## Key Challenges & Solutions

| Challenge | Solution |
|-----------|----------|
| **Vision precision** | GLM-4.6v for coarse layout + PIL/OpenCV for exact measurements |
| **Parameter mapping** | User spec provides exact names; OSC discovery validates |
| **Window capture** | Win32 `FindWindow` + `BitBlt` for specific window |
| **Audio timing** | Librosa OSC capture with `.done` markers + 100ms settling |
| **Convergence** | Clear thresholds (SSIM>0.90, ΔE<5) + max 5 iterations |
| **Color accuracy** | K-means extraction from image; validate with ΔE |
| **Component sizing** | Grid overlay on screenshot; pixel measurement tool |
| **OSC control path** | Test FIRST - use JUCE standalone or Reaper with OSC |

### Honest Assessment

**What WILL work well:**
- ✅ Screenshot capture and visual comparison
- ✅ Color extraction and validation (ΔE)
- ✅ Pixel-level measurement
- ✅ Code generation from spec + image
- ✅ Iterative OODA refinement

**What may need iteration:**
- ⚠️ OSC control of plugins in DAWs (depends on host)
- ⚠️ Audio capture timing (may need calibration)
- ⚠️ Vision extraction accuracy (depends on image quality)

**What requires user input:**
- 📋 High-quality GUI mockup image
- 📋 Accurate spec document (names, values)
- 📋 Running plugin for parameter discovery
- 📋 Final visual review

**Known limitations:**
- ❌ Complex animations/transitions may not match perfectly
- ❌ Custom drawn components (meters, graphs) need templates
- ❌ Multi-tab/pane UIs need decomposition

---

## Verification Steps

1. **DryWetMixerDemo Test**:
   ```bash
   # Run on headless plugin
   python autodev_frontend.py \
     --gui-image tests/drywet_design.png \
     --plugin C:\dev\HeathAudio\build\DryWetMixerDemo_VST3.dll \
     --test-mode
   ```

2. **Validate Output**:
   - Check generated HTML/CSS/JS files
   - Review screenshot comparison (SSIM > 0.90)
   - Verify color accuracy (ΔE < 5.0)
   - Confirm parameter affects audio output

3. **Integration Test**:
   - Load plugin in DAW
   - Manually test all controls
   - Verify parameter binding works
   - Check visual match to design

---

## Reference Files

### Key Patterns to Reuse:
- **JUCE WebView**: `C:\dev\HeathAudio\plugins\AmpBender\Source\PluginEditor.cpp`
- **Parameter Binding**: AmpBender's postMessage/evaluateJavascript pattern
- **OSC Testing**: `C:\dev\librosa\librosa_test\osc_control.py`
- **OODA Loop**: Existing AutoDev framework (proven with Mal implementation)

### Component Templates:
- Knob with vertical label
- Slider with value display
- Toggle switch (boolean)
- Dropdown menu (discrete choice)
- LED indicator
- Meter/bar display

---

## Next Steps

### Immediate Actions (GLM-4.7 can start now):

1. **Create frontend module structure**
   ```
   mkdir -p frontend/templates
   touch frontend/__init__.py
   touch frontend/{observe,orient,decide,act}.py
   touch frontend/{screenshot,measurement,image_analysis}.py
   ```

2. **Test OSC control path** (CRITICAL - validates approach)
   - Try connecting to DryWetMixerDemo via OSC
   - Verify we can read parameters
   - Verify we can set parameters
   - Verify we can capture audio output

3. **Create simple GUI mockup** for DryWetMixerDemo
   - 400x200px image
   - Single slider for "mix" parameter
   - Known colors for testing

4. **Implement screenshot tool prototype**
   - Win32 FindWindow by title
   - BitBlt capture
   - Save to file

### First Milestone:
**Generate working frontend for DryWetMixerDemo** with:
- Single slider control
- Visual match to mockup (>90% SSIM)
- Audio validation (mix affects dry/wet balance)
- Screenshot capture working
