import sys
import os
print(f"Frozen: {getattr(sys, 'frozen', False)}")
if getattr(sys, 'frozen', False):
    print(f"MEIPASS: {sys._MEIPASS}")
    print(f"Exe dir: {os.path.dirname(sys.executable)}")
