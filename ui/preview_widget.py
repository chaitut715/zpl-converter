import logging
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import Qt
from PyQt6.QtGui import QPixmap, QResizeEvent
from PyQt6.QtWidgets import QLabel, QScrollArea, QSizePolicy, QVBoxLayout, QWidget

logger = logging.getLogger(__name__)


class PreviewWidget(QWidget):
    """Scrollable panel that displays a rendered ZPL label as PNG."""

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self._original_pixmap: Optional[QPixmap] = None
        self._build_ui()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load_image(self, path: Path) -> None:
        """Display the PNG at *path* in the preview panel."""
        self.error_label.setVisible(False)
        pixmap = QPixmap(str(path))
        if pixmap.isNull():
            self.show_error(f"Failed to load image:\n{path}")
            return
        self._original_pixmap = pixmap
        self._render_scaled()
        logger.info("Preview loaded: %s", path)

    def show_error(self, message: str) -> None:
        """Display a red error banner inside the preview panel."""
        self._original_pixmap = None
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText("")
        self.error_label.setText(f"Render Error:\n\n{message}")
        self.error_label.setVisible(True)
        logger.error("Preview error: %s", message)

    def clear(self) -> None:
        """Reset the panel to its idle placeholder state."""
        self._original_pixmap = None
        self.image_label.setPixmap(QPixmap())
        self.image_label.setText(
            "No preview — render a ZPL file to see the label here."
        )
        self.image_label.setStyleSheet("color: #888; font-size: 12px;")
        self.error_label.setVisible(False)

    # ------------------------------------------------------------------
    # Qt overrides
    # ------------------------------------------------------------------

    def resizeEvent(self, event: QResizeEvent) -> None:
        super().resizeEvent(event)
        if self._original_pixmap and not self._original_pixmap.isNull():
            self._render_scaled()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(4)

        header = QLabel("Preview")
        header.setAlignment(Qt.AlignmentFlag.AlignCenter)
        header.setStyleSheet("font-weight: bold; font-size: 13px; padding: 4px;")
        layout.addWidget(header)

        self.scroll_area = QScrollArea()
        self.scroll_area.setWidgetResizable(True)
        self.scroll_area.setAlignment(Qt.AlignmentFlag.AlignCenter)

        self.image_label = QLabel(
            "No preview — render a ZPL file to see the label here."
        )
        self.image_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_label.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding
        )
        self.image_label.setStyleSheet("color: #888; font-size: 12px;")
        self.scroll_area.setWidget(self.image_label)
        layout.addWidget(self.scroll_area, stretch=1)

        self.error_label = QLabel()
        self.error_label.setWordWrap(True)
        self.error_label.setStyleSheet(
            "QLabel {"
            "  background-color: #c0392b;"
            "  color: white;"
            "  padding: 8px;"
            "  border-radius: 4px;"
            "  font-family: monospace;"
            "  font-size: 11px;"
            "}"
        )
        self.error_label.setVisible(False)
        layout.addWidget(self.error_label)

    def _render_scaled(self) -> None:
        """Scale _original_pixmap to fit the scroll area and display it."""
        if not self._original_pixmap:
            return
        available = self.scroll_area.viewport().size()
        scaled = self._original_pixmap.scaled(
            available.width() - 4,
            available.height() - 4,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_label.setPixmap(scaled)
        self.image_label.setStyleSheet("")
