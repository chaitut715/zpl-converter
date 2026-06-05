# Changelog

All notable changes to this project will be documented here.

## [1.0.0] — 2026-06-05

### Added
- ZPL → PNG rendering via bundled [labelize](https://github.com/GOODBOY008/labelize) binary
- Live preview with auto-rescale on window resize
- Drag-and-drop: files, multiple files, or an entire folder
- Paste / type raw ZPL directly into the editor
- Multi-label ZPL support — single file with multiple `^XA…^XZ` blocks renders all pages
- Save as PNG (page 1) and Save as PDF (all pages, exact label dimensions)
- Batch folder export — processes all `.zpl` and `.txt` files in a folder
- Configurable DPI (152 / 203 / 300 / 600) and label dimensions (width × height in inches)
- Output files named after the source file (e.g. `203032468.pdf`)
- QR code compatibility fix — rewrites manual-mode `^FD` fields to labelize-compatible format
- macOS Apple Silicon support for local development
- Windows 10/11 x64 self-contained executable built by GitHub Actions CI
