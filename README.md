# ZPL Converter

A self-contained Windows 10/11 desktop application that converts ZPL (Zebra Programming Language) label files to PNG or PDF — fully offline, no Java required.

## Features

| Feature | Detail |
|---|---|
| Live preview | Renders ZPL to PNG instantly in the preview panel |
| Any file extension | Accepts `.zpl`, `.txt`, or any text file containing ZPL |
| Drag-and-drop | Drop files, multiple files, or an entire folder |
| Paste ZPL | Type or paste raw ZPL directly into the editor |
| Multi-label files | Single ZPL file with multiple `^XA…^XZ` blocks → all pages rendered |
| PNG export | Save page 1 as PNG, named after the source file |
| PDF export | All pages → multi-page PDF with exact label page dimensions |
| Batch processing | Folder of ZPL/text files → PNGs or one combined PDF |
| Configurable DPI | 152 / 203 / 300 / 600 (default 203) |
| Label sizing | Width × height in inches; controls PDF page size and render canvas |
| Output naming | Output files named after the source file (e.g. `203032468.pdf`) |
| QR code fix | Automatic rewrite of manual-mode QR `^FD` fields to labelize-compatible format |
| Error reporting | Labelize stderr shown inline in the preview; batch failures logged to `failed_files.log` |
| Fully offline | Zero network calls at runtime |

---

## Prerequisites (local development on macOS)

| Tool | Notes |
|---|---|
| Python 3.12+ | Use a venv — see below |
| Labelize ARM binary | Download from [Labelize releases](https://github.com/GOODBOY008/labelize/releases), place at `assets/labelize` |

---

## Local development setup (macOS Apple Silicon)

```bash
git clone <your-repo-url>
cd zpl-converter

# Create and activate venv
python3 -m venv .venv
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### Obtain the Labelize binary (macOS)

Download the macOS ARM64 build from [Labelize releases](https://github.com/GOODBOY008/labelize/releases) and place it at `assets/labelize`.

Remove the macOS quarantine flag before the first run:

```bash
xattr -d com.apple.quarantine assets/labelize
chmod +x assets/labelize
```

### Run the app

```bash
.venv/bin/python3 main.py
# or, if venv is activated:
python3 main.py
```

---

## Labelize CLI interface

The renderer calls labelize via its `convert` subcommand:

```
labelize convert <INPUT> -o <OUTPUT> --dpmm <N> --width <mm> --height <mm>
```

DPI values in the settings panel map to labelize `--dpmm` as follows:

| UI DPI | `--dpmm` |
|---|---|
| 152 | 6 |
| 203 | 8 |
| 300 | 12 |
| 600 | 24 |

Width and height are passed in millimetres (`inches × 25.4`).

**Multi-label files:** when a ZPL file contains multiple `^XA…^XZ` blocks, labelize produces `<stem>_1.png`, `<stem>_2.png`, … The app collects all pages automatically.

**QR code compatibility:** labelize does not support ZPL manual-mode QR data (`^FDMM,…^FS`). The renderer preprocesses ZPL before sending it, rewriting `^FD[HQML][MAE],` prefixes to `^FDQA,`.

---

## Download

Grab the latest release from the [**Releases page**](https://github.com/chaitut715/zpl-converter/releases/latest):

| File | Description |
|---|---|
| `zpl-converter-*-portable.zip` | **Portable** — unzip anywhere, run `zpl_converter.exe` |
| `zpl-converter-setup-*.exe` | **Installer** — adds Start Menu shortcut and uninstaller |

No Python, no Java, no runtimes required.

---

## Building the Windows executable (GitHub Actions)

The `.exe` is produced by a `windows-latest` GitHub Actions runner.

> **There is no pre-built `labelize.exe`** in the Labelize releases.  
> The CI compiles it from source using the Rust toolchain (~8 min first build, ~3 min after caching).

### Release a new version

```bash
git tag v1.0.0
git push origin v1.0.0
```

The workflow will build, package, and publish a GitHub Release automatically with both the portable zip and the installer attached.

### CI build steps

1. Set up Python 3.12 and install dependencies
2. Install Rust stable (MSVC) via `dtolnay/rust-toolchain@stable`
3. Clone and `cargo build --release --features cli` the labelize source → `assets\labelize.exe`
4. Run `pyinstaller zpl_converter.spec` → `dist/zpl_converter/`
5. Package portable zip → `zpl-converter-<tag>-windows-x64-portable.zip`
6. Compile Inno Setup installer (if `installer.iss` present)
7. On tag push: publish GitHub Release with both files attached

---

## Building the installer (Windows only)

```powershell
# 1. Build the PyInstaller bundle first
pyinstaller zpl_converter.spec

# 2. Compile with Inno Setup 6
"C:\Program Files (x86)\Inno Setup 6\ISCC.exe" installer.iss
```

Output: `Output\zpl-converter-setup-1.0.0.exe`

---

## Testing in UTM (Windows ARM VM on M-series Mac)

Windows 11 ARM has a built-in x64 emulation layer — the x64 `.exe` runs without modification.

1. Install [UTM](https://mac.getutm.app)
2. Create a Windows 11 ARM VM
3. Copy the `zpl_converter/` folder to the VM (UTM shared folder or network share)
4. Run `zpl_converter.exe`

---

## Logging

| Platform | Path |
|---|---|
| Windows | `%TEMP%\zpl_converter\zpl_converter.log` |
| macOS | `/tmp/zpl_converter/zpl_converter.log` |

---

## Project structure

```
zpl-converter/
├── main.py                   # Entry point — logging, binary check, top-level error guard
├── config.py                 # LABELIZE_BIN, TEMP_DIR, LOG_FILE (MEIPASS-aware)
├── requirements.txt          # PyQt6, reportlab, Pillow
├── zpl_converter.spec        # PyInstaller onedir spec (Windows x64, console=False)
├── installer.iss             # Inno Setup 6 script
├── CLAUDE.md                 # Context for Claude Code sessions
├── THIRD_PARTY_LICENSES.md   # License attribution for bundled software
├── ui/
│   ├── main_window.py        # Main window, toolbar, drag-and-drop, RenderThread, BatchThread
│   └── preview_widget.py     # Scrollable PNG preview with auto-rescale and error banner
├── core/
│   ├── renderer.py           # ZPL → PNG: preprocessing, labelize subprocess, multi-page collection
│   ├── pdf_export.py         # PNG list → multi-page PDF at exact label dimensions
│   └── batch.py              # Folder batch: *.zpl + *.txt, progress callback, failed_files.log
├── assets/
│   ├── labelize              # macOS ARM64 binary (local dev, gitignored)
│   └── labelize.exe          # Windows x64 binary (built by CI, gitignored)
└── .github/
    └── workflows/
        └── build.yml         # CI: Rust build → PyInstaller → artifacts
```

---

## Dependencies

| Package | Purpose |
|---|---|
| `PyQt6` | UI framework |
| `reportlab` | PDF generation |
| `Pillow` | Image I/O (used by reportlab) |
| `labelize` | ZPL → PNG renderer (Rust binary, platform-specific) |

---

## Offline guarantee

The built application makes zero network calls at runtime. All Python dependencies are bundled by PyInstaller. The `labelize` binary is included in `dist/zpl_converter/assets/`.
