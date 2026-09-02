from pathlib import Path

from PyInstaller.utils.hooks import collect_dynamic_libs, collect_submodules

ROOT = Path(SPEC).resolve().parent
MODEL_DIR = ROOT / 'resources' / 'models' / 'multilingual-e5-small-onnx'
SPRITE_DIR = ROOT / 'resources' / 'sprites'
CATALOG_ENDPOINT_FILE = ROOT / 'resources' / 'catalog_endpoint.txt'

if not (MODEL_DIR / 'model.onnx').is_file() or not (MODEL_DIR / 'tokenizer.json').is_file():
    raise SystemExit('Bundled E5 model files are missing; run tools/fetch_e5_model.py first.')

hidden = collect_submodules('bookeater.nlp')
binaries = collect_dynamic_libs('onnxruntime')
datas = [(str(MODEL_DIR), 'resources/models/multilingual-e5-small-onnx')]
if SPRITE_DIR.is_dir():
    datas.append((str(SPRITE_DIR), 'resources/sprites'))
if CATALOG_ENDPOINT_FILE.is_file():
    datas.append((str(CATALOG_ENDPOINT_FILE), 'resources'))

a = Analysis(
    ['bookeater_desktop.py'],
    pathex=[str(ROOT / 'src')],
    binaries=binaries,
    datas=datas,
    hiddenimports=hidden,
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    noarchive=False,
    optimize=0,
)
pyz = PYZ(a.pure)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='BookEater',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
)

coll = COLLECT(
    exe,
    a.binaries,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='BookEater',
)
