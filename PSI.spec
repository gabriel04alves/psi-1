# -*- mode: python ; coding: utf-8 -*-
# Portable PSI.spec — uses SPECPATH so paths work on any machine.
import sys
import os
from pathlib import Path
from PyInstaller.utils.hooks import collect_all, copy_metadata

HERE = Path(SPECPATH)

# ── Static data files bundled read-only ───────────────────────────────────────
datas = [
    (str(HERE / "streamlit_app.py"),                          "."),
    (str(HERE / "pages"),                                     "pages"),
    (str(HERE / "utils"),                                     "utils"),
    (str(HERE / "database"),                                  "database"),
    (str(HERE / "data" / "27002_2026.json"),                  "data"),
    (str(HERE / "data" / "27701_2026.json"),                  "data"),
    (str(HERE / "data" / "ABNT_NBR_ISO_IEC_27002_2022.pdf"),  "data"),
    (str(HERE / "data" / "ABNT_NBR_ISO_IEC_27701_2026.pdf"),  "data"),
    (str(HERE / "data" / "__init__.py"),                      "data"),
    (str(HERE / "data" / "iso27002_controls.py"),             "data"),
    (str(HERE / "data" / "iso27701_controls.py"),             "data"),
]
binaries = []

# ── Graphviz binaries (platform-specific, best-effort) ────────────────────────
if sys.platform == "win32":
    _gv_bin = os.environ.get("GRAPHVIZ_BIN", r"C:\Program Files\Graphviz\bin")
    if os.path.isdir(_gv_bin):
        for _f in Path(_gv_bin).glob("*.exe"):
            binaries.append((str(_f), "graphviz"))
        for _f in Path(_gv_bin).glob("*.dll"):
            binaries.append((str(_f), "graphviz"))
elif sys.platform == "darwin":
    for _prefix in ["/opt/homebrew", "/usr/local"]:
        _dot = f"{_prefix}/bin/dot"
        if os.path.exists(_dot):
            binaries.append((_dot, "."))
            _gvlib = f"{_prefix}/lib/graphviz"
            if os.path.isdir(_gvlib):
                binaries.append((_gvlib, "graphviz"))
            break
else:  # Linux
    for _dot in ["/usr/bin/dot", "/usr/local/bin/dot"]:
        if os.path.exists(_dot):
            binaries.append((_dot, "."))
            break
    for _gvlib in [
        "/usr/lib64/graphviz",
        "/usr/lib/graphviz",
        "/usr/lib/x86_64-linux-gnu/graphviz",
    ]:
        if os.path.isdir(_gvlib):
            binaries.append((_gvlib, "graphviz"))
            break

# ── Hidden imports ─────────────────────────────────────────────────────────────
hiddenimports = [
    "sqlite3", "csv", "io", "json", "re", "ast",
    "shutil", "tempfile", "argparse", "random",
    "collections", "contextlib", "threading", "webbrowser",
    "database.db",
    "data.iso27002_controls", "data.iso27701_controls",
    "utils.analytics", "utils.pdf_report",
    "utils.get_and_format_iso", "utils.gen_diagram",
    "pandas.core.arrays.arrow",
    "plotly.express", "plotly.graph_objects",
    "streamlit.runtime.scriptrunner.magic_funcs",
    "streamlit.web.cli",
]

# ── Collect packages ───────────────────────────────────────────────────────────
datas += copy_metadata("streamlit")

for _pkg in [
    "streamlit", "reportlab", "pdfplumber", "pdfminer",
    "plotly", "altair", "graphviz", "pygraphviz", "eralchemy2",
    "pandas", "numpy", "pyarrow", "PIL", "narwhals", "sqlalchemy",
]:
    _tmp = collect_all(_pkg)
    datas         += _tmp[0]
    binaries      += _tmp[1]
    hiddenimports += _tmp[2]

# ── Analysis ───────────────────────────────────────────────────────────────────
a = Analysis(
    [str(HERE / "run.py")],
    pathex=[str(HERE)],
    binaries=binaries,
    datas=datas,
    hiddenimports=hiddenimports,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[str(HERE / "_psi_runtime_hook.py")],
    excludes=["tkinter", "matplotlib", "IPython", "jupyter", "notebook"],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="PSI",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=True,   # set False to hide the terminal window after stabilization
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=None,
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name="PSI",
)
