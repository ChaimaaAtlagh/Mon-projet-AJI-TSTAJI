# PyInstaller onedir: exe séparé de ses bibliothèques pour une distribution plus simple.
from pathlib import Path
import os
import sys
from glob import glob

from PyInstaller.utils.hooks import collect_data_files


ROOT = Path(SPECPATH).resolve()
icon_path = ROOT / "app" / "assets" / "AJI_TSTAJI.ico"
if not icon_path.is_file():
    raise SystemExit(f"Icône Windows introuvable : {icon_path}")
datas = [
    (str(ROOT / "data" / "cleaned" / "data_nettoyee.xlsx"), "data/cleaned"),
]
api_config_file = os.environ.get("AJI_API_CONFIG_FILE")
if api_config_file:
    config_path = Path(api_config_file).resolve()
    if not config_path.is_file():
        raise SystemExit(f"Configuration API de build introuvable : {config_path}")
    datas.append((str(config_path), "config"))
assets_root = ROOT / "app" / "assets"
for asset in assets_root.rglob("*"):
    if asset.is_file():
        destination = Path("app/assets") / asset.relative_to(assets_root).parent
        datas.append((str(asset), str(destination)))

# CTk et Matplotlib chargent des thèmes, polices et ressources à l'exécution.
datas += collect_data_files("customtkinter")
datas += collect_data_files("matplotlib")

# L'installation Python de construction peut ne pas exposer TclTkInfo à
# PyInstaller. Les chemins varient entre Python.org et Anaconda.
tcl_init_candidates = [
    Path(path) for pattern in (
        Path(sys.base_prefix) / "tcl" / "tcl*" / "init.tcl",
        Path(sys.base_prefix) / "Library" / "lib" / "tcl*" / "init.tcl",
    ) for path in glob(str(pattern))
]
tk_index_candidates = [
    Path(path) for pattern in (
        Path(sys.base_prefix) / "tcl" / "tk*" / "pkgIndex.tcl",
        Path(sys.base_prefix) / "Library" / "lib" / "tk*" / "pkgIndex.tcl",
    ) for path in glob(str(pattern))
]
if not tcl_init_candidates or not tk_index_candidates:
    raise SystemExit(f"Scripts Tcl/Tk manquants pour l'interpréteur {sys.executable}")

for source_root, destination_root in (
    (tcl_init_candidates[0].parent, "_tcl_data"),
    (tk_index_candidates[0].parent, "_tk_data"),
):
    for resource in source_root.rglob("*"):
        if resource.is_file():
            destination = Path(destination_root) / resource.relative_to(source_root).parent
            datas.append((str(resource), str(destination)))

a = Analysis(
    [str(ROOT / "app" / "main.py")],
    pathex=[str(ROOT)],
    binaries=[],
    datas=datas,
    hiddenimports=[
        "_tkinter",
        "tkinter",
        "tkinter.constants",
        "tkinter.filedialog",
        "tkinter.font",
        "tkinter.messagebox",
        "tkinter.simpledialog",
        "tkinter.ttk",
        "matplotlib.backends.backend_tkagg",
        "matplotlib.backends.backend_agg",
        "PIL._tkinter_finder",
        # Le chatbot charge le SDK OpenAI-compatible utilisé par Groq.
        # Les imports explicites protègent le module et sa ressource Chat
        # contre les exclusions lors de l'analyse PyInstaller.
        "openai",
        "openai._client",
        "openai.resources.chat",
        "openai.resources.chat.completions",
    ],
    hookspath=[str(ROOT / "deployment" / "pyinstaller_hooks")],
    hooksconfig={},
    runtime_hooks=[
        str(ROOT / "deployment" / "pyinstaller_hooks" / "runtime" / "aji_tcltk.py"),
    ],
    excludes=[],
    noarchive=False,
    optimize=1,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name="AJI_TSTAJI_FINAL",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=str(icon_path),
)
