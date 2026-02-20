"""
Preview Server - Live Preview for HTML/CSS/JS with Hot Reload

Serves UI files and notifies browser to reload on file changes.
Supports visual editor mode for CSS editing.

Usage:
    python -m translation_layer preview <directory>
    python -m translation_layer preview <directory> --editor
"""

import argparse
import asyncio
import glob
import json
import os
import re
import threading
import webbrowser
from http.server import HTTPServer, SimpleHTTPRequestHandler
from pathlib import Path
from typing import Set, Optional

import websockets
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler, FileModifiedEvent


# Global state
_ws_clients: Set[websockets.WebSocketServerProtocol] = set()
_editor_mode: bool = False
_css_file_path: Optional[str] = None


# Editor injection script - adds CSS panel and click-to-select functionality
EDITOR_SCRIPT = '''
<style>
#editor-panel {
    position: fixed;
    right: 0;
    top: 0;
    width: 350px;
    height: 100vh;
    background: #1e1e1e;
    border-left: 1px solid #444;
    display: flex;
    flex-direction: column;
    font-family: 'Consolas', 'Monaco', monospace;
    z-index: 9999;
    color: #e0e0e0;
}
.editor-header {
    background: #333;
    padding: 10px 15px;
    color: #a0e0e0;
    font-weight: bold;
    display: flex;
    justify-content: space-between;
    align-items: center;
    border-bottom: 1px solid #444;
}
.editor-header span {
    font-size: 14px;
}
#editor-close {
    background: none;
    border: none;
    color: #a0a0a0;
    font-size: 20px;
    cursor: pointer;
    padding: 0 5px;
}
#editor-close:hover {
    color: #fff;
}
.editor-selector {
    background: #252525;
    padding: 8px 15px;
    border-bottom: 1px solid #444;
    font-size: 12px;
    color: #a0e0e0;
}
.editor-content {
    flex: 1;
    display: flex;
    flex-direction: column;
    overflow: hidden;
}
#css-editor {
    width: 100%;
    height: 100%;
    background: #1e1e1e;
    color: #e0e0e0;
    border: none;
    padding: 10px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 13px;
    resize: none;
    outline: none;
    line-height: 1.5;
}
.editor-footer {
    background: #333;
    padding: 10px 15px;
    display: flex;
    gap: 10px;
    border-top: 1px solid #444;
}
.editor-footer button {
    background: #404040;
    color: #e0e0e0;
    border: none;
    padding: 8px 16px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
}
.editor-footer button:hover {
    background: #505050;
}
#editor-apply {
    background: #2a5a5a;
    color: #a0e0e0;
}
#editor-apply:hover {
    background: #3a6a6a;
}
.editor-highlight {
    outline: 2px solid #a0e0e0 !important;
    outline-offset: 2px;
    background-color: rgba(160, 224, 224, 0.1) !important;
}
.editor-hover-highlight {
    outline: 1px dashed #a0e0e0 !important;
    outline-offset: 1px;
}
/* Control buttons */
.editor-btn {
    position: fixed;
    background: #333;
    color: #a0e0e0;
    border: 1px solid #444;
    padding: 5px 10px;
    border-radius: 4px;
    cursor: pointer;
    font-size: 12px;
    z-index: 9998;
    font-family: 'Arial', sans-serif;
}
.editor-btn:hover {
    background: #444;
}
.editor-btn.active {
    background: #2a5a5a;
}
#editor-toggle {
    left: 10px;
    top: 10px;
}
#grid-toggle {
    left: 120px;
    top: 10px;
}
#css-toggle {
    left: 170px;
    top: 10px;
}
#zoom-indicator {
    position: fixed;
    left: 10px;
    top: 40px;
    background: #333;
    color: #a0e0e0;
    padding: 5px 10px;
    border-radius: 4px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    z-index: 9998;
}
/* Resize handles */
.resize-handle {
    position: absolute;
    width: 10px;
    height: 10px;
    background: #a0e0e0;
    border: 1px solid #fff;
    border-radius: 2px;
    z-index: 10001;
    box-shadow: 0 0 3px rgba(0,0,0,0.5);
}
.resize-handle.nw { top: -5px; left: -5px; cursor: nwse-resize; }
.resize-handle.ne { top: -5px; right: -5px; cursor: nesw-resize; }
.resize-handle.sw { bottom: -5px; left: -5px; cursor: nesw-resize; }
.resize-handle.se { bottom: -5px; right: -5px; cursor: nwse-resize; }
.resize-handle.n { top: -5px; left: 50%; transform: translateX(-50%); cursor: ns-resize; }
.resize-handle.s { bottom: -5px; left: 50%; transform: translateX(-50%); cursor: ns-resize; }
.resize-handle.e { right: -5px; top: 50%; transform: translateY(-50%); cursor: ew-resize; }
.resize-handle.w { left: -5px; top: 50%; transform: translateY(-50%); cursor: ew-resize; }
/* Size indicator */
#size-indicator {
    position: fixed;
    bottom: 10px;
    left: 10px;
    background: #333;
    color: #a0e0e0;
    padding: 5px 10px;
    border-radius: 4px;
    font-family: 'Consolas', 'Monaco', monospace;
    font-size: 12px;
    z-index: 9998;
    display: none;
}
#size-indicator.visible {
    display: block;
}
/* Grid overlay */
#grid-overlay {
    position: fixed;
    top: 0;
    left: 0;
    width: 100%;
    height: 100%;
    pointer-events: none;
    z-index: 9997;
    display: none;
}
#grid-overlay.visible {
    display: block;
}
.grid-line {
    position: absolute;
    border-color: rgba(255, 50, 50, 0.6);
    border-style: dashed;
    border-width: 0;
}
.grid-line.h {
    width: 100%;
    border-top-width: 1px;
}
.grid-line.v {
    height: 100%;
    border-left-width: 1px;
}
/* Plugin container wrapper for zoom */
#plugin-wrapper {
    transform-origin: center center;
    transition: transform 0.1s ease;
}
</style>

<div id="editor-panel">
    <div class="editor-header">
        <span>CSS Editor <small style="color:#666">(auto-apply on drag/resize)</small></span>
        <button id="editor-close">&times;</button>
    </div>
    <div class="editor-selector" id="current-selector">Click an element to inspect</div>
    <div class="editor-content">
        <textarea id="css-editor" placeholder="CSS rules will appear here..."></textarea>
    </div>
    <div class="editor-footer">
        <button id="editor-apply">Apply</button>
        <button id="editor-reset">Reset</button>
        <button id="editor-undo" title="Ctrl+Z">Undo</button>
        <button id="editor-redo" title="Ctrl+Y">Redo</button>
    </div>
</div>

<button id="editor-toggle" class="editor-btn">Inspect</button>
<button id="grid-toggle" class="editor-btn">Grid</button>
<button id="css-toggle" class="editor-btn">CSS</button>
<div id="zoom-indicator">Zoom: 100% | F=reset</div>
<div id="size-indicator"></div>
<div id="grid-overlay"></div>

<script>
(function() {
    const ws = new WebSocket('ws://localhost:8765');
    let inspectMode = false;
    let gridVisible = false;
    let currentSelector = null;
    let originalCss = '';
    let selectedElement = null;

    // Undo/Redo history
    let cssHistory = [];
    let historyIndex = -1;
    const maxHistory = 50;

    // Zoom state
    let currentZoom = 1.0;
    const zoomStep = 0.1;
    const minZoom = 0.5;
    const maxZoom = 3.0;
    let lastMouseX = 0;
    let lastMouseY = 0;

    // Track mouse position for zoom-to-mouse
    document.addEventListener('mousemove', function(e) {
        lastMouseX = e.clientX;
        lastMouseY = e.clientY;
    });

    // Drag/Resize state
    let isDragging = false;
    let isResizing = false;
    let resizeHandle = null;
    let startX, startY;
    let startLeft, startTop, startWidth, startHeight;
    let dragEl = null;
    let resizeEl = null;

    // Elements
    const panel = document.getElementById('editor-panel');
    const toggle = document.getElementById('editor-toggle');
    const gridToggle = document.getElementById('grid-toggle');
    const cssToggle = document.getElementById('css-toggle');
    const editor = document.getElementById('css-editor');
    const selectorDisplay = document.getElementById('current-selector');
    const applyBtn = document.getElementById('editor-apply');
    const resetBtn = document.getElementById('editor-reset');
    const undoBtn = document.getElementById('editor-undo');
    const redoBtn = document.getElementById('editor-redo');
    const closeBtn = document.getElementById('editor-close');
    const sizeIndicator = document.getElementById('size-indicator');
    const zoomIndicator = document.getElementById('zoom-indicator');
    const gridOverlay = document.getElementById('grid-overlay');

    // === ZOOM FUNCTIONALITY ===
    // Ctrl+scroll to zoom (centers on mouse position)
    document.addEventListener('wheel', function(e) {
        if (e.ctrlKey) {
            e.preventDefault();
            const container = document.querySelector('.plugin-container');
            if (!container) return;

            // Get mouse position relative to container
            const rect = container.getBoundingClientRect();
            const mouseX = lastMouseX - rect.left;
            const mouseY = lastMouseY - rect.top;

            // Update zoom level
            if (e.deltaY < 0) {
                currentZoom = Math.min(maxZoom, currentZoom + zoomStep);
            } else {
                currentZoom = Math.max(minZoom, currentZoom - zoomStep);
            }

            // Apply zoom with transform-origin at mouse position
            container.style.transformOrigin = `${mouseX}px ${mouseY}px`;
            container.style.transform = `scale(${currentZoom})`;
            zoomIndicator.textContent = `Zoom: ${Math.round(currentZoom * 100)}% | F=reset`;
            updateGridPosition();
        }
    }, { passive: false });

    // 'F' to reset zoom
    document.addEventListener('keydown', function(e) {
        if (e.key === 'f' && !e.ctrlKey && !e.shiftKey && !e.altKey && document.activeElement !== editor) {
            currentZoom = 1.0;
            const container = document.querySelector('.plugin-container');
            if (container) {
                container.style.transform = 'scale(1)';
                container.style.transformOrigin = 'center center';
            }
            zoomIndicator.textContent = 'Zoom: 100% | F=reset';
            updateGridPosition();
        }
    });

    // === GRID FUNCTIONALITY ===
    function createGrid() {
        gridOverlay.innerHTML = '';
        const container = document.querySelector('.plugin-container');
        if (!container) return;

        const rect = container.getBoundingClientRect();
        const w = rect.width;
        const h = rect.height;

        // Grid divisions: 1/2, 1/4, 1/8
        const divs = [2, 4, 8];

        divs.forEach(div => {
            // Vertical lines
            for (let i = 1; i < div; i++) {
                const line = document.createElement('div');
                line.className = 'grid-line v';
                line.style.left = (rect.left + (w * i / div)) + 'px';
                line.style.top = rect.top + 'px';
                line.style.height = h + 'px';
                gridOverlay.appendChild(line);
            }
            // Horizontal lines
            for (let i = 1; i < div; i++) {
                const line = document.createElement('div');
                line.className = 'grid-line h';
                line.style.left = rect.left + 'px';
                line.style.top = (rect.top + (h * i / div)) + 'px';
                line.style.width = w + 'px';
                gridOverlay.appendChild(line);
            }
        });
    }

    function updateGridPosition() {
        if (gridVisible) {
            createGrid();
        }
    }

    gridToggle.addEventListener('click', function() {
        gridVisible = !gridVisible;
        gridToggle.classList.toggle('active', gridVisible);
        if (gridVisible) {
            createGrid();
            gridOverlay.classList.add('visible');
        } else {
            gridOverlay.classList.remove('visible');
        }
    });

    // === CSS PANEL TOGGLE ===
    cssToggle.addEventListener('click', function() {
        const isVisible = panel.style.display !== 'none';
        panel.style.display = isVisible ? 'none' : 'flex';
        cssToggle.classList.toggle('active', !isVisible);
    });

    // === INSPECT MODE ===
    toggle.addEventListener('click', function() {
        inspectMode = !inspectMode;
        toggle.classList.toggle('active', inspectMode);
        toggle.textContent = inspectMode ? 'Inspect ON' : 'Inspect';
        document.body.style.cursor = inspectMode ? 'crosshair' : 'default';
        if (!inspectMode) {
            clearHighlight();
            clearHoverHighlight();
            removeResizeHandles();
            selectedElement = null;
        }
    });

    // Close panel (X button)
    closeBtn.addEventListener('click', function() {
        panel.style.display = 'none';
        cssToggle.classList.remove('active');
    });

    // === UNDO/REDO ===
    function saveToHistory() {
        // Truncate any redo history
        cssHistory = cssHistory.slice(0, historyIndex + 1);
        cssHistory.push({
            selector: currentSelector,
            css: editor.value
        });
        // Always set index to last position
        historyIndex = cssHistory.length - 1;
        // Trim if too long
        if (cssHistory.length > maxHistory) {
            cssHistory.shift();
            historyIndex = cssHistory.length - 1;
        }
    }

    function undo() {
        console.log('[Undo] historyIndex:', historyIndex, 'history length:', cssHistory.length);
        if (historyIndex > 0) {
            historyIndex--;
            const state = cssHistory[historyIndex];
            if (state && state.css) {
                editor.value = state.css;
                currentSelector = state.selector;
                selectorDisplay.textContent = currentSelector || 'No selection';
                applyCssWithoutSave(state.css);
                console.log('[Undo] Restored state', historyIndex);
            }
        } else {
            console.log('[Undo] No more history to undo');
        }
    }

    function redo() {
        console.log('[Redo] historyIndex:', historyIndex, 'history length:', cssHistory.length);
        if (historyIndex < cssHistory.length - 1) {
            historyIndex++;
            const state = cssHistory[historyIndex];
            if (state && state.css) {
                editor.value = state.css;
                currentSelector = state.selector;
                selectorDisplay.textContent = currentSelector || 'No selection';
                applyCssWithoutSave(state.css);
                console.log('[Redo] Restored state', historyIndex);
            }
        } else {
            console.log('[Redo] No more history to redo');
        }
    }

    // Apply CSS directly to stylesheet without triggering save/reload
    function applyCssWithoutSave(cssText) {
        // Find or create a style element for live preview
        let styleEl = document.getElementById('live-preview-style');
        if (!styleEl) {
            styleEl = document.createElement('style');
            styleEl.id = 'live-preview-style';
            document.head.appendChild(styleEl);
        }
        styleEl.textContent = cssText;
    }

    undoBtn.addEventListener('click', undo);
    redoBtn.addEventListener('click', redo);

    // Global keyboard shortcuts
    document.addEventListener('keydown', function(e) {
        if (document.activeElement === editor) return; // Don't interfere with text editing

        if (e.ctrlKey && e.key === 'z') {
            e.preventDefault();
            undo();
        }
        if (e.ctrlKey && e.key === 'y') {
            e.preventDefault();
            redo();
        }
    });

    // Shift+Enter in editor to apply
    editor.addEventListener('keydown', function(e) {
        if (e.shiftKey && e.key === 'Enter') {
            e.preventDefault();
            saveToHistory();
            autoApplyChange();
        }
    });

    // === AUTO-APPLY ===
    let lastSaveTime = 0;
    const reloadDebounceMs = 2000; // Ignore reloads for 2 seconds after save

    function autoApplyChange() {
        if (!currentSelector) return;
        lastSaveTime = Date.now(); // Record save time for debounce
        ws.send(JSON.stringify({
            type: 'save_css',
            selector: currentSelector,
            css: editor.value
        }));
    }

    // === ELEMENT SELECTION ===
    document.addEventListener('click', function(e) {
        if (e.target.closest('#editor-panel') || e.target.closest('.editor-btn') || e.target.classList.contains('resize-handle')) {
            return;
        }
        if (isDragging || isResizing) return;
        if (!inspectMode) return;

        e.preventDefault();
        e.stopPropagation();

        const element = e.target;
        const selector = getCSSSelector(element);

        highlightElement(element);
        clearHoverHighlight();
        selectedElement = element;
        addResizeHandles(element);

        currentSelector = selector;
        selectorDisplay.textContent = selector;

        ws.send(JSON.stringify({
            type: 'get_css',
            selector: selector
        }));
    }, true);

    // Hover highlight
    document.addEventListener('mouseover', function(e) {
        if (!inspectMode) return;
        if (e.target.closest('#editor-panel') || e.target.closest('.editor-btn') || e.target.classList.contains('resize-handle')) return;
        clearHoverHighlight();
        e.target.classList.add('editor-hover-highlight');
    });

    document.addEventListener('mouseout', function(e) {
        if (!inspectMode) return;
        e.target.classList.remove('editor-hover-highlight');
    });

    // === DRAG FUNCTIONALITY ===
    document.addEventListener('mousedown', function(e) {
        if (!selectedElement) return;
        if (e.target.classList.contains('resize-handle')) {
            isResizing = true;
            resizeHandle = e.target.dataset.handle;
            resizeEl = selectedElement;
            const rect = resizeEl.getBoundingClientRect();
            const style = getComputedStyle(resizeEl);
            startX = e.clientX;
            startY = e.clientY;
            startWidth = rect.width;
            startHeight = rect.height;
            startLeft = parseFloat(style.left) || 0;
            startTop = parseFloat(style.top) || 0;
            e.preventDefault();
            return;
        }

        if (e.target === selectedElement || selectedElement.contains(e.target)) {
            if (e.target.classList.contains('resize-handle')) return;
            isDragging = true;
            dragEl = selectedElement;
            const style = getComputedStyle(dragEl);
            startX = e.clientX;
            startY = e.clientY;

            const transform = style.transform;
            if (transform && transform !== 'none') {
                const match = transform.match(/translate\\((-?\\d+(?:\\.\\d+)?)px,\\s*(-?\\d+(?:\\.\\d+)?)px\\)/);
                if (match) {
                    startLeft = parseFloat(match[1]);
                    startTop = parseFloat(match[2]);
                } else {
                    startLeft = 0;
                    startTop = 0;
                }
            } else {
                startLeft = parseFloat(style.left) || 0;
                startTop = parseFloat(style.top) || 0;
            }

            if (style.position === 'static') {
                dragEl.style.position = 'relative';
            }
            e.preventDefault();
        }
    });

    document.addEventListener('mousemove', function(e) {
        if (isDragging && dragEl) {
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;
            dragEl.style.left = (startLeft + deltaX) + 'px';
            dragEl.style.top = (startTop + deltaY) + 'px';
            sizeIndicator.textContent = `Position: ${Math.round(startLeft + deltaX)}px, ${Math.round(startTop + deltaY)}px`;
            sizeIndicator.classList.add('visible');
            updateResizeHandlesPosition(dragEl);
        }

        if (isResizing && resizeEl) {
            const deltaX = e.clientX - startX;
            const deltaY = e.clientY - startY;
            const aspectRatio = startWidth / startHeight;
            let newWidth = startWidth;
            let newHeight = startHeight;

            if (resizeHandle.includes('e')) newWidth = startWidth + deltaX;
            if (resizeHandle.includes('w')) newWidth = startWidth - deltaX;
            if (resizeHandle.includes('s')) newHeight = startHeight + deltaY;
            if (resizeHandle.includes('n')) newHeight = startHeight - deltaY;

            if (e.shiftKey) {
                if (resizeHandle === 'n' || resizeHandle === 's') {
                    newWidth = newHeight * aspectRatio;
                } else if (resizeHandle === 'e' || resizeHandle === 'w') {
                    newHeight = newWidth / aspectRatio;
                } else {
                    const avgScale = (newWidth / startWidth + newHeight / startHeight) / 2;
                    newWidth = startWidth * avgScale;
                    newHeight = startHeight * avgScale;
                }
            }

            newWidth = Math.max(20, newWidth);
            newHeight = Math.max(20, newHeight);

            resizeEl.style.width = newWidth + 'px';
            resizeEl.style.height = newHeight + 'px';
            sizeIndicator.textContent = `Size: ${Math.round(newWidth)}px × ${Math.round(newHeight)}px${e.shiftKey ? ' (1:1)' : ''}`;
            sizeIndicator.classList.add('visible');
            updateResizeHandlesPosition(resizeEl);
        }
    });

    document.addEventListener('mouseup', function(e) {
        if (isDragging && dragEl) {
            const style = getComputedStyle(dragEl);

            // Update the editor content with new position
            if (currentSelector && editor.value) {
                let css = editor.value;
                const newLeft = dragEl.style.left;
                const newTop = dragEl.style.top;

                // Update or add left property
                if (newLeft) {
                    css = updatePropertyInCSS(css, 'left', newLeft);
                }
                // Update or add top property
                if (newTop) {
                    css = updatePropertyInCSS(css, 'top', newTop);
                }

                editor.value = css;
                console.log('[Editor] Updated position: left=' + newLeft + ', top=' + newTop);
            }

            sizeIndicator.textContent = `Position updated - Shift+Enter to save`;
            sizeIndicator.classList.add('visible');

            // Save state for undo
            saveToHistory();

            isDragging = false;
            dragEl = null;
        }

        if (isResizing && resizeEl) {
            // Update the editor content with new size
            if (currentSelector && editor.value) {
                let css = editor.value;
                const newWidth = resizeEl.style.width;
                const newHeight = resizeEl.style.height;

                css = updatePropertyInCSS(css, 'width', newWidth);
                css = updatePropertyInCSS(css, 'height', newHeight);

                editor.value = css;
                console.log('[Editor] Updated size: width=' + newWidth + ', height=' + newHeight);
            }

            sizeIndicator.textContent = `Size updated - Shift+Enter to save`;
            sizeIndicator.classList.add('visible');

            // Save state for undo
            saveToHistory();

            isResizing = false;
            resizeEl = null;
            resizeHandle = null;
        }
    });

    // Helper: Update or add a CSS property in the current selector's block
    function updatePropertyInCSS(css, property, value) {
        if (!currentSelector) {
            console.log('[Editor] No selector selected, cannot update');
            return css;
        }

        // Find the selector block using simple string search
        const selectorStart = css.indexOf(currentSelector);
        if (selectorStart === -1) {
            console.log('[Editor] Could not find selector: ' + currentSelector);
            return css;
        }

        const braceStart = css.indexOf('{', selectorStart);
        if (braceStart === -1) return css;

        // Find matching closing brace
        let depth = 1;
        let braceEnd = braceStart + 1;
        while (depth > 0 && braceEnd < css.length) {
            if (css[braceEnd] === '{') depth++;
            else if (css[braceEnd] === '}') depth--;
            braceEnd++;
        }

        // Extract block content
        const beforeBlock = css.substring(0, braceStart + 1);
        let blockContent = css.substring(braceStart + 1, braceEnd - 1);
        const afterBlock = css.substring(braceEnd - 1);

        // Look for the property in the block using simple search
        const propStart = blockContent.indexOf(property + ':');

        if (propStart !== -1) {
            // Property exists - find the semicolon and replace
            const propEnd = blockContent.indexOf(';', propStart);
            if (propEnd !== -1) {
                const oldValue = blockContent.substring(propStart, propEnd + 1);
                blockContent = blockContent.replace(oldValue, property + ': ' + value + ';');
                console.log('[Editor] Updated existing property: ' + property + ': ' + value);
            }
        } else {
            // Property doesn't exist - add it after the opening brace
            blockContent = '\\n    ' + property + ': ' + value + ';' + blockContent;
            console.log('[Editor] Added new property: ' + property + ': ' + value);
        }

        return beforeBlock + blockContent + afterBlock;
    }

    // === RESIZE HANDLES ===
    function addResizeHandles(el) {
        removeResizeHandles();
        const handles = ['nw', 'n', 'ne', 'e', 'se', 's', 'sw', 'w'];
        const container = document.createElement('div');
        container.id = 'resize-handles-container';

        handles.forEach(h => {
            const handle = document.createElement('div');
            handle.className = 'resize-handle ' + h;
            handle.dataset.handle = h;
            container.appendChild(handle);
        });

        const rect = el.getBoundingClientRect();
        container.style.position = 'fixed';
        container.style.left = rect.left + 'px';
        container.style.top = rect.top + 'px';
        container.style.width = rect.width + 'px';
        container.style.height = rect.height + 'px';
        container.style.pointerEvents = 'none';
        container.style.zIndex = '10000';

        container.querySelectorAll('.resize-handle').forEach(h => {
            h.style.pointerEvents = 'auto';
        });

        document.body.appendChild(container);
    }

    function removeResizeHandles() {
        const container = document.getElementById('resize-handles-container');
        if (container) container.remove();
    }

    function updateResizeHandlesPosition(el) {
        const container = document.getElementById('resize-handles-container');
        if (!container) return;
        const rect = el.getBoundingClientRect();
        container.style.left = rect.left + 'px';
        container.style.top = rect.top + 'px';
        container.style.width = rect.width + 'px';
        container.style.height = rect.height + 'px';
    }

    // === APPLY / RESET ===
    applyBtn.addEventListener('click', function() {
        saveToHistory();
        autoApplyChange();
    });

    resetBtn.addEventListener('click', function() {
        editor.value = originalCss;
    });

    // === WEBSOCKET ===
    ws.onmessage = function(e) {
        try {
            const data = JSON.parse(e.data);
            if (data.type === 'css_rules') {
                editor.value = data.css;
                originalCss = data.css;
                saveToHistory();
            } else if (data.type === 'reload') {
                // Debounce: skip reload if we just saved
                const timeSinceSave = Date.now() - lastSaveTime;
                if (timeSinceSave < reloadDebounceMs) {
                    console.log('[Editor] Skipped reload (auto-save debounce)');
                } else {
                    console.log('[Hot Reload] File changed, reloading...');
                    location.reload();
                }
            } else if (data.type === 'save_result') {
                if (data.success) {
                    selectorDisplay.textContent = 'Saved!';
                    selectorDisplay.style.color = '#4a8a4a';
                    setTimeout(() => {
                        selectorDisplay.style.color = '#a0e0e0';
                        selectorDisplay.textContent = currentSelector;
                    }, 500);
                }
            }
        } catch (err) {
            if (e.data === 'reload') {
                const timeSinceSave = Date.now() - lastSaveTime;
                if (timeSinceSave >= reloadDebounceMs) {
                    location.reload();
                }
            }
        }
    };

    // === HELPERS ===
    function getCSSSelector(el) {
        if (el.className && typeof el.className === 'string') {
            const classes = el.className.trim().split(/\\s+/).filter(c => c && !c.startsWith('editor-') && !c.startsWith('resize-'));
            if (classes.length > 0) return '.' + classes[0];
        }
        if (el.id) return '#' + el.id;
        const parent = el.parentElement;
        if (parent && parent.className) {
            const parentClasses = parent.className.trim().split(/\\s+/).filter(c => c && !c.startsWith('editor-'));
            if (parentClasses.length > 0) return '.' + parentClasses[0] + ' > ' + el.tagName.toLowerCase();
        }
        return el.tagName.toLowerCase();
    }

    function highlightElement(el) {
        clearHighlight();
        el.classList.add('editor-highlight');
    }

    function clearHighlight() {
        document.querySelectorAll('.editor-highlight').forEach(e => e.classList.remove('editor-highlight'));
    }

    function clearHoverHighlight() {
        document.querySelectorAll('.editor-hover-highlight').forEach(e => e.classList.remove('editor-hover-highlight'));
    }

    console.log('[Editor] Visual editor loaded - drag/resize auto-applies, Ctrl+Z/Y undo/redo, Ctrl+scroll zoom, F reset, Grid toggle');
})();
</script>
'''


def find_css_rules(selector: str, css_content: str) -> str:
    """
    Extract CSS rules matching a selector from CSS content.

    Args:
        selector: CSS selector (e.g., '.knob', '#in-knob')
        css_content: Full CSS file content

    Returns:
        CSS rule(s) as string
    """
    # Clean selector for regex
    clean_selector = re.escape(selector)

    # Pattern to match selector and its block
    # Handles: .knob { ... } and .knob:hover { ... }
    pattern = rf'{clean_selector}[^{{]*\{{[^}}]*\}}'

    matches = re.findall(pattern, css_content, re.DOTALL | re.MULTILINE)

    if matches:
        return '\n\n'.join(matches)
    else:
        # Try partial match (selector might be part of a compound selector)
        pattern = rf'[^{{]*{clean_selector}[^{{]*\{{[^}}]*\}}'
        matches = re.findall(pattern, css_content, re.DOTALL | re.MULTILINE)
        if matches:
            return '\n\n'.join(matches[:3])  # Limit to first 3 matches
        return f'/* No rules found for {selector} */'


def update_css_rules(selector: str, new_rules: str, css_content: str) -> str:
    """
    Replace CSS rules matching selector with new rules.

    Args:
        selector: CSS selector to find (e.g., '.knob')
        new_rules: New CSS rule(s) to replace with
        css_content: Full CSS file content

    Returns:
        Updated CSS content
    """
    # Clean selector for regex
    clean_selector = re.escape(selector)

    # Pattern to match the selector and its block (handles nested braces)
    # This matches: .selector ... { ... } where inner braces are balanced
    pattern = rf'({clean_selector}[^{{]*\{{(?:[^{{}}]|{{[^{{}}]*}})*\}})'

    new_rules_stripped = new_rules.strip()

    if re.search(pattern, css_content, re.DOTALL):
        # Replace ALL occurrences of the rule
        result = re.sub(pattern, new_rules_stripped, css_content, flags=re.DOTALL)
        return result
    else:
        # Append new rule at end
        return css_content.rstrip() + '\n\n' + new_rules_stripped


class EditorReloadHandler(SimpleHTTPRequestHandler):
    """HTTP handler with editor mode support."""
    editor_mode = False  # Class variable - set before server starts

    def __init__(self, *args, directory=None, **kwargs):
        if directory is None:
            directory = os.getcwd()
        self.directory = directory
        super().__init__(*args, directory=directory, **kwargs)

    def do_GET(self):
        """Handle GET requests."""
        path = self.translate_path(self.path)

        # API: Get full CSS content
        if self.path == '/__css_full__':
            css_path = os.path.join(self.directory, 'styles.css')
            if os.path.exists(css_path):
                with open(css_path, 'r', encoding='utf-8') as f:
                    css_content = f.read()
                self.send_json_response({'success': True, 'css': css_content})
            else:
                self.send_json_response({'success': False, 'error': 'styles.css not found'})
            return

        # Handle directory requests - check for index.html
        html_path = path
        if os.path.isdir(path):
            for index in ['index.html', 'index.htm']:
                index_path = os.path.join(path, index)
                if os.path.isfile(index_path):
                    html_path = index_path
                    break

        # HTML files - inject scripts
        if html_path.endswith('.html') and os.path.isfile(html_path):
            with open(html_path, 'rb') as f:
                content = f.read()

            # Build injection script
            injection = b'<script>\n'
            injection += b'const WS_PORT = 8765;\n'
            injection += b'</script>\n'

            # Add editor panel if in editor mode
            if EditorReloadHandler.editor_mode:
                injection += EDITOR_SCRIPT.encode('utf-8')

            # Add hot reload script
            hot_reload = b'''
<script>
(function() {
    const ws = new WebSocket('ws://localhost:' + (typeof WS_PORT !== 'undefined' ? WS_PORT : 8765));
    ws.onmessage = function(e) {
        if (e.data === 'reload' || (e.data && JSON.parse(e.data).type === 'reload')) {
            console.log('[Hot Reload] Reloading...');
            location.reload();
        }
    };
    ws.onclose = function() {
        console.log('[Hot Reload] Disconnected');
    };
    console.log('[Hot Reload] Connected');
})();
</script>
'''
            injection += hot_reload

            # Insert before </body>
            if b'</body>' in content:
                content = content.replace(b'</body>', injection + b'</body>')
            elif b'</html>' in content:
                content = content.replace(b'</html>', injection + b'</html>')
            else:
                content += injection

            self.send_response(200)
            self.send_header('Content-Type', 'text/html; charset=utf-8')
            self.send_header('Content-Length', str(len(content)))
            self.end_headers()
            self.wfile.write(content)
        else:
            super().do_GET()

    def do_POST(self):
        """Handle POST requests."""
        # API: Save CSS
        if self.path == '/__css_save__':
            content_length = int(self.headers['Content-Length'])
            post_data = self.rfile.read(content_length)

            try:
                data = json.loads(post_data.decode('utf-8'))
                css_content = data.get('css', '')

                css_path = os.path.join(self.directory, 'styles.css')
                with open(css_path, 'w', encoding='utf-8') as f:
                    f.write(css_content)

                self.send_json_response({'success': True, 'no_reload': True})
                print(f"[Editor] Saved CSS changes to {css_path}")

                # Don't trigger reload - editor handles CSS update internally

            except Exception as e:
                self.send_json_response({'success': False, 'error': str(e)})
            return

        super().do_POST()

    def send_json_response(self, data: dict):
        """Send JSON response."""
        content = json.dumps(data).encode('utf-8')
        self.send_response(200)
        self.send_header('Content-Type', 'application/json')
        self.send_header('Content-Length', str(len(content)))
        self.send_header('Access-Control-Allow-Origin', '*')
        self.end_headers()
        self.wfile.write(content)

    def log_message(self, format, *args):
        """Suppress verbose logging."""
        pass

    def end_headers(self):
        """Add cache-control headers to prevent caching during development."""
        self.send_header('Cache-Control', 'no-store, no-cache, must-revalidate, max-age=0')
        self.send_header('Pragma', 'no-cache')
        self.send_header('Expires', '0')
        super().end_headers()


class FileChangeHandler(FileSystemEventHandler):
    """Watchdog handler for file changes."""

    def __init__(self, callback):
        self.callback = callback

    def on_modified(self, event):
        if not event.is_directory:
            ext = os.path.splitext(event.src_path)[1].lower()
            if ext in ('.html', '.css', '.js', '.svg', '.png', '.jpg', '.jpeg'):
                self.callback(event.src_path)


async def ws_handler(websocket):
    """WebSocket handler for reload and editor messages."""
    global _css_file_path

    _ws_clients.add(websocket)
    print(f"[WS] Client connected ({len(_ws_clients)} total)")

    try:
        async for message in websocket:
            try:
                data = json.loads(message)

                if data.get('type') == 'get_css':
                    # Find CSS rules for selector
                    selector = data.get('selector', '')

                    if _css_file_path and os.path.exists(_css_file_path):
                        with open(_css_file_path, 'r', encoding='utf-8') as f:
                            css_content = f.read()

                        rules = find_css_rules(selector, css_content)

                        await websocket.send(json.dumps({
                            'type': 'css_rules',
                            'selector': selector,
                            'css': rules
                        }))
                    else:
                        await websocket.send(json.dumps({
                            'type': 'css_rules',
                            'selector': selector,
                            'css': '/* CSS file not found */'
                        }))

                elif data.get('type') == 'save_css':
                    # Update specific CSS rules
                    selector = data.get('selector', '')
                    new_rules = data.get('css', '')

                    if _css_file_path and selector:
                        # Read current CSS
                        with open(_css_file_path, 'r', encoding='utf-8') as f:
                            original_css = f.read()

                        # Update only the matching rules
                        updated_css = update_css_rules(selector, new_rules, original_css)

                        # Write back
                        with open(_css_file_path, 'w', encoding='utf-8') as f:
                            f.write(updated_css)

                        print(f"[Editor] Updated rules for {selector}")

                        await websocket.send(json.dumps({
                            'type': 'save_result',
                            'success': True
                        }))

                        # Notify all clients to reload
                        notify_reload(_css_file_path)

            except json.JSONDecodeError:
                # Plain text message - ignore
                pass

    finally:
        _ws_clients.remove(websocket)
        print(f"[WS] Client disconnected ({len(_ws_clients)} total)")


async def ws_server(host='localhost', port=8765):
    """WebSocket server."""
    print(f"[WS] Starting WebSocket server on ws://{host}:{port}")
    async with websockets.serve(ws_handler, host, port):
        await asyncio.Future()


def notify_reload(filepath: str):
    """Notify all connected clients to reload."""
    if _ws_clients:
        print(f"[Hot Reload] Changed: {filepath}")
        for ws in list(_ws_clients):
            try:
                asyncio.create_task(ws.send(json.dumps({'type': 'reload'})))
            except Exception as e:
                print(f"[WS] Error: {e}")


def start_http_server(directory: str, port: int = 8000):
    """Start HTTP server."""
    global _css_file_path
    _css_file_path = os.path.join(directory, 'styles.css')

    # Set editor mode on handler class before starting server
    EditorReloadHandler.editor_mode = _editor_mode

    os.chdir(directory)
    handler = lambda *args, **kwargs: EditorReloadHandler(*args, directory=directory, **kwargs)
    server = HTTPServer(('localhost', port), handler)

    mode = "EDITOR MODE" if EditorReloadHandler.editor_mode else "PREVIEW MODE"
    print(f"[HTTP] Serving {directory} at http://localhost:{port}")
    print(f"[Mode] {mode}")

    server.serve_forever()


def start_ws_server(port: int = 8765):
    """Start WebSocket server in background thread."""
    def run_ws():
        asyncio.run(ws_server('localhost', port))

    thread = threading.Thread(target=run_ws, daemon=True)
    thread.start()

    import time
    time.sleep(0.5)


def start_file_watcher(directory: str):
    """Start file watcher for hot reload."""
    handler = FileChangeHandler(notify_reload)
    observer = Observer()
    observer.schedule(handler, directory, recursive=True)
    observer.start()
    print(f"[Watch] Monitoring {directory}")
    return observer


def main():
    """Main entry point."""
    global _editor_mode

    parser = argparse.ArgumentParser(
        description='Preview server with hot reload and visual editor',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog='''
Examples:
  python preview_server.py ./ui/public/
  python preview_server.py ./ui/public/ --editor
  python -m translation_layer preview ./ui/public/ --editor
'''
    )
    parser.add_argument('directory', help='Directory to serve')
    parser.add_argument('--port', '-p', type=int, default=8000, help='HTTP port')
    parser.add_argument('--ws-port', '-w', type=int, default=8765, help='WebSocket port')
    parser.add_argument('--no-browser', '-n', action='store_true', help='Do not open browser')
    parser.add_argument('--editor', '-e', action='store_true', help='Enable visual editor mode')

    args = parser.parse_args()

    # Set editor mode (must use global to modify module-level variable)
    global _editor_mode
    _editor_mode = args.editor
    print(f"[MAIN] Editor mode set to: {_editor_mode}", flush=True)

    # Validate directory
    directory = Path(args.directory).resolve()
    if not directory.is_dir():
        print(f"Error: Directory not found: {directory}")
        return 1

    print("=" * 50)
    print("PREVIEW SERVER" + (" + EDITOR" if _editor_mode else ""))
    print("=" * 50)

    # Start servers
    start_ws_server(args.ws_port)
    observer = start_file_watcher(str(directory))

    try:
        if not args.no_browser:
            import time
            def open_browser():
                time.sleep(0.5)
                url = f"http://localhost:{args.port}"
                print(f"[Browser] Opening {url}")
                webbrowser.open(url)
            threading.Thread(target=open_browser, daemon=True).start()

        start_http_server(str(directory), args.port)

    except KeyboardInterrupt:
        print("\n[Server] Shutting down...")
        observer.stop()
        observer.join()
        print("[Server] Done.")
        return 0

    return 0


if __name__ == '__main__':
    import sys
    sys.exit(main())
