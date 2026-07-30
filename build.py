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
    dirs_to_clean = ["build", "dist", "__pycache__", "frontend/src-tauri/target"]
    for d in dirs_to_clean:
        if os.path.exists(d):
            print(f"Removing {d}...")
            shutil.rmtree(d, ignore_errors=True)

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
    
    if result.returncode == 0 and "IMPORT_FAILED" not in result.stdout and "IMPORT_FAILED" not in result.stderr:
        print("All required dependencies successfully imported inside the bundle!")
        if result.stderr.strip():
            print(f"[Warning] STDERR during verification:\n{result.stderr.strip()}")
    else:
        print(f"CRITICAL ERROR: Import verification failed!")
        print(f"Return Code: {result.returncode}")
        print(f"STDOUT:\n{result.stdout}")
        print(f"STDERR:\n{result.stderr}")
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

    # 1. Package Backend with PyInstaller
    print("\n--- 1. Packaging Backend ---")
    run_command('pip install --upgrade "setuptools<70.0.0" pyinstaller==6.9.0')
    run_command("pyinstaller --noconfirm backend.spec", cwd=root_dir)
    
    # 2. Build Tauri App
    print("\n--- 2. Building Desktop App (Tauri) ---")
    if not (frontend_dir / "node_modules").exists():
        run_command("npm install", cwd=frontend_dir)
    
    if platform.system() == "Darwin":
        run_command("npx tauri build --bundles app", cwd=frontend_dir)
    else:
        run_command("npx tauri build", cwd=frontend_dir)
    
    print("\n--- 3. Post-build Steps ---")
    if platform.system() == "Darwin":
        app_path = frontend_dir / "src-tauri" / "target" / "release" / "bundle" / "macos" / "AI Attendance Agent.app"
        dmg_path = frontend_dir / "src-tauri" / "target" / "release" / "bundle" / "dmg" / "AI Attendance Agent_0.1.0_aarch64.dmg"
        if not dmg_path.exists():
            dmg_path = frontend_dir / "src-tauri" / "target" / "release" / "bundle" / "dmg" / "AI Attendance Agent_1.0.0_aarch64.dmg"
            
        print(f"Build complete! Original App located at: {app_path}")
        
        # 4. Isolated macOS Signing
        print("\n--- 4. Isolated macOS Deep Signing ---")
        tmp_dir = Path("/tmp/ai_attendance_packaging")
        if tmp_dir.exists():
            shutil.rmtree(tmp_dir)
        tmp_dir.mkdir(parents=True)
        
        # Copy without symlinks/extended attributes interference
        run_command(f'cp -R "{app_path}" "{tmp_dir}/AI Attendance Agent.app"')
        target_app = tmp_dir / "AI Attendance Agent.app"
        
        # Remove any detritus
        run_command(f'find "{target_app}" -name ".DS_Store" -delete')
        run_command(f'xattr -cr "{target_app}"', exit_on_error=False)
        
        sign_id = os.environ.get("APPLE_SIGNING_IDENTITY", "-")
        
        # 4.1 Sign all dynamic libraries and shared objects
        run_command(f'find "{target_app}" -type f \\( -name "*.dylib" -o -name "*.so" \\) -exec codesign --force --sign "{sign_id}" --options runtime {{}} \\;')
        
        # 4.2 Sign embedded Python runtime inside PyInstaller _internal
        run_command(f'find "{target_app}/Contents/Resources/backend/_internal" -type f -name "Python*" -exec codesign --force --sign "{sign_id}" --options runtime {{}} \\;', exit_on_error=False)
        run_command(f'find "{target_app}/Contents/Resources/backend/_internal" -type f -name "base_library.zip" -exec codesign --force --sign "{sign_id}" --options runtime {{}} \\;', exit_on_error=False)

        # 4.3 Sign the backend executable sidecar
        run_command(f'codesign --force --sign "{sign_id}" --options runtime "{target_app}/Contents/Resources/backend/backend"')
        
        # 4.4 Sign Tauri Frameworks and main MacOS binary
        run_command(f'find "{target_app}/Contents/Frameworks" -type f -exec codesign --force --sign "{sign_id}" --options runtime {{}} \\;', exit_on_error=False)
        run_command(f'find "{target_app}/Contents/MacOS" -type f -exec codesign --force --sign "{sign_id}" --options runtime {{}} \\;')
        
        # 4.5 Sign the outer .app bundle WITHOUT --deep
        run_command(f'codesign --force --sign "{sign_id}" --strict --options runtime "{target_app}"')
        
        # 4.6 Verify the signatures
        run_command(f'codesign --verify --deep --strict --verbose=4 "{target_app}"')
        
        # Note: spctl --assess only passes if signed with a real Developer ID, so we don't fail the build on it if using ad-hoc (-)
        if sign_id != "-":
            run_command(f'spctl --assess --type execute --verbose "{target_app}"')
        
        # Package into DMG using hdiutil directly
        print("\n--- 5. Creating Distributable DMG ---")
        final_dmg = root_dir / "dist" / "AI Attendance Agent.dmg"
        if final_dmg.exists():
            final_dmg.unlink()
        
        run_command(f'hdiutil create -volname "AI Attendance Agent" -srcfolder "{tmp_dir}" -ov -format UDZO "{final_dmg}"')
        
        # Notarization (if credentials provided)
        apple_id = os.environ.get("APPLE_ID")
        apple_password = os.environ.get("APPLE_PASSWORD")
        apple_team_id = os.environ.get("APPLE_TEAM_ID")
        
        if sign_id != "-" and apple_id and apple_password and apple_team_id:
            print("\n--- 6. Apple Notarization ---")
            run_command(f'xcrun notarytool submit "{final_dmg}" --apple-id "{apple_id}" --password "{apple_password}" --team-id "{apple_team_id}" --wait')
            run_command(f'xcrun stapler staple "{final_dmg}"')
            print("Notarization and stapling complete.")
        
        print(f"\nArtifacts perfectly signed and packaged to dist/")
    else:
        # Windows
        installer_path = frontend_dir / "src-tauri" / "target" / "release" / "bundle" / "nsis" / "AI Attendance Agent_1.0.0_x64-setup.exe"
        if installer_path.exists():
            shutil.copy(str(installer_path), str(root_dir / "dist" / "AI Attendance Agent Setup.exe"))
            print(f"Installer copied to dist/")

if __name__ == "__main__":
    main()
