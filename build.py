import os
import sys
import subprocess
import shutil
import platform
import tempfile
from pathlib import Path

def run_command(command, cwd=None, exit_on_error=True):
    print(f"Running: {command}")
    result = subprocess.run(command, shell=True, cwd=cwd, text=True)
    if result.returncode != 0 and exit_on_error:
        print(f"Error executing: {command}")
        sys.exit(1)
    return result

def clean_artifacts():
    print("--- Cleaning Stale Artifacts ---")
    dirs_to_clean = ["build", "dist", "__pycache__"]
    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f"Removing {d}...")
            shutil.rmtree(d, ignore_errors=True)
    
    # We do NOT remove the spec file because we rely on the manual AI Attendance Agent.spec!

def check_bundle_size(app_path):
    print("\n--- Verifying Bundle Size ---")
    total_size = 0
    for dirpath, dirnames, filenames in os.walk(app_path):
        for f in filenames:
            fp = os.path.join(dirpath, f)
            if not os.path.islink(fp):
                total_size += os.path.getsize(fp)
    size_mb = total_size / (1024 * 1024)
    print(f"Bundle size: {size_mb:.2f} MB")
    
    if size_mb < 200:
        print("CRITICAL ERROR: Bundle size shrank massively! This means PyInstaller missed heavy dependencies (NumPy, Faster Whisper, etc.).")
        print("Please review the PyInstaller spec and requirements versions (NumPy must be 1.x).")
        sys.exit(1)
    return size_mb

def verify_imports(executable_path):
    print("\n--- Verifying Imports Inside Packaged App ---")
    cmd = f'"{executable_path}" --verify-imports'
    result = subprocess.run(cmd, shell=True, capture_output=True, text=True)
    if "IMPORTS_OK" in result.stdout:
        print("All required dependencies successfully imported inside the bundle!")
    else:
        print(f"CRITICAL ERROR: Import verification failed!\nSTDOUT:\n{result.stdout}\nSTDERR:\n{result.stderr}")
        sys.exit(1)

def main():
    print("========================================")
    print("Building AI Attendance Agent Desktop App")
    print("========================================")

    if sys.version_info >= (3, 13):
        print(f"CRITICAL ERROR: Python {platform.python_version()} detected. Python >=3.13 is incompatible with PyInstaller packaging for this app. Please use Python 3.12.")
        sys.exit(1)

    root_dir = Path(__file__).resolve().parent
    frontend_dir = root_dir / "frontend"
    
    clean_artifacts()

    # 1. Build frontend
    print("\n--- 1. Building Frontend ---")
    if not (frontend_dir / "node_modules").exists():
        run_command("npm install", cwd=frontend_dir)
    run_command("npm run build", cwd=frontend_dir)
    
    if not (frontend_dir / "dist").exists():
        print("Frontend build failed: dist directory not found.")
        sys.exit(1)

    # 2. Package with PyInstaller using the SPEC file
    print("\n--- 2. Packaging Backend & Frontend ---")
    run_command("pip install pyinstaller==6.9.0")
    
    # We strictly use the .spec file
    run_command("pyinstaller --noconfirm \"AI Attendance Agent.spec\"", cwd=root_dir)
    
    print("\n--- 3. Post-build Steps ---")
    if platform.system() == "Darwin":
        app_path = root_dir / "dist" / "AI Attendance Agent.app"
        executable_path = app_path / "Contents" / "MacOS" / "AI Attendance Agent"
        
        print(f"Build complete! App located at: {app_path}")
        
        check_bundle_size(app_path)
        verify_imports(executable_path)
        
        print("\n--- 4. Code Signing and Verification ---")
        tmp_build_dir = Path(tempfile.gettempdir()) / "AIA_Build"
        if tmp_build_dir.exists():
            shutil.rmtree(tmp_build_dir, ignore_errors=True)
        tmp_build_dir.mkdir(parents=True)
        
        isolated_app_path = tmp_build_dir / "AI Attendance Agent.app"
        print(f"Isolating app to {isolated_app_path} for code signing...")
        run_command(f'cp -R "{app_path}" "{isolated_app_path}"')
        
        # Clean detritus
        run_command(f'find "{isolated_app_path}" -name "__pycache__" -type d -exec rm -rf {{}} +')
        run_command(f'find "{isolated_app_path}" -name ".DS_Store" -delete')
        
        # Strip extended attributes safely (symlink safe)
        run_command(f'find "{isolated_app_path}" -exec xattr -cs {{}} +')
        
        # Sign the app
        run_command(f'codesign --force --deep --sign - "{isolated_app_path}"')
        run_command(f'codesign --verify --deep --strict --verbose=4 "{isolated_app_path}"')
        
        print("Testing Gatekeeper acceptance...")
        spctl_result = subprocess.run(f'spctl --assess --type execute --verbose=4 "{isolated_app_path}"', shell=True)
        if spctl_result.returncode != 0:
            print("Notice: spctl rejected the app (expected for ad-hoc).")
        
        print("\n--- 5. Creating DMG ---")
        isolated_dmg_path = tmp_build_dir / "AI Attendance Agent.dmg"
        run_command(f'hdiutil create -volname "AI Attendance Agent" -srcfolder "{isolated_app_path}" -ov -format UDZO "{isolated_dmg_path}"')
        
        dmg_path = root_dir / "dist" / "AI Attendance Agent.dmg"
        run_command(f'cp "{isolated_dmg_path}" "{dmg_path}"')
        
        print(f"DMG created successfully: {dmg_path}")
        shutil.rmtree(tmp_build_dir, ignore_errors=True)
        
    else:
        dist_path = root_dir / "dist" / "AI Attendance Agent"
        executable_path = dist_path / "AI Attendance Agent.exe"
        
        print(f"Build complete! Folder located at: {dist_path}")
        check_bundle_size(dist_path)
        verify_imports(executable_path)
        
        print("\n--- 4. Creating Windows Installer ---")
        run_command('iscc "setup.iss"')

if __name__ == "__main__":
    main()
