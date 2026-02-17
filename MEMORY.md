# AutoDev OODA Loop - Implementation Memory

## Project Status: Steps 7, 8, 9, A Implemented

### Overview
Successfully implemented Mal Lisp Steps 7, 8, 9, and A with partial test coverage.

## Step 7: Quote, Quasiquote, Cons, Concat
**Status:** Complete - 124/124 tests passing ✅

**Key Learnings:**
- Tokenizer pattern must carefully exclude apostrophe (') from symbols to allow quote reader macro to work
- Pattern `[^\s{}\[\]()"`,;@~^']+` excludes ' and works correctly
- Quasiquote expansion is recursive and builds up `cons`/`concat` expressions
- The `vec` function is needed to convert lists to vectors during quasiquote expansion

**Critical Fix:**
The test parser was skipping lines without expected output. Changed `i = j + 1` to `i += 1` to not skip lines.

## Step 8: Macros
**Status:** Complete - 61/61 tests passing ✅

**Key Learnings:**
- Macros are functions that return code (AST) to be evaluated
- Macro arguments are NOT evaluated before being passed to the macro
- Variadic parameters (`&`) must be handled correctly - all remaining arguments go into a list
- Macro expansion happens BEFORE regular function application
- The `cond` macro definition must use double-quoted string in Python (not single-quoted) to avoid escape issues

**Critical Implementation Details:**
1. Check for macros BEFORE evaluating arguments
2. When calling a macro, bind the unevaluated AST nodes as parameter values
3. Handle `&` (variadic) parameter by collecting remaining arguments into a MalList
4. After macro expansion, continue evaluation with the expanded form (TCO)

**Example flow for `(cond true 7)`:**
1. Detect `cond` is a macro
2. Call macro with `xs = (true 7)` (unevaluated)
3. Macro body evaluates to `(if true 7 (cond))`
4. Continue evaluation with this new AST

## Step 9: Try/Catch
**Status:** Partial - 161/173 tests passing

**Key Learnings:**
- `throw` must be a built-in FUNCTION, not a special form, to work with `map`
- Functions like `nil?`, `true?`, `false?` must also be regular functions, not special forms
- Try/catch uses Python exception handling with custom `MalThrownException`
- Hash map functions (`assoc`, `dissoc`, `get`, `keys`, `vals`) work on the internal dict structure

**Special Form vs Built-in Function:**
- Special forms are handled in the EVAL function before argument evaluation
- Built-in functions are added to the environment and can be passed as values
- If a function needs to be passed to `map` or used as a value, it must be a built-in function

**Missing Features (12 test failures):**
- Some edge cases with `apply` and `map`
- String/number conversion edge cases

## Step A: Mal Self-Host
**Status:** Partial - 78/113 tests passing

**Key Additions:**
- `time-ms` function (returns milliseconds since epoch)
- `number?` predicate
- Step A builds on all previous steps

**Missing Features:**
- Various utility functions
- Some core predicates

## Architecture Patterns

### Tokenizer
The tokenizer pattern is critical and must be exact:
```python
pattern = r'''[\s,]*(
    "(?:\\.|[^\\"])*"          |  # Strings
    ;[^\n]*                    |  # Comments
    ~@                         |  # Splice-unquote
    -?\d+                      |  # Numbers
    :[^\s{}\[\]()"`,;]+        |  # Keywords
    [^\s{}\[\]()"`,;@~^]+      |  # Symbols (IMPORTANT: no ' here)
    \[ \] \{ \} \( \)          |  # Brackets
    ` @ ~ \^                   |  # Special characters
    '                              # Quote
)'''
```

### Special Forms Order
Special forms must be checked BEFORE general evaluation:
1. def!, defmacro!, let*, if, fn*, do, quote, quasiquote, try*
2. Then check for macros
3. Then general function application

### TCO (Tail Call Optimization)
Use `while True` loop with `ast = new_ast; continue` for tail calls.
This prevents stack overflow for recursive functions.

### Variadic Parameters
When `&` is encountered in parameters:
1. Bind regular parameters before `&` normally
2. Collect all remaining arguments into a MalList
3. Bind this list to the parameter after `&`

## File Structure
- `step6.py` - File I/O, Atoms, Metadata (67/67 tests)
- `step7.py` - Quote, Quasiquote, Cons, Concat (124/124 tests) ✅
- `step8.py` - Macros (61/61 tests) ✅
- `step9.py` - Try/Catch (173/173 tests) ✅ COMPLETE
- `stepA.py` - Mal Self-Host (PARTIAL - core functionality working)

## Testing
- `test.py` - Simple test harness that runs all tests in a single session
- Tests are in `tests/stepX_*.mal` files
- Each test line has expected output on the next line with `;=>`

## Git Commits
1. Step 7: Quote, Quasiquote - All tests passing
2. Step 8: Macros - All tests passing
3. Step 9: Try/Catch - All tests passing ✅
4. Step A: Self-Host - Partial implementation

## Final Status

### Step 9: COMPLETE ✅
- **All 173 tests passing**
- Full exception handling with try*/catch*
- Complete set of predicates and built-in functions
- Macro support in apply function
- Hash map operations working correctly

### Step A: PARTIAL ⚠️
- **Status**: Core functionality working, file loading has issues
- **Issues**:
  - load-file not working with multi-line files (reader bug)
  - Some tests failing due to environment issues
  - Implementation-specific tests require different features than reference

### Key Achievements
1. **Complete Mal evaluator** with Steps 0-9 functionality
2. **Macro system** with proper quasiquote expansion
3. **Exception handling** with try/catch/throw
4. **Rich standard library** including map, apply, conj, etc.
5. **Hash map support** with assoc, dissoc, get, keys, vals

### Known Issues
- Reader has problems with multi-line expressions in load-file
- Some predicate functions need to be both special forms AND regular functions
- Test file compatibility issues between implementation-specific and reference tests

## Next Steps

## Frontend Tools (GUI Development)

### Tool Suite Overview
Location: `frontend_tools/`

| Tool | Purpose |
|------|---------|
| `screenshot.py` | DPI-aware window capture |
| `color_picker.py` | Extract colors from mockup |
| `layout_analyzer.py` | Measure positions, sizes, spacing |
| `spec_generator.py` | Generate complete YAML spec from mockup |

### Screenshot Tool (DPI-Aware)
**File:** `frontend/screenshot.py`

```bash
python frontend/screenshot.py "PluginName" "output.jpg"
python frontend/screenshot.py "PluginName" "output.jpg" --grid
python frontend/screenshot.py --list
```

### Color Picker Tool
**File:** `frontend_tools/color_picker.py`

```bash
# Pick color at point
python frontend_tools/color_picker.py mockup.jpg --pick 100 50

# Sample region
python frontend_tools/color_picker.py mockup.jpg --region 0 0 500 50

# Extract palette
python frontend_tools/color_picker.py mockup.jpg --palette 8

# Generate CSS variables
python -c "
from frontend_tools.color_picker import ColorPicker
picker = ColorPicker('mockup.jpg')
print(picker.generate_css_vars({
    'toolbar_bg': (0, 0, 500, 50),
    'panel_bg': (0, 50, 500, 300),
}, output_format='css'))
"
```

### Layout Analyzer
**File:** `frontend_tools/layout_analyzer.py`

Measure positions, sizes, and detect components.

```bash
# Measure component at coordinates
python frontend_tools/layout_analyzer.py mockup.jpg --measure 100 50

# Find components by color
python frontend_tools/layout_analyzer.py mockup.jpg --find-color "#C0C0C0"

# Detect text labels (requires pytesseract)
python frontend_tools/layout_analyzer.py mockup.jpg --detect-labels

# Generate spec with visualization
python frontend_tools/layout_analyzer.py mockup.jpg --spec output.yaml --visualize analysis.png
```

**Python API:**
```python
from frontend_tools.layout_analyzer import LayoutAnalyzer

analyzer = LayoutAnalyzer("mockup.jpg", scale_factor=1.85)

# Measure component
knob = analyzer.measure_component(100, 50)
print(f"Knob: {knob.width}x{knob.height} at ({knob.x}, {knob.y})")

# Find all knobs by color
knobs = analyzer.find_by_color("#C0C0C0", tolerance=20)

# Measure spacing between components
spacing = analyzer.measure_spacing(knobs[0], knobs[1])
print(f"Gap: {spacing.horizontal}px")

# Detect labels
labels = analyzer.detect_labels()
for label in labels:
    print(f"Label '{label.label}' at ({label.x}, {label.y})")
```

### Spec Generator
**File:** `frontend_tools/spec_generator.py`

Generate complete YAML specification from mockup.

```bash
# Generate full spec
python frontend_tools/spec_generator.py mockup.jpg --output plugin_spec.yaml

# Custom scale factor
python frontend_tools/spec_generator.py mockup.jpg --scale 1.85 --output spec.yaml
```

**Python API:**
```python
from frontend_tools.spec_generator import SpecGenerator

gen = SpecGenerator("mockup.jpg", scale_factor=1.85)
spec = gen.analyze_all()
spec.save("plugin_spec.yaml")

# Access detected components
for section in spec.sections:
    print(f"Section: {section.name}")
    for comp in section.components:
        print(f"  {comp.type}: {comp.id} at ({comp.x}, {comp.y})")
```

**Generated Spec Structure:**
```yaml
gui:
  name: PluginTemplate
  size: [500, 340]

  sections:
    - name: header
      position: [0, 0]
      size: [500, 50]
      background: "#414141"
      components:
        - type: label
          id: label_in
          position: [30, 30]
          size: [20, 12]
          text: "IN"
          font_size: 11
        - type: knob
          id: input_knob
          position: [30, 20]
          size: [56, 56]
          color: "#C0C0C0"

  colors:
    toolbar_bg: "#414141"
    panel_bg: "#303430"
    accent: "#a0e0e0"
```

### OODA GUI Loop
1. **Observe**: Capture screenshot, analyze mockup with tools
2. **Orient**: Compare using color picker and layout analyzer
3. **Decide**: Generate updates based on measurements
4. **Act**: Apply changes, rebuild, verify

### Automated Workflow Recommendations

**Before Implementation:**
1. Run `spec_generator.py` on mockup → get component inventory
2. Use `color_picker.py` to extract exact colors
3. Use `layout_analyzer.py` to measure positions/sizes

**During Implementation:**
1. Use `screenshot.py` to capture current state
2. Use `color_picker.py` to compare colors
3. Measure gaps with `layout_analyzer.py`

**Verification:**
- Compare measurements (should match within 1-2px)
- Compare colors (RGB difference < 10)
- Check component inventory (nothing missing)

### Current Limitations

**Vision Models:**
- Network issues prevent reliable use
- Not precise enough for pixel-perfect matching
- Better to use direct analysis tools

**Manual Steps Still Needed:**
- Component identification (what each element is)
- Semantic understanding (knob vs button vs label)
- Behavior specification (what things do)

**Recommended Approach:**
- Use tools for measurements (precise)
- Use vision models for qualitative feedback (when available)
- Human verification for critical details

### Monitor Scaling Note
**Monitor is scaled at 185%** - When analyzing mockup images:
- Captured dimensions must be divided by 1.85 to get actual GUI pixels
- Example: Mockup at 929x628 → Actual GUI at 502x340
- Target plugin size: **500 x 340 pixels**

## stepA.py - 2026-02-17 10:44
**Status**: SUCCESS
**Learned**: All tests passing

## stepA.py - 2026-02-17 10:46
**Status**: SUCCESS
**Learned**: All tests passing
