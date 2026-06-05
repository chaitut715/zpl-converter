import sys
import logging
import platform

from PyQt6.QtWidgets import QApplication, QMessageBox

from config import TEMP_DIR, LOG_FILE, LABELIZE_BIN
from ui.main_window import MainWindow


def setup_logging() -> None:
    """Configure file + console logging."""
    TEMP_DIR.mkdir(parents=True, exist_ok=True)
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        handlers=[
            logging.FileHandler(LOG_FILE, encoding="utf-8"),
            logging.StreamHandler(sys.stdout),
        ],
    )


def check_dependencies() -> bool:
    """Return False if the labelize binary is missing."""
    return LABELIZE_BIN.exists()


def main() -> None:
    """Application entry point."""
    setup_logging()
    logger = logging.getLogger(__name__)

    app = QApplication(sys.argv)
    app.setApplicationName("ZPL Converter")
    app.setApplicationVersion("1.0.0")
    app.setOrganizationName("ZPL Converter")

    if not check_dependencies():
        QMessageBox.critical(
            None,
            "Missing Binary",
            f"labelize binary not found at:\n{LABELIZE_BIN}\n\n"
            "Download the appropriate binary from:\n"
            "https://github.com/GOODBOY008/labelize/releases\n\n"
            "Place it in the assets/ folder and restart the application.",
        )
        sys.exit(1)

    try:
        window = MainWindow()
        window.show()
        logger.info("ZPL Converter started")
        sys.exit(app.exec())
    except Exception as exc:
        logger.exception("Unhandled exception at top level")
        QMessageBox.critical(
            None,
            "Unexpected Error",
            f"An unexpected error occurred:\n\n{exc}\n\n"
            f"Check the log file for details:\n{LOG_FILE}",
        )
        sys.exit(1)


if __name__ == "__main__":
    main()
