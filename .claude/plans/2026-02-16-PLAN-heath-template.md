# HeathAudioPluginTemplate - Implementation Plan
**For:** GLM-4.7 (Sonnet)
**Created:** 2026-02-16
**Source:** Extracted from AmpBender plugin

---

## Overview

Create a reusable JUCE plugin template with WebView-based UI that can be cloned from GitHub for new plugin projects.

**Target GUI Size:** 500 x 340 pixels (actual)
**Important:** NO manual resizing - only zoom parameter changes the scale.

---

## Phase 1: Project Setup

### 1.1 Create Template Directory Structure
```
C:\dev\HeathAudio\templates\HeathAudioPluginTemplate\
├── Source/
│   ├── PluginProcessor.h
│   ├── PluginProcessor.cpp
│   ├── PluginEditor.h
│   ├── PluginEditor.cpp
│   ├── ui/public/
│   │   ├── index.html
│   │   ├── styles.css
│   │   └── app.js
│   └── resources/
│       └── logo.svg
├── CMakeLists.txt
├── README.md
└── TEMPLATE_CONFIG.yaml
```

### 1.2 Create TEMPLATE_CONFIG.yaml
Configuration file for per-project customization:
```yaml
plugin_name: "MyPlugin"
manufacturer: "Heath Audio"
version: "1.0.0"
plugin_id: "HTHP"  # 4-char ID

# Colors
accent_color: "#a0e0e0"  # Cyan

# Zoom levels
zoom_levels: [0.75, 1.0, 1.25]
default_zoom: 1.0
```

---

## Phase 2: Extract Backend (PluginProcessor)

### 2.1 Copy and Modify PluginProcessor.h

**From:** `C:\dev\HeathAudio\plugins\AmpBender\Source\PluginProcessor.h`

**Keep:**
- Basic AudioProcessor structure
- Atomic meter values
- CPU usage tracking
- Parameter layout pattern

**Remove:**
- All DSP code (circuits, convolution, routing)
- OSC server
- IR loading
- Autogain

**Add template parameters:**
```cpp
// Template parameters (always included)
AudioParameterFloat* inputGainParam;   // -60 to 6 dB
AudioParameterFloat* outputGainParam;  // -60 to 6 dB
AudioParameterChoice* oversampleParam; // 1x, 2x, 4x, 8x
AudioParameterChoice* zoomParam;       // 75%, 100%, 125%, 150%, 200%
```

### 2.2 Copy and Modify PluginProcessor.cpp

**Meter accessors (keep verbatim):**
```cpp
float getInputLevel() const { return inputLevel.load(); }
float getOutputLevel() const { return outputLevel.load(); }
float getInputPeak() const { return inputPeak.load(); }
float getOutputPeak() const { return outputPeak.load(); }
float getCpuUsage() const { return cpuUsage.load(); }
```

**Parameter creation (simplify):**
```cpp
addParameter(inputGainParam = new AudioParameterFloat(
    "input_gain", "IN", -60.0f, 6.0f, 0.0f));
addParameter(outputGainParam = new AudioParameterFloat(
    "output_gain", "OUT", -60.0f, 6.0f, 0.0f));
addParameter(oversampleParam = new AudioParameterChoice(
    "oversampling", "OS", StringArray{"1x", "2x", "4x", "8x"}, 0));
addParameter(zoomParam = new AudioParameterChoice(
    "zoom", "ZOOM", StringArray{"75%", "100%", "125%"}, 1));
```

**Preset save/load (generic):**
```cpp
void getStateInformation(MemoryBlock& destData) override {
    // Standard XML state save
}

void setStateInformation(const void* data, int sizeInBytes) override {
    // Standard XML state load
}
```

---

## Phase 3: Extract Frontend (PluginEditor)

### 3.1 Copy and Rename LookAndFeel Class

**From:** `AmpBenderLookAndFeel` in PluginEditor.h

**Changes:**
- Rename to `HeathAudioLookAndFeel`
- Replace gold colors with configurable accent color
- Keep all button and title bar drawing logic

```cpp
class HeathAudioLookAndFeel : public LookAndFeel_V4 {
public:
    HeathAudioLookAndFeel(const Colour& accentColour) {
        // Use accentColour instead of hardcoded gold
        this->accentColour = accentColour;
    }

    Colour accentColour;
    Colour backgroundDark = Colour(0xff202020);
    Colour backgroundMedium = Colour(0xff404040);
    // ... rest of LookAndFeel implementation
};
```

### 3.2 Copy and Modify WebView Setup

**Keep:**
- WebBrowserComponent::Options setup
- Resource provider for local files
- Native function registration pattern

**Native functions to implement:**

```cpp
// Zoom control (IMPORTANT - only way to resize)
.withNativeFunction("setZoom", [this](const auto& args, auto complete) {
    if (args.size() > 0) {
        float newZoom = (float)args[0];
        getProcessor().zoomParam->setValueNotifyingHost(newZoom);
        // Trigger resize via setSize(), not manual drag
    }
    complete({});
})

// Get plugin info
.withNativeFunction("getPluginInfo", [](const auto& args, auto complete) {
    DynamicObject::Ptr info = new DynamicObject();
    info->setProperty("name", "HeathAudioPlugin");
    info->setProperty("version", "1.0.0");
    complete({info.get()});
})

// Window resize via zoom (internal use)
.withNativeFunction("requestWindowResize", [this](const auto& args, auto complete) {
    if (args.size() >= 2) {
        int baseWidth = (int)args[0];
        int baseHeight = (int)args[1];
        float zoom = getProcessor().zoomParam->getValue();

        // Calculate actual size based on zoom
        int actualWidth = (int)(baseWidth * zoom);
        int actualHeight = (int)(baseHeight * zoom);

        setSize(actualWidth, actualHeight);
    }
    complete({});
})
```

### 3.3 Disable Manual Resizing

**CRITICAL:** Add constraints to prevent manual drag-resizing:

```cpp
// In PluginEditor constructor
setResizable(false, false);  // NO manual resizing
setResizeLimits(500, 340, 500, 340);  // Fixed base size

// Resize only happens via zoom parameter
void updateZoom() {
    float zoom = processorRef.zoomParam->getValue();
    int width = (int)(500 * zoom);
    int height = (int)(340 * zoom);
    setSize(width, height);
}
```

### 3.4 Timer Callback for Meters

**Keep pattern, simplify:**

```cpp
void timerCallback() override {
    float inputDb = processorRef.getInputLevel();
    float outputDb = processorRef.getOutputLevel();
    float inputPeak = processorRef.getInputPeak();
    float outputPeak = processorRef.getOutputPeak();
    float cpu = processorRef.getCpuUsage();

    String js = String::formatted(
        "if (typeof window.updateMeters === 'function') { "
        "window.updateMeters(%f, %f, %f, %f, %f); }",
        inputDb, outputDb, inputPeak, outputPeak, cpu);

    webView->evaluateJavascript(js, nullptr);
}
```

---

## Phase 4: Extract UI (HTML/CSS/JS)

### 4.1 Copy HTML Structure

**From:** `C:\dev\HeathAudio\plugins\AmpBender\Source\ui\public\index.html`

**Keep:**
- Header bar with left/center/right sections
- Meter containers on left/right edges
- About overlay structure

**Remove:**
- AmpBender-specific panels
- Circuit mod controls
- Patchbay interface

**Simplify to template:**

```html
<!-- Header bar -->
<div class="toolbar">
  <div class="toolbar-left">
    <div class="knob-container">
      <div class="knob" id="input-knob"></div>
      <span class="knob-label">IN</span>
    </div>
    <div class="preset-dropdown">
      <button class="custom-dropdown-toggle" id="preset-btn">PRESET</button>
      <div class="toolbar-dropdown" id="preset-menu"></div>
    </div>
    <button class="icon-btn" id="save-btn" title="Save Preset"></button>
    <button class="icon-btn" id="load-btn" title="Load Preset"></button>
  </div>

  <div class="toolbar-center">
    <button class="logo-btn" id="about-btn">HEATH AUDIO</button>
  </div>

  <div class="toolbar-right">
    <div class="os-dropdown">
      <button class="custom-dropdown-toggle" id="os-btn">OS 1x</button>
      <div class="toolbar-dropdown" id="os-menu">
        <div data-value="0">1x</div>
        <div data-value="1">2x</div>
        <div data-value="2">4x</div>
        <div data-value="3">8x</div>
      </div>
    </div>
    <div class="zoom-dropdown">
      <button class="custom-dropdown-toggle" id="zoom-btn">100%</button>
      <div class="toolbar-dropdown" id="zoom-menu">
        <div data-value="0.75">75%</div>
        <div data-value="1.0">100%</div>
        <div data-value="1.25">125%</div>
      </div>
    </div>
    <div class="knob-container">
      <div class="knob" id="output-knob"></div>
      <span class="knob-label">OUT</span>
    </div>
  </div>
</div>

<!-- Main panel with meters -->
<div class="main-panel">
  <div class="meter-container left-meter">
    <div class="meter-scale" id="input-meter-scale"></div>
  </div>

  <div class="center-panel">
    <!-- Plugin-specific content goes here -->
    <div class="placeholder-content">
      <p>Plugin controls go here</p>
    </div>
  </div>

  <div class="meter-container right-meter">
    <div class="meter-scale" id="output-meter-scale"></div>
  </div>
</div>

<!-- About overlay -->
<div class="about-overlay" id="about-overlay">
  <div class="about-dialog">
    <h1 class="about-title">HEATH AUDIO</h1>
    <p class="about-version" id="about-version">v1.0.0</p>
    <p class="about-copyright">© 2025 Heath Audio</p>
  </div>
</div>
```

### 4.2 Copy CSS with Configurable Colors

**From:** `C:\dev\HeathAudio\plugins\AmpBender\Source\ui\public\styles.css`

**Add CSS custom properties for theming:**

```css
:root {
  /* Configurable accent color */
  --accent-color: #a0e0e0;
  --accent-dark: #204040;

  /* Backgrounds */
  --bg-primary: #202020;
  --bg-secondary: #404040;
  --bg-tertiary: #606060;

  /* Text */
  --text-primary: #e0e0e0;
  --text-secondary: #a0a0a0;
  --text-disabled: #808080;
}

/* Rest of CSS using these variables */
.toolbar {
  background: var(--bg-secondary);
}

.accent-border {
  border-color: var(--accent-color);
}
```

### 4.3 Copy JavaScript with Generic Functions

**From:** `C:\dev\HeathAudio\plugins\AmpBender\Source\ui\public\app.js`

**Keep patterns:**
- Knob rendering and interaction
- Dropdown menus
- Meter updates
- Parameter binding via native functions

**Simplify for template:**

```javascript
// Zoom handling
function setZoom(scale) {
  window.chrome.webview.postMessage({
    type: 'setZoom',
    value: scale
  });
}

// Request resize (only allowed via zoom)
function resizeFromZoom() {
  const zoom = parseFloat(document.body.dataset.zoom || '1.0');
  window.chrome.webview.postMessage({
    type: 'requestWindowResize',
    width: 500,
    height: 340
  });
}

// Meter updates (called from C++)
window.updateMeters = function(inputDb, outputDb, inPeak, outPeak, cpu) {
  updateMeter('input-meter', inputDb, inPeak);
  updateMeter('output-meter', outputDb, outPeak);
};

// Preset menu
function loadPreset(index) {
  window.chrome.webview.postMessage({
    type: 'loadPreset',
    index: index
  });
}

// About dialog
function showAbout() {
  document.getElementById('about-overlay').classList.add('visible');
}
```

---

## Phase 5: Build Configuration

### 5.1 Create CMakeLists.txt

**Based on:** AmpBender's CMakeLists.txt

**Key changes:**
- Remove AmpBender-specific source files
- Add TEMPLATE_CONFIG.yaml as build-time dependency
- Make plugin name/version configurable

```cmake
cmake_minimum_required(VERSION 3.20)
project(HeathAudioPluginTemplate VERSION 1.0.0)

# Read template config
# (optional: parse yaml to set plugin name, etc.)

add_juce_plugin(${PROJECT_NAME}
    PLUGIN_NAME "${PROJECT_NAME}"
    COMPANY_NAME "Heath Audio"
    COMPANY_WEBSITE "https://heathaudio.com"
    COMPANY_EMAIL "contact@heathaudio.com"

    VERSION ${PROJECT_VERSION}

    # Source files
    SOURCE_FILES
        Source/PluginProcessor.cpp
        Source/PluginEditor.cpp

    # UI as binary data
    BINARY_DATA
        Source/ui/public/index.html
        Source/ui/public/styles.css
        Source/ui/public/app.js
)
```

---

## Phase 6: Testing

### 6.1 Test Header Functionality
- [ ] IN/OUT knobs change parameters
- [ ] Preset dropdown shows factory presets
- [ ] Save button opens file dialog
- [ ] Load button opens file dialog
- [ ] OS dropdown changes oversampling
- [ ] Zoom dropdown resizes window (NO manual resize!)
- [ ] About button opens overlay

### 6.2 Test Meters
- [ ] Input meter responds to audio
- [ ] Output meter responds to audio
- [ ] Peak hold works
- [ ] dB scale is correct (-60 to +6)

### 6.3 Test Zoom Behavior
- [ ] 75%: 375 x 255 px
- [ ] 100%: 500 x 340 px
- [ ] 125%: 625 x 425 px
- [ ] Manual drag-resize does NOT work

### 6.4 Test Preset System
- [ ] Save preset creates XML file
- [ ] Load preset restores parameters
- [ ] State survives DAW session save/load

---

## Phase 7: Documentation and GitHub

### 7.1 Create README.md

```markdown
# HeathAudioPluginTemplate

A reusable JUCE plugin template with WebView UI.

## Features
- Fixed 500x340 base size, scalable via zoom (75%-200%)
- Input/output meters with dB scales
- Preset management
- Oversampling options
- HeathAudio LookAndFeel

## Creating a New Plugin

1. Clone this template
2. Edit TEMPLATE_CONFIG.yaml with your plugin details
3. Add plugin-specific parameters to PluginProcessor
4. Design center panel in index.html
5. Build with CMake

## Building

```bash
cmake -B build
cmake --build build
```
```

### 7.2 Push to GitHub

```bash
cd C:\dev\HeathAudio\templates\HeathAudioPluginTemplate
git init
git add .
git commit -m "Initial template release"
gh repo create HeathAudioPluginTemplate --public --source=.
git push -u origin main
```

---

## Implementation Order

1. **Phase 1**: Create directory structure and config
2. **Phase 2**: Backend (PluginProcessor)
3. **Phase 3**: Frontend infrastructure (PluginEditor, LookAndFeel)
4. **Phase 4**: UI files (HTML/CSS/JS)
5. **Phase 5**: Build config (CMakeLists.txt)
6. **Phase 6**: Test all functionality
7. **Phase 7**: Document and push to GitHub

---

## Key Constraints

- **NO manual resizing** - Window size only changes via zoom parameter
- **Base size: 500 x 340** - Always scale from this baseline
- **Colors configurable** - Use TEMPLATE_CONFIG.yaml
- **Plugin-specific content** - Goes in center panel placeholder only

---

## Success Criteria

- [ ] Builds without errors
- [ ] Loads in DAW (Reaper, Ableton, Bitwig)
- [ ] All header controls work
- [ ] Meters display audio levels
- [ ] Zoom resizes correctly (75%, 100%, 125%, 150%, 200%)
- [ ] Manual resize is blocked
- [ ] Can be cloned for new plugin project
