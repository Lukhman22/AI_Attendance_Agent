import sys
modules = ["numpy", "pandas", "sqlalchemy", "fastapi", "uvicorn", "ctranslate2", "onnxruntime", "fitz", "faster_whisper", "backend.app.main"]

for m in modules:
    # Clear sys.modules of pkg_resources to see if this specific module loads it
    sys.modules.pop('pkg_resources', None)
    try:
        __import__(m)
        if 'pkg_resources' in sys.modules:
            print(f"{m} loaded pkg_resources!")
    except Exception as e:
        print(f"{m} failed: {e}")
