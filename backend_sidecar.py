import sys
import os
import socket
import threading
import uvicorn
from pathlib import Path

# Ensure paths are correct for PyInstaller MEIPASS
if getattr(sys, 'frozen', False):
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

sys.path.insert(0, os.path.join(base_path, 'backend'))

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def main():
    port = get_free_port()
    
    # Tauri relies on reading stdout to get the backend port
    print(f"__TAURI_BACKEND_PORT__={port}", flush=True)

    # Disable default browser launching logic entirely
    # The application is purely headless backend now
    
    import backend.app.main
    uvicorn.run(
        backend.app.main.app,
        host="127.0.0.1",
        port=port,
        log_level="error",
        workers=1,
    )

if __name__ == "__main__":
    import multiprocessing
    multiprocessing.freeze_support()
    main()
