import logging
import shutil
from pathlib import Path
from typing import Callable, List, Optional, Tuple

from core.renderer import ZPLRenderer, RendererError
from core.pdf_export import PDFExporter

logger = logging.getLogger(__name__)


class BatchProcessor:
    """Processes a folder of ZPL files into PNGs or a combined PDF."""

    def process_folder(
        self,
        input_folder: Path,
        output_folder: Path,
        dpi: int,
        as_pdf: bool,
        label_width_in: float,
        label_height_in: float,
        progress_callback: Optional[Callable[[int, int], None]] = None,
    ) -> Tuple[int, int, Optional[Path]]:
        """
        Render all .zpl files in input_folder.

        Args:
            input_folder: Directory containing .zpl files.
            output_folder: Destination directory for output files.
            dpi: Render resolution.
            as_pdf: If True, combine all labels into one multi-page PDF.
            label_width_in: Label width in inches (for PDF page size).
            label_height_in: Label height in inches (for PDF page size).
            progress_callback: Called with (current_index, total) after each file.

        Returns:
            (succeeded_count, failed_count, log_path_or_None)
        """
        zpl_files: List[Path] = sorted(
            list(input_folder.glob("*.zpl")) + list(input_folder.glob("*.txt"))
        )
        if not zpl_files:
            logger.warning("No .zpl files found in: %s", input_folder)
            return 0, 0, None

        output_folder.mkdir(parents=True, exist_ok=True)

        total = len(zpl_files)
        succeeded = 0
        failed_entries: List[Tuple[str, str]] = []
        rendered_pngs: List[Path] = []

        renderer = ZPLRenderer()

        for idx, zpl_file in enumerate(zpl_files, start=1):
            if progress_callback:
                progress_callback(idx, total)

            try:
                png_paths = renderer.render_zpl_file(
                    zpl_file, dpi, label_width_in, label_height_in
                )
                rendered_pngs.extend(png_paths)

                if not as_pdf:
                    if len(png_paths) == 1:
                        dest = output_folder / f"{zpl_file.stem}.png"
                        shutil.copy2(png_paths[0], dest)
                        logger.info("Exported PNG: %s", dest)
                    else:
                        for page_idx, png_path in enumerate(png_paths, start=1):
                            dest = output_folder / f"{zpl_file.stem}_p{page_idx}.png"
                            shutil.copy2(png_path, dest)
                            logger.info("Exported PNG page %d: %s", page_idx, dest)

                succeeded += 1

            except RendererError as exc:
                logger.error("Render failed for %s: %s", zpl_file.name, exc)
                failed_entries.append((zpl_file.name, str(exc)))
            except Exception as exc:
                logger.exception("Unexpected error processing %s", zpl_file.name)
                failed_entries.append((zpl_file.name, f"Unexpected error: {exc}"))

        # Combine into a multi-page PDF when requested
        if as_pdf and rendered_pngs:
            pdf_path = output_folder / "batch_export.pdf"
            try:
                PDFExporter().export_batch(
                    rendered_pngs, pdf_path, label_width_in, label_height_in, dpi
                )
                logger.info("Batch PDF saved: %s", pdf_path)
            except Exception as exc:
                logger.error("Failed to create batch PDF: %s", exc)
                failed_entries.append(("batch_export.pdf", str(exc)))
                succeeded = max(0, succeeded - len(rendered_pngs))

        # Write failure log
        log_path: Optional[Path] = None
        if failed_entries:
            log_path = output_folder / "failed_files.log"
            with log_path.open("w", encoding="utf-8") as fh:
                fh.write(
                    f"Batch processing failures "
                    f"({len(failed_entries)}/{total}):\n\n"
                )
                for filename, reason in failed_entries:
                    fh.write(f"[FAILED] {filename}\n  Reason: {reason}\n\n")
            logger.info("Failure log: %s", log_path)

        return succeeded, len(failed_entries), log_path
