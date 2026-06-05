# ZPL Converter — Claude Code Context

## What this project is

A PyQt6 desktop app that renders ZPL label files to PNG/PDF using the Labelize Rust binary as a subprocess. Developed on macOS Apple Silicon; Windows builds are produced exclusively via GitHub Actions.

---

## How to run locally

```bash
# One-time setup
python3 -m venv .venv
.venv/bin/pip install -r requirements.txt

# Run
.venv/bin/python3 main.py
```

The app starts fine on macOS. Rendering works only if `assets/labelize` (ARM binary) is present and the quarantine flag has been removed:

```bash
xattr -d com.apple.quarantine assets/labelize
```

---

## Labelize binary — platform rules

`config.py` resolves the binary name via `platform.system()`:

| Platform | Binary path |
|---|---|
| macOS / Linux | `assets/labelize` |
| Windows | `assets/labelize.exe` |

Both are gitignored. The macOS ARM binary is placed manually. The Windows binary is compiled from source in CI (no pre-built release exists).

When running as a PyInstaller bundle, `sys._MEIPASS` is used as the base directory instead of the project root.

---

## Labelize CLI — actual interface

The original spec assumed `--input / --output / --dpi` flags. The real CLI uses a subcommand:

```
labelize convert <INPUT> -o <OUTPUT> --dpmm <N> --width <mm> --height <mm>
```

DPI → dpmm mapping (defined in `core/renderer.py` as `_DPI_TO_DPMM`):

```
152 → 6,  203 → 8,  300 → 12,  600 → 24
```

Width and height are in **millimetres**: `round(inches * 25.4)`.

---

## Multi-label ZPL files

A single ZPL file can contain multiple `^XA…^XZ` label blocks. Labelize detects this and outputs numbered PNGs: `<stem>_1.png`, `<stem>_2.png`, etc. (instead of the base filename).

`_collect_output_pngs()` in `core/renderer.py` handles this by globbing for `<stem>_*.png` siblings. All methods that used to return a single `Path` now return `list[Path]`.

---

## ZPL preprocessing

Real-world ZPL files (e.g. from warehouse systems) use a two-character prefix in `^FD` fields after `^BQ` (QR code) commands:

```
^FDMM,A^FS   →  error correction M, mode M (manual), data "A"
```

Labelize only supports automatic mode. `_preprocess_zpl()` rewrites these before rendering:

```python
re.sub(r"\^FD[HQMLhqml][MAEmaEe],", "^FDQA,", content)
```

This runs on every render — it's idempotent and cheap.

---

## Partial render handling

Labelize exits with code 1 even if it rendered some pages before hitting an error. The renderer checks for output files first:

- Pages found + non-zero exit → partial success, log warning, return what rendered
- No pages + non-zero exit → raise `RendererError`

---

## Output file naming

The source file stem is tracked in `MainWindow._source_stem`. It is:
- Set in `_load_zpl_file()` to `path.stem`
- Reset to `"output"` on clear
- Passed to `RenderThread` → `render_zpl_string(name_stem=…)` so temp files and PNGs use the source name
- Used as the default filename in Save PNG / Save PDF dialogs

---

## File input

- **Drop zone** accepts any file (no extension filter) — `.zpl`, `.txt`, anything
- **Open dialog** filter: `ZPL / Text Files (*.zpl *.txt) | All Files (*)`
- **Batch folder scan** globs both `*.zpl` and `*.txt`

---

## Background threads

All rendering and batch processing runs off the main thread:

| Thread | Signal on success | Signal on failure |
|---|---|---|
| `RenderThread` | `finished(list[str])` — PNG paths | `error(str)` |
| `BatchThread` | `finished(int, int, str)` — ok, failed, log path | — |

`RenderThread.finished` emits a `list` (not `str`) because multi-label files produce multiple PNGs. The preview always shows page 1; Save as PDF exports all pages.

---

## CI build — three jobs

`build.yml` has three jobs: `build-windows`, `build-macos`, `release`.  
The `release` job runs only on `v*` tags and waits for both build jobs.

### build-windows (`windows-latest`)

No pre-built `labelize.exe` exists in the Labelize releases — it's compiled from source:

1. `dtolnay/rust-toolchain@stable` (target: `x86_64-pc-windows-msvc`)
2. `git clone https://github.com/GOODBOY008/labelize labelize-src`
3. `cargo build --release --features cli` — **`--features cli` is required**; without it cargo builds only the library and produces no binary
4. Copy `target/release/labelize.exe` → `assets/labelize.exe`
5. `pyinstaller zpl_converter.spec` → `dist/zpl_converter/`
6. Zip → `zpl-converter-<tag>-windows-x64-portable.zip`

Cargo artifacts cached via `actions/cache@v4`. First build ~8–10 min; subsequent ~3 min.

### build-macos (`macos-latest`, Apple Silicon)

Pre-built ARM binary is available in labelize releases:

1. Download `labelize-aarch64-apple-darwin.tar.gz` from labelize v1.1.0 release
2. Extract → `assets/labelize`, `chmod +x`
3. `pyinstaller zpl_converter_macos.spec` → `dist/ZPL Converter.app`
4. Zip → `zpl-converter-<tag>-macos-arm64.zip`

The `.app` bundle is **unsigned** — users bypass Gatekeeper with right-click → Open, or `xattr -dr com.apple.quarantine "ZPL Converter.app"`.

---

## Temp and log locations

```
macOS : /tmp/zpl_converter/
Win   : %TEMP%\zpl_converter\
Log   : <TEMP_DIR>/zpl_converter.log
```

The preprocessed ZPL is written to `<TEMP_DIR>/<stem>_processed.zpl` before rendering.

---

## What NOT to do

- Do not pass `--dpi` to labelize — it does not accept that flag. Use `--dpmm`.
- Do not pass width/height in inches — labelize expects millimetres.
- Do not look for `<output>.png` after a multi-label render — labelize writes `<output>_1.png`, `<output>_2.png`, etc.
- Do not hardcode any paths — all paths go through `config.py`.
- Do not add network calls at runtime — the app must stay fully offline.
- Do not return a single `Path` from renderer methods — they return `list[Path]`.
- Do not run `cargo build --release` without `--features cli` — it builds only the library, exits 0, and produces no binary.
