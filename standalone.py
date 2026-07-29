import os
import sys
import time
import socket
import threading
import webbrowser
import uvicorn
import httpx
from pathlib import Path

# Ensure paths are correct for PyInstaller MEIPASS
if getattr(sys, 'frozen', False):
    # PyInstaller creates a temp folder and stores path in _MEIPASS
    base_path = sys._MEIPASS
else:
    base_path = os.path.dirname(os.path.abspath(__file__))

# Make sure backend is in the path
sys.path.insert(0, os.path.join(base_path, 'backend'))

# Redirect stdout and stderr to a log file if frozen
if getattr(sys, 'frozen', False) and "--verify-imports" not in sys.argv:
    log_dir = Path.home() / ".ai_attendance_agent" / "logs"
    log_dir.mkdir(parents=True, exist_ok=True)
    log_file = open(log_dir / "app.log", "a", encoding="utf-8")
    sys.stdout = log_file
    sys.stderr = log_file

def run_splash():
    try:
        import tkinter as tk
        import threading
        root = tk.Tk()
        root.title("Starting")
        root.overrideredirect(True)
        root.attributes("-topmost", True)
        
        w, h = 320, 100
        sw, sh = root.winfo_screenwidth(), root.winfo_screenheight()
        root.geometry(f"{w}x{h}+{int(sw/2-w/2)}+{int(sh/2-h/2)}")
        
        frame = tk.Frame(root, bg="#ffffff", highlightbackground="#1e3a8a", highlightthickness=2)
        frame.pack(expand=True, fill="both")
        
        lbl = tk.Label(frame, text="Starting AI Attendance Agent...\n\nPlease wait.", bg="#ffffff", font=("Helvetica", 13), fg="#1e293b")
        lbl.pack(expand=True)
        
        def wait_stdin():
            try:
                sys.stdin.read()
            except: pass
            finally:
                root.quit()
        threading.Thread(target=wait_stdin, daemon=True).start()
        
        root.mainloop()
    except Exception:
        pass
    sys.exit(0)

if len(sys.argv) > 1 and sys.argv[1] == "--splash":
    run_splash()

if len(sys.argv) > 1 and sys.argv[1] == "--verify-imports":
    modules = [
        "numpy",
        "pandas",
        "sqlalchemy",
        "fastapi",
        "uvicorn",
        "ctranslate2",
        "onnxruntime",
        "fitz",
        "faster_whisper",
        "backend.app.main"
    ]
    import traceback
    for m in modules:
        try:
            print(f"Checking {m}...")
            __import__(m)
            print("OK")
        except Exception as e:
            print(f"FAILED MODULE: {m}")
            print(f"Exception: {e}")
            print(f"Traceback:\n{traceback.format_exc()}")
            sys.exit(1)
    print("IMPORTS_OK")
    sys.exit(0)

def get_free_port():
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.bind(('', 0))
        s.listen(1)
        port = s.getsockname()[1]
    return port

def wait_for_server(port: int):
    url = f"http://127.0.0.1:{port}/health"
    timeout = 180
    start_time = time.time()
    
    import subprocess
    splash_proc = None
    try:
        cmd = [sys.executable, "--splash"] if getattr(sys, 'frozen', False) else [sys.executable, __file__, "--splash"]
        splash_proc = subprocess.Popen(cmd, stdin=subprocess.PIPE, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
    except Exception as e:
        print(f"[Startup] Could not launch splash: {e}")
    
    print("[Startup] Waiting for health endpoint")
    while time.time() - start_time < timeout:
        try:
            with httpx.Client(timeout=1.0) as client:
                response = client.get(url)
                if response.status_code == 200:
                    print("[Startup] Server is healthy! Opening browser...")
                    if splash_proc and splash_proc.stdin:
                        try:
                            splash_proc.stdin.close()
                        except: pass
                    webbrowser.open(f"http://127.0.0.1:{port}")
                    return
        except Exception:
            pass
        time.sleep(0.5)
        
    if splash_proc and splash_proc.stdin:
        try:
            splash_proc.stdin.close()
        except: pass
    print("[Startup] Timeout waiting for health endpoint.", file=sys.stderr)
    
def show_error_dialog(title, message, exc_info=None):
    try:
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw() # Hide the main window
        full_msg = message
        if exc_info:
            full_msg += f"\n\nDetails:\n{exc_info}"
        messagebox.showerror(title, full_msg)
        root.destroy()
    except Exception:
        # Fallback if tkinter is not available (though it should be in standard python)
        pass
    print(f"{title}: {message}", file=sys.stderr)
    if exc_info:
        print(f"Details: {exc_info}", file=sys.stderr)

def main():
    try:
        print("[Startup] Application launched")
        
        if getattr(sys, 'frozen', False):
            print("[Startup] Frozen mode detected")
            print(f"[Startup] Base path resolved: {sys._MEIPASS}")
        else:
            print("[Startup] Frozen mode NOT detected (running from script)")
        
        print("[Startup] Sys.path updated")
        
        lock_file = Path.home() / ".ai_attendance_agent" / "active_port.txt"
        lock_file.parent.mkdir(parents=True, exist_ok=True)
        
        if lock_file.exists():
            try:
                with open(lock_file, "r") as f:
                    saved_port = int(f.read().strip())
                
                # Check if the server is actually alive
                with httpx.Client(timeout=1.0) as client:
                    resp = client.get(f"http://127.0.0.1:{saved_port}/health")
                    if resp.status_code == 200:
                        print(f"[Startup] App already running on port {saved_port}. Focusing browser.")
                        import webbrowser
                        webbrowser.open(f"http://127.0.0.1:{saved_port}")
                        sys.exit(0)
            except Exception:
                # Stale lock file, ignore and overwrite
                pass

        print("[Startup] Importing backend.app.main")
        import backend.app.main
        print("[Startup] Backend import successful")
        
        print("[Startup] Finding free port")
        port = get_free_port()
        
        # Save the active port
        with open(lock_file, "w") as f:
            f.write(str(port))

        
        print("[Startup] Starting health monitor")
        threading.Thread(target=wait_for_server, args=(port,), daemon=True).start()
        
        print("[Startup] Launching Uvicorn")
        uvicorn.run(
            backend.app.main.app,
            host="127.0.0.1",
            port=port,
            log_level="error", # Suppress dev logs
            workers=1,
        )
    except Exception as e:
        import traceback
        exc_str = traceback.format_exc()
        traceback.print_exc()
        show_error_dialog(
            "Application Startup Failed",
            f"Unable to initialize AI Attendance Agent.\nException: {type(e).__name__}: {str(e)}",
            exc_info=exc_str
        )
        raise

if __name__ == "__main__":
    # Windows freeze support
    import multiprocessing
    multiprocessing.freeze_support()
    
    main()
