import os
import sys

site_packages = "venv/lib/python3.12/site-packages"
for root, dirs, files in os.walk(site_packages):
    for f in files:
        if f.endswith('.py'):
            try:
                with open(os.path.join(root, f), 'r', encoding='utf-8') as file:
                    if 'pkg_resources' in file.read():
                        print(f"Found in {os.path.join(root, f)}")
            except Exception:
                pass
