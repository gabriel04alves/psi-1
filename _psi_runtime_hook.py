import sys
import os
from pathlib import Path

if getattr(sys, "frozen", False):
    if sys.platform == "win32":
        _base = Path(os.environ.get("APPDATA", str(Path.home())))
    elif sys.platform == "darwin":
        _base = Path.home() / "Library" / "Application Support"
    else:  # Linux / BSD
        _base = Path(os.environ.get("XDG_DATA_HOME", str(Path.home() / ".local" / "share")))

    _data_dir = _base / "PSI"
    _data_dir.mkdir(parents=True, exist_ok=True)
    os.environ["PSI_DATA_DIR"] = str(_data_dir)

    os.environ.setdefault("STREAMLIT_BROWSER_GATHER_USAGE_STATS", "false")
    os.environ.setdefault("STREAMLIT_SERVER_HEADLESS", "true")
    os.environ["STREAMLIT_GLOBAL_DEVELOPMENT_MODE"] = "false"
