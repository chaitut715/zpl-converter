import logging
from pathlib import Path
from typing import List

from reportlab.pdfgen import canvas
from reportlab.lib.units import inch

logger = logging.getLogger(__name__)


class PDFExporter:
    """Exports PNG label images to PDF using reportlab."""

    def export_single(
        self,
        png_path: Path,
        pdf_path: Path,
        label_width_in: float,
        label_height_in: float,
        dpi: int,
    ) -> None:
        """
        Export a single PNG to a one-page PDF sized to the label dimensions.

        Args:
            png_path: Source PNG file.
            pdf_path: Destination PDF file.
            label_width_in: Label width in inches.
            label_height_in: Label height in inches.
            dpi: DPI used when the PNG was rendered (informational).
        """
        self.export_batch(
            [png_path], pdf_path, label_width_in, label_height_in, dpi
        )

    def export_batch(
        self,
        png_paths: List[Path],
        pdf_path: Path,
        label_width_in: float,
        label_height_in: float,
        dpi: int,
    ) -> None:
        """
        Export multiple PNGs to a multi-page PDF.

        Each PNG occupies one page whose dimensions exactly match the label size.

        Args:
            png_paths: Source PNG files, one per page.
            pdf_path: Destination PDF file.
            label_width_in: Label width in inches.
            label_height_in: Label height in inches.
            dpi: DPI used when the PNGs were rendered (informational).
        """
        if not png_paths:
            raise ValueError("No PNG files provided for PDF export.")

        page_w = label_width_in * inch
        page_h = label_height_in * inch

        c = canvas.Canvas(str(pdf_path), pagesize=(page_w, page_h))

        pages_written = 0
        for i, png_path in enumerate(png_paths):
            if not png_path.exists():
                logger.warning("PNG missing, skipping page %d: %s", i + 1, png_path)
                continue

            c.drawImage(
                str(png_path),
                x=0,
                y=0,
                width=page_w,
                height=page_h,
                preserveAspectRatio=True,
                anchor="c",
            )
            c.showPage()
            pages_written += 1
            logger.info(
                "PDF page %d/%d: %s", pages_written, len(png_paths), png_path.name
            )

        if pages_written == 0:
            raise ValueError("No valid PNG files were found; PDF not written.")

        c.save()
        logger.info("PDF saved: %s (%d pages)", pdf_path, pages_written)
