"""
AutoDev Frontend - Autonomous VST Plugin GUI Generation

This module implements the OODA loop for generating JUCE WebView frontends
from GUI mockups and specification documents.

Components:
- observe.py: Image analysis, parameter discovery
- orient.py: Pattern matching, component mapping
- decide.py: HTML/CSS/JS code generation
- act.py: Testing, validation, screenshots

Tools:
- screenshot.py: Win32 window capture
- measurement.py: Color picker, pixel measurement
- image_analysis.py: GLM-4.6v vision integration
- visual_diff.py: SSIM comparison
"""

__version__ = "0.1.0"
