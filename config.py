import sys
import platform
import tempfile
from pathlib import Path

if getattr(sys, "_MEIPASS", None):
    BASE_DIR = Path(sys._MEIPASS)
else:
    BASE_DIR = Path(__file__).parent

_bin_name = "labelize.exe" if platform.system() == "Windows" else "labelize"
LABELIZE_BIN = BASE_DIR / "assets" / _bin_name
TEMP_DIR = Path(tempfile.gettempdir()) / "zpl_converter"
LOG_FILE = TEMP_DIR / "zpl_converter.log"
