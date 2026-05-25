import sys
import os
import threading
import time
import webbrowser
from pathlib import Path


def resource_path(*parts: str) -> str:
    base = Path(sys._MEIPASS) if getattr(sys, "frozen", False) else Path(__file__).parent
    return str(base.joinpath(*parts))


def _open_browser(url: str, delay: float) -> None:
    time.sleep(delay)
    webbrowser.open(url)


def main() -> None:
    port = int(os.environ.get("PSI_PORT", "8501"))
    url = f"http://localhost:{port}"
    app = resource_path("streamlit_app.py")

    threading.Thread(target=_open_browser, args=(url, 2.5), daemon=True).start()

    sys.argv = [
        "streamlit", "run", app,
        "--server.port", str(port),
        "--server.headless", "true",
        "--browser.gatherUsageStats", "false",
        "--global.developmentMode", "false",
    ]

    from streamlit.web import cli as stcli
    sys.exit(stcli.main())


if __name__ == "__main__":
    main()
