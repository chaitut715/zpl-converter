import logging
import shutil
import tempfile
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QSize, Qt, QThread, pyqtSignal
from PyQt6.QtGui import QAction, QDragEnterEvent, QDropEvent
from PyQt6.QtWidgets import (
    QComboBox,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QProgressBar,
    QPushButton,
    QSizePolicy,
    QSplitter,
    QStatusBar,
    QTextEdit,
    QToolBar,
    QVBoxLayout,
    QWidget,
)

from config import TEMP_DIR
from core.renderer import ZPLRenderer, RendererError
from core.pdf_export import PDFExporter
from core.batch import BatchProcessor
from ui.preview_widget import PreviewWidget

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Background threads
# ---------------------------------------------------------------------------


class RenderThread(QThread):
    """Renders ZPL in a background thread so the UI stays responsive."""

    finished = pyqtSignal(list)  # list[str] of PNG paths (one per label page)
    error = pyqtSignal(str)

    def __init__(
        self,
        zpl_content: str,
        dpi: int,
        width_in: float,
        height_in: float,
        name_stem: str = "output",
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.zpl_content = zpl_content
        self.dpi = dpi
        self.width_in = width_in
        self.height_in = height_in
        self.name_stem = name_stem

    def run(self) -> None:
        try:
            png_paths = ZPLRenderer().render_zpl_string(
                self.zpl_content, self.dpi, self.width_in, self.height_in,
                self.name_stem,
            )
            self.finished.emit([str(p) for p in png_paths])
        except RendererError as exc:
            self.error.emit(str(exc))
        except Exception as exc:
            logger.exception("Unexpected render error")
            self.error.emit(f"Unexpected error: {exc}")


class BatchThread(QThread):
    """Runs batch processing in a background thread."""

    progress = pyqtSignal(int, int)        # current, total
    finished = pyqtSignal(int, int, str)   # succeeded, failed, log_path

    def __init__(
        self,
        input_folder: Path,
        output_folder: Path,
        dpi: int,
        as_pdf: bool,
        label_width: float,
        label_height: float,
        parent: Optional[QWidget] = None,
    ) -> None:
        super().__init__(parent)
        self.input_folder = input_folder
        self.output_folder = output_folder
        self.dpi = dpi
        self.as_pdf = as_pdf
        self.label_width = label_width
        self.label_height = label_height

    def run(self) -> None:
        succeeded, failed, log_path = BatchProcessor().process_folder(
            self.input_folder,
            self.output_folder,
            self.dpi,
            self.as_pdf,
            self.label_width,
            self.label_height,
            progress_callback=lambda cur, tot: self.progress.emit(cur, tot),
        )
        self.finished.emit(succeeded, failed, str(log_path) if log_path else "")


# ---------------------------------------------------------------------------
# Drop zone
# ---------------------------------------------------------------------------


class DropZone(QLabel):
    """A drag-and-drop target that accepts .zpl files and folders."""

    files_dropped = pyqtSignal(list)  # list[str] of dropped paths

    def __init__(self, parent: Optional[QWidget] = None) -> None:
        super().__init__(parent)
        self.setText("Drag & drop .zpl file(s) or a folder here")
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setAcceptDrops(True)
        self.setMinimumHeight(72)
        self.setStyleSheet(
            "QLabel {"
            "  border: 2px dashed #888;"
            "  border-radius: 8px;"
            "  color: #888;"
            "  font-size: 13px;"
            "  padding: 8px;"
            "}"
            "QLabel:hover {"
            "  border-color: #4a90d9;"
            "  color: #4a90d9;"
            "}"
        )

    def dragEnterEvent(self, event: QDragEnterEvent) -> None:
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event: QDropEvent) -> None:
        paths = [url.toLocalFile() for url in event.mimeData().urls()]
        if paths:
            self.files_dropped.emit(paths)


# ---------------------------------------------------------------------------
# Main window
# ---------------------------------------------------------------------------


class MainWindow(QMainWindow):
    """Primary application window."""

    def __init__(self) -> None:
        super().__init__()
        self.setWindowTitle("ZPL Converter")
        self.setMinimumSize(900, 640)
        self.resize(1200, 800)

        self._current_pngs: list[Path] = []   # all pages from last render
        self._current_png: Optional[Path] = None  # page 1 (shown in preview)
        self._source_stem: str = "output"          # stem of the loaded source file
        self._render_thread: Optional[RenderThread] = None
        self._batch_thread: Optional[BatchThread] = None

        self._build_ui()
        self._connect_signals()
        logger.info("MainWindow initialised")

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        central = QWidget()
        self.setCentralWidget(central)
        root = QVBoxLayout(central)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        self._build_toolbar()

        splitter = QSplitter(Qt.Orientation.Horizontal)
        root.addWidget(splitter, stretch=1)

        splitter.addWidget(self._build_left_panel())

        self.preview = PreviewWidget()
        splitter.addWidget(self.preview)
        splitter.setStretchFactor(0, 1)
        splitter.setStretchFactor(1, 2)
        splitter.setSizes([380, 820])

        root.addWidget(self._build_settings_panel())

        self.progress_bar = QProgressBar()
        self.progress_bar.setVisible(False)
        root.addWidget(self.progress_bar)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Ready")

    def _build_toolbar(self) -> None:
        tb = QToolBar("Main")
        tb.setIconSize(QSize(18, 18))
        tb.setMovable(False)
        self.addToolBar(tb)

        self.act_open = QAction("Open ZPL…", self)
        self.act_open.setShortcut("Ctrl+O")
        tb.addAction(self.act_open)

        tb.addSeparator()

        self.act_save_png = QAction("Save as PNG", self)
        self.act_save_png.setShortcut("Ctrl+S")
        self.act_save_png.setEnabled(False)
        tb.addAction(self.act_save_png)

        self.act_save_pdf = QAction("Save as PDF", self)
        self.act_save_pdf.setShortcut("Ctrl+Shift+S")
        self.act_save_pdf.setEnabled(False)
        tb.addAction(self.act_save_pdf)

        tb.addSeparator()

        self.act_batch = QAction("Batch Export Folder…", self)
        tb.addAction(self.act_batch)

    def _build_left_panel(self) -> QWidget:
        panel = QWidget()
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        self.drop_zone = DropZone()
        layout.addWidget(self.drop_zone)

        group = QGroupBox("ZPL Input")
        gl = QVBoxLayout(group)

        self.zpl_editor = QTextEdit()
        self.zpl_editor.setPlaceholderText(
            "Paste ZPL code here…\n\nExample:\n"
            "^XA\n^FO50,50\n^A0N,50,50\n^FDHello World^FS\n^XZ"
        )
        self.zpl_editor.setFontFamily("Courier New")
        self.zpl_editor.setFontPointSize(10)
        gl.addWidget(self.zpl_editor)

        btn_row = QHBoxLayout()
        self.btn_render = QPushButton("Render Preview")
        self.btn_render.setDefault(True)
        self.btn_clear = QPushButton("Clear")
        btn_row.addWidget(self.btn_render)
        btn_row.addWidget(self.btn_clear)
        gl.addLayout(btn_row)

        layout.addWidget(group, stretch=1)
        return panel

    def _build_settings_panel(self) -> QGroupBox:
        group = QGroupBox("Settings")
        outer = QHBoxLayout(group)

        form = QFormLayout()
        form.setHorizontalSpacing(8)

        self.dpi_combo = QComboBox()
        self.dpi_combo.addItems(["152", "203", "300", "600"])
        self.dpi_combo.setCurrentText("203")
        form.addRow("DPI:", self.dpi_combo)

        self.width_input = QLineEdit("4.0")
        self.width_input.setFixedWidth(55)
        form.addRow("Width (in):", self.width_input)

        self.height_input = QLineEdit("6.0")
        self.height_input.setFixedWidth(55)
        form.addRow("Height (in):", self.height_input)

        outer.addLayout(form)
        outer.addSpacing(24)

        out_row = QHBoxLayout()
        out_row.addWidget(QLabel("Output Folder:"))
        self.output_folder_input = QLineEdit()
        self.output_folder_input.setPlaceholderText("Default: same folder as input file")
        self.output_folder_input.setMinimumWidth(220)
        out_row.addWidget(self.output_folder_input)
        self.btn_browse = QPushButton("Browse…")
        self.btn_browse.setFixedWidth(70)
        out_row.addWidget(self.btn_browse)
        outer.addLayout(out_row)
        outer.addStretch()

        return group

    # ------------------------------------------------------------------
    # Signal wiring
    # ------------------------------------------------------------------

    def _connect_signals(self) -> None:
        self.drop_zone.files_dropped.connect(self._on_files_dropped)
        self.btn_render.clicked.connect(self._on_render_clicked)
        self.btn_clear.clicked.connect(self._on_clear_clicked)
        self.act_open.triggered.connect(self._on_open_file)
        self.act_save_png.triggered.connect(self._on_save_png)
        self.act_save_pdf.triggered.connect(self._on_save_pdf)
        self.act_batch.triggered.connect(self._on_batch_action)
        self.btn_browse.clicked.connect(self._on_browse_output)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_files_dropped(self, paths: list) -> None:
        if len(paths) == 1:
            p = Path(paths[0])
            if p.is_dir():
                self._start_batch(p)
                return
            if p.is_file():
                self._load_zpl_file(p)
                return
        # Multiple files — treat as batch regardless of extension
        files = [Path(p) for p in paths if Path(p).is_file()]
        if files:
            self._start_batch_from_file_list(files)

    def _on_open_file(self) -> None:
        paths, _ = QFileDialog.getOpenFileNames(
            self, "Open ZPL File(s)", "",
            "ZPL / Text Files (*.zpl *.txt);;All Files (*)"
        )
        if len(paths) == 1:
            self._load_zpl_file(Path(paths[0]))
        elif len(paths) > 1:
            self._start_batch_from_file_list([Path(p) for p in paths])

    def _load_zpl_file(self, path: Path) -> None:
        try:
            content = path.read_text(encoding="utf-8", errors="replace")
        except OSError as exc:
            self._show_error(f"Cannot read file:\n{exc}")
            return
        self._source_stem = path.stem
        self.zpl_editor.setPlainText(content)
        self.status_bar.showMessage(f"Loaded: {path.name}")
        self._on_render_clicked()

    def _on_render_clicked(self) -> None:
        zpl = self.zpl_editor.toPlainText().strip()
        if not zpl:
            self.status_bar.showMessage("No ZPL content to render.")
            return
        if self._render_thread and self._render_thread.isRunning():
            return

        dpi = int(self.dpi_combo.currentText())
        try:
            w, h = self._label_dimensions()
        except ValueError:
            w, h = 4.0, 6.0
        self.status_bar.showMessage("Rendering…")
        self.btn_render.setEnabled(False)

        self._render_thread = RenderThread(zpl, dpi, w, h, self._source_stem, self)
        self._render_thread.finished.connect(self._on_render_done)
        self._render_thread.error.connect(self._on_render_error)
        self._render_thread.start()

    def _on_render_done(self, png_paths: list) -> None:
        self._current_pngs = [Path(p) for p in png_paths]
        self._current_png = self._current_pngs[0]
        self.preview.load_image(self._current_png)
        self.act_save_png.setEnabled(True)
        self.act_save_pdf.setEnabled(True)
        self.btn_render.setEnabled(True)
        count = len(self._current_pngs)
        msg = (
            f"Rendered {count} page(s) — preview shows page 1"
            if count > 1
            else f"Rendered: {self._current_png}"
        )
        self.status_bar.showMessage(msg)
        logger.info("Render complete: %d page(s)", count)

    def _on_render_error(self, message: str) -> None:
        self.preview.show_error(message)
        self.act_save_png.setEnabled(False)
        self.act_save_pdf.setEnabled(False)
        self.btn_render.setEnabled(True)
        self.status_bar.showMessage("Render failed — see preview for details.")
        logger.error("Render failed: %s", message)

    def _on_clear_clicked(self) -> None:
        self.zpl_editor.clear()
        self.preview.clear()
        self._current_pngs = []
        self._current_png = None
        self._source_stem = "output"
        self.act_save_png.setEnabled(False)
        self.act_save_pdf.setEnabled(False)
        self.status_bar.showMessage("Cleared.")

    def _on_save_png(self) -> None:
        if not self._current_png or not self._current_png.exists():
            self._show_error("No rendered image to save.")
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save PNG", f"{self._source_stem}.png", "PNG Images (*.png)"
        )
        if not dest:
            return
        try:
            shutil.copy2(self._current_png, dest)
            self.status_bar.showMessage(f"Saved PNG: {dest}")
        except OSError as exc:
            self._show_error(f"Cannot save PNG:\n{exc}")

    def _on_save_pdf(self) -> None:
        if not self._current_pngs:
            self._show_error("No rendered image to save.")
            return
        dest, _ = QFileDialog.getSaveFileName(
            self, "Save PDF", f"{self._source_stem}.pdf", "PDF Files (*.pdf)"
        )
        if not dest:
            return
        try:
            w, h = self._label_dimensions()
            dpi = int(self.dpi_combo.currentText())
            PDFExporter().export_batch(self._current_pngs, Path(dest), w, h, dpi)
            pages = len(self._current_pngs)
            self.status_bar.showMessage(f"Saved PDF ({pages} page(s)): {dest}")
        except (ValueError, OSError) as exc:
            self._show_error(f"Cannot save PDF:\n{exc}")

    def _on_batch_action(self) -> None:
        folder = QFileDialog.getExistingDirectory(
            self, "Select Folder Containing ZPL Files"
        )
        if folder:
            self._start_batch(Path(folder))

    def _start_batch(self, input_folder: Path) -> None:
        output_folder = self._resolve_output_folder(input_folder)
        reply = self._ask_pdf_or_png(input_folder, output_folder)
        if reply is None:
            return
        self._run_batch(input_folder, output_folder, as_pdf=reply)

    def _start_batch_from_file_list(self, files: list) -> None:
        tmp_dir = Path(tempfile.mkdtemp(prefix="zpl_batch_"))
        for f in files:
            shutil.copy2(f, tmp_dir / f.name)
        default_out = files[0].parent
        output_folder = self._resolve_output_folder(default_out)
        reply = self._ask_pdf_or_png(tmp_dir, output_folder)
        if reply is None:
            shutil.rmtree(tmp_dir, ignore_errors=True)
            return
        self._run_batch(tmp_dir, output_folder, as_pdf=reply)

    def _run_batch(self, input_folder: Path, output_folder: Path, as_pdf: bool) -> None:
        try:
            w, h = self._label_dimensions()
        except ValueError:
            w, h = 4.0, 6.0

        dpi = int(self.dpi_combo.currentText())
        output_folder.mkdir(parents=True, exist_ok=True)

        self.progress_bar.setRange(0, 0)
        self.progress_bar.setVisible(True)
        self.status_bar.showMessage("Batch processing…")
        self.act_batch.setEnabled(False)

        self._batch_thread = BatchThread(
            input_folder, output_folder, dpi, as_pdf, w, h, self
        )
        self._batch_thread.progress.connect(self._on_batch_progress)
        self._batch_thread.finished.connect(self._on_batch_done)
        self._batch_thread.start()

    def _on_batch_progress(self, current: int, total: int) -> None:
        self.progress_bar.setRange(0, total)
        self.progress_bar.setValue(current)
        self.status_bar.showMessage(f"Processing {current}/{total}…")

    def _on_batch_done(self, succeeded: int, failed: int, log_path: str) -> None:
        self.progress_bar.setVisible(False)
        self.act_batch.setEnabled(True)

        summary = f"Batch complete: {succeeded} succeeded, {failed} failed."
        if failed > 0 and log_path:
            summary += f"\n\nFailed files logged to:\n{log_path}"
        QMessageBox.information(self, "Batch Export Complete", summary)
        self.status_bar.showMessage(f"Batch done — {succeeded} OK, {failed} failed.")
        logger.info("Batch done: %d OK, %d failed", succeeded, failed)

    def _on_browse_output(self) -> None:
        folder = QFileDialog.getExistingDirectory(self, "Select Output Folder")
        if folder:
            self.output_folder_input.setText(folder)

    # ------------------------------------------------------------------
    # Helpers
    # ------------------------------------------------------------------

    def _label_dimensions(self) -> tuple:
        """Return (width_inches, height_inches) from the settings inputs."""
        return float(self.width_input.text()), float(self.height_input.text())

    def _resolve_output_folder(self, fallback: Path) -> Path:
        text = self.output_folder_input.text().strip()
        return Path(text) if text else fallback

    def _ask_pdf_or_png(
        self, input_folder: Path, output_folder: Path
    ) -> Optional[bool]:
        """
        Ask the user whether to export as a multi-page PDF.

        Returns True for PDF, False for individual PNGs, None for Cancel.
        """
        reply = QMessageBox.question(
            self,
            "Batch Export Format",
            f"Source folder:\n{input_folder}\n\n"
            f"Output folder:\n{output_folder}\n\n"
            "Export as a single multi-page PDF?\n"
            "(Choose 'No' to export individual PNG files.)",
            QMessageBox.StandardButton.Yes
            | QMessageBox.StandardButton.No
            | QMessageBox.StandardButton.Cancel,
        )
        if reply == QMessageBox.StandardButton.Cancel:
            return None
        return reply == QMessageBox.StandardButton.Yes

    def _show_error(self, message: str) -> None:
        QMessageBox.critical(self, "Error", message)
        self.status_bar.showMessage(f"Error: {message}")
