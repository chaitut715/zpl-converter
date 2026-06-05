import logging
import re
import subprocess
from pathlib import Path

from config import LABELIZE_BIN, TEMP_DIR

logger = logging.getLogger(__name__)

# Labelize accepts dots-per-mm, not DPI.  Map our UI DPI labels to dpmm.
_DPI_TO_DPMM: dict[int, int] = {152: 6, 203: 8, 300: 12, 600: 24}

_ERROR_HINTS: list[tuple[str, str]] = [
    (
        "qr code: empty content",
        "QR code has empty or invalid data.\n\n"
        "The ^FD field after ^BQ must contain the text to encode.\n"
        "Example:\n"
        "  ^BQN,2,5\n"
        "  ^FDhttps://example.com^FS\n\n"
        "If you are using the QA prefix format, make sure there is\n"
        "content after the comma:\n"
        "  ^FDQA,https://example.com^FS",
    ),
    (
        "invalid qr barcode data",
        "QR code has empty or invalid data.\n\n"
        "The ^FD field after ^BQ must contain the text to encode.\n"
        "Example:\n"
        "  ^BQN,2,5\n"
        "  ^FDhttps://example.com^FS",
    ),
    (
        "invalid barcode data",
        "Barcode field (^FD) contains empty or invalid data.\n"
        "Check that your ^FD…^FS block has content after the barcode command.",
    ),
    (
        "unsupported",
        "Labelize does not support this ZPL command or combination.\n"
        "Check the Labelize release notes for supported features.",
    ),
]


def _friendly_error(raw: str) -> str:
    """Return a user-friendly message for known labelize errors."""
    lower = raw.lower()
    for keyword, hint in _ERROR_HINTS:
        if keyword in lower:
            return hint
    return raw


def _preprocess_zpl(content: str) -> str:
    """
    Rewrite ZPL patterns that labelize does not support.

    QR code ^FD fields in ZPL use a two-character prefix:
      [error-correction-level][character-mode],[data]
    e.g. ^FDMM,A^FS  (error=M, mode=M/manual, data="A")

    Labelize only handles automatic mode. This rewrites any prefixed
    format to ^FDQA,[data]^FS so labelize can render it.
    """
    # Match: ^FD + 1 error-correction char (H/Q/M/L) + 1 mode char (A/M/E) + comma
    # Rewrite to: ^FDQA,
    content = re.sub(
        r"\^FD[HQMLhqml][MAEmaEe],",
        "^FDQA,",
        content,
    )
    return content


def _collect_output_pngs(base_png: Path) -> list[Path]:
    """
    Collect PNGs that labelize wrote for a (possibly multi-label) ZPL file.

    Single label  → base_png  (e.g. out.png)
    Multiple labels → base_png.stem + "_1.png", "_2.png", …
    """
    stem = base_png.stem
    numbered = sorted(base_png.parent.glob(f"{stem}_*.png"))
    if numbered:
        return numbered
    if base_png.exists():
        return [base_png]
    return []


class RendererError(Exception):
    """Raised when ZPL rendering fails completely (zero pages produced)."""


class ZPLRenderer:
    """Renders ZPL labels to PNG using the bundled labelize binary."""

    def render_zpl_string(
        self,
        zpl_content: str,
        dpi: int,
        width_in: float = 4.0,
        height_in: float = 6.0,
        name_stem: str = "output",
    ) -> list[Path]:
        """
        Write ZPL content to a temp file and render it to PNG(s).

        Args:
            name_stem: Base name used for the temp file and output PNGs.
                       Defaults to "output"; pass the source filename stem
                       so rendered PNGs are named after the original file.

        Returns a list with one Path per label block (^XA…^XZ) in the input.
        Raises RendererError if no pages could be rendered at all.
        """
        TEMP_DIR.mkdir(parents=True, exist_ok=True)
        tmp_zpl = TEMP_DIR / f"{name_stem}.zpl"
        tmp_zpl.write_text(zpl_content, encoding="utf-8")
        return self.render_zpl_file(tmp_zpl, dpi, width_in, height_in)

    def render_zpl_file(
        self,
        zpl_path: Path,
        dpi: int,
        width_in: float = 4.0,
        height_in: float = 6.0,
    ) -> list[Path]:
        """
        Render a ZPL file (single or multi-label) to PNG(s).

        Applies ZPL preprocessing to fix known labelize incompatibilities
        before rendering.  Returns one Path per rendered label page.
        Raises RendererError if no pages could be rendered at all.
        """
        self._check_binary()
        TEMP_DIR.mkdir(parents=True, exist_ok=True)

        # Preprocess: fix QR code format and other known issues
        raw_content = zpl_path.read_text(encoding="utf-8", errors="replace")
        processed_content = _preprocess_zpl(raw_content)
        processed_zpl = TEMP_DIR / f"{zpl_path.stem}_processed.zpl"
        processed_zpl.write_text(processed_content, encoding="utf-8")

        output_png = TEMP_DIR / f"{zpl_path.stem}_{dpi}dpi.png"

        returncode, stdout, stderr = self._run_labelize_raw(
            processed_zpl, output_png, dpi, width_in, height_in
        )

        pngs = _collect_output_pngs(output_png)

        if returncode != 0:
            error_msg = _friendly_error(
                stderr.strip() or stdout.strip() or "Unknown error"
            )
            if pngs:
                # Partial success: some labels rendered before the error
                logger.warning(
                    "Partial render for %s: %d page(s) OK, then error: %s",
                    zpl_path.name,
                    len(pngs),
                    error_msg,
                )
            else:
                raise RendererError(error_msg)

        if not pngs:
            raise RendererError(
                f"labelize produced no output PNGs for: {zpl_path.name}"
            )

        logger.info("Rendered %d page(s) from %s", len(pngs), zpl_path.name)
        return pngs

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _check_binary(self) -> None:
        """Raise RendererError if the labelize binary is not present."""
        if not LABELIZE_BIN.exists():
            raise RendererError(
                f"labelize binary not found at:\n{LABELIZE_BIN}\n\n"
                "Download the appropriate build from:\n"
                "https://github.com/GOODBOY008/labelize/releases\n"
                "and place it in the assets/ folder."
            )

    def _run_labelize_raw(
        self,
        zpl_path: Path,
        output_png: Path,
        dpi: int,
        width_in: float,
        height_in: float,
    ) -> tuple[int, str, str]:
        """Run labelize and return (returncode, stdout, stderr)."""
        dpmm = _DPI_TO_DPMM.get(dpi, 8)
        width_mm = round(width_in * 25.4)
        height_mm = round(height_in * 25.4)

        cmd = [
            str(LABELIZE_BIN),
            "convert",
            str(zpl_path),
            "-o", str(output_png),
            "--dpmm", str(dpmm),
            "--width", str(width_mm),
            "--height", str(height_mm),
        ]
        logger.info("Running: %s", " ".join(cmd))

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=60,
            )
        except subprocess.TimeoutExpired:
            raise RendererError("labelize timed out after 60 seconds.")
        except FileNotFoundError:
            raise RendererError(f"labelize binary not found: {LABELIZE_BIN}")
        except OSError as exc:
            raise RendererError(f"Failed to launch labelize: {exc}") from exc

        logger.debug("stdout: %s", result.stdout)
        logger.debug("stderr: %s", result.stderr)
        return result.returncode, result.stdout, result.stderr
