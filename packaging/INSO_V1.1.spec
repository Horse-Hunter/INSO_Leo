# PyInstaller onedir/windowed release. Runtime configuration and production data
# are intentionally absent; deploy those locally after the generic build.
from PyInstaller.utils.hooks import collect_all, collect_submodules
from pathlib import Path

repo_root = Path(SPECPATH).parent

datas = []
# The canonical Core Provider resolves this module beside _vault_backend.py.
# It contains no vault records; frozen mode must retain that sibling path.
datas.append((str(repo_root / "src" / "core" / "CredentialVault.psm1"), "src/core"))
binaries = []
hiddenimports = collect_submodules("src")
# Tcl/Tk lives in the base Python installation rather than this build venv.
# Pin its GUI entry points so PyInstaller's Tk hooks collect the runtime too.
hiddenimports += ["tkinter", "tkinter.ttk", "tkinter.messagebox"]
for package in (
    "customtkinter",
    "googleapiclient",
    "google_auth_oauthlib",
    "google.auth",
    "openpyxl",
    "playwright",
):
    package_datas, package_binaries, package_hiddenimports = collect_all(package)
    datas += [
        entry
        for entry in package_datas
        if "/vite/htmlReport/" not in entry[0].replace("\\", "/")
    ]
    binaries += package_binaries
    hiddenimports += package_hiddenimports
hiddenimports += collect_submodules(
    "websocket",
    filter=lambda name: not name.startswith("websocket.tests")
    and name != "websocket._wsdump",
)

a = Analysis(
    [str(repo_root / "scripts" / "windows_release_entry.py")],
    pathex=[str(repo_root)],
    binaries=binaries,
    datas=datas,
    hiddenimports=sorted(set(hiddenimports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=["pytest", "ruff"],
    noarchive=False,
    optimize=1,
)
# The bundled HTML trace viewer contains test/example token-shaped text and is
# not used by this read-only CDP client. Keep the Playwright Python/driver runtime.
a.datas = [
    entry
    for entry in a.datas
    if "/htmlReport/" not in entry[0].replace("\\", "/")
]
pyz = PYZ(a.pure)
exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name="INSO_V1.1",
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=False,
    console=False,
    disable_windowed_traceback=True,
    icon=str(repo_root / "packaging" / "assets" / "inso-v1.1.ico"),
)
coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=False,
    upx_exclude=[],
    name="INSO_V1.1",
)
