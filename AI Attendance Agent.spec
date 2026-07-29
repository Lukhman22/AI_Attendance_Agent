# -*- mode: python ; coding: utf-8 -*-

from PyInstaller.utils.hooks import collect_data_files, collect_submodules, collect_dynamic_libs
import sys
import os
import platform

block_cipher = None

# Collect heavy libraries meticulously
hidden_imports = []
hidden_imports += collect_submodules('numpy')
hidden_imports += collect_submodules('pandas')
hidden_imports += collect_submodules('sqlalchemy')
hidden_imports += collect_submodules('fastapi')
hidden_imports += collect_submodules('pydantic')
hidden_imports += collect_submodules('uvicorn')
hidden_imports += collect_submodules('faster_whisper')
hidden_imports += collect_submodules('ctranslate2')
hidden_imports += collect_submodules('onnxruntime')
hidden_imports += collect_submodules('requests')
hidden_imports += collect_submodules('huggingface_hub')
hidden_imports += ['fitz', 'backend.app.models', 'backend.app.main', 'tkinter']

datas = []
# Ensure frontend static files are bundled
frontend_dist = os.path.join('frontend', 'dist')
if os.path.exists(frontend_dist):
    datas.append((frontend_dist, 'frontend/dist'))

# Ensure sample_data is bundled if present
if os.path.exists('sample_data'):
    datas.append(('sample_data', 'sample_data'))

# Collect data for specific libraries
datas += collect_data_files('faster_whisper')
datas += collect_data_files('ctranslate2')
datas += collect_data_files('onnxruntime')

binaries = []
binaries += collect_dynamic_libs('ctranslate2')
binaries += collect_dynamic_libs('onnxruntime')
binaries += collect_dynamic_libs('numpy')
binaries += collect_dynamic_libs('pandas')

a = Analysis(
    ['standalone.py'],
    pathex=[],
    binaries=binaries,
    datas=datas,
    hiddenimports=list(set(hidden_imports)),
    hookspath=[],
    hooksconfig={},
    runtime_hooks=[],
    excludes=[],
    win_no_prefer_redirects=False,
    win_private_assemblies=False,
    cipher=block_cipher,
    noarchive=False,
)

pyz = PYZ(a.pure, a.zipped_data, cipher=block_cipher)

exe = EXE(
    pyz,
    a.scripts,
    [],
    exclude_binaries=True,
    name='AI Attendance Agent',
    debug=False,
    bootloader_ignore_signals=False,
    strip=False,
    upx=True,
    console=False,
    disable_windowed_traceback=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon=os.path.join('frontend', 'public', 'favicon.ico') if platform.system() == 'Windows' else None
)

coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=False,
    upx=True,
    upx_exclude=[],
    name='AI Attendance Agent',
)

if platform.system() == 'Darwin':
    app = BUNDLE(
        coll,
        name='AI Attendance Agent.app',
        icon=None,
        bundle_identifier='com.company.aiattendanceagent',
        info_plist={
            'NSHighResolutionCapable': 'True',
            'LSBackgroundOnly': 'False'
        }
    )
