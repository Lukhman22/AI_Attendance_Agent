# Packaging & Distribution Guide

This document explains how to build, package, test, and distribute the AI Attendance Agent as a standalone desktop application for both macOS and Windows. 

The application utilizes a robust multi-stage pipeline that compiles the React frontend, packages the FastAPI backend using PyInstaller, and bundles heavy AI libraries and static assets into a single distributable artifact.

---

## 1. Prerequisites

Before generating a build, ensure the host machine has the following tools installed:

### Global Requirements
- **Python**: Version `3.12` strictly required. (Python 3.13+ contains structural changes incompatible with PyInstaller for this specific architecture).
- **Node.js & npm**: Required to compile the React frontend.

### macOS Specific Requirements
- **Xcode Command Line Tools**: Required for `codesign` and `hdiutil` commands. (Install via `xcode-select --install`).

### Windows Specific Requirements
- **Inno Setup**: Required to compile the `setup.iss` script into a `Setup.exe` installer. Download from [jrsoftware.org](https://jrsoftware.org/isinfo.php). Ensure `iscc` is accessible in your system `PATH`.

---

## 2. Build Pipeline Overview

The packaging process is fully automated via `build.py`, which is invoked by platform-specific wrapper scripts. The pipeline executes the following sequence:

1. Validates the Python version.
2. Cleans stale build artifacts (`dist/`, `build/`, `__pycache__`).
3. Compiles the React SPA (`npm run build`).
4. Invokes PyInstaller utilizing `AI Attendance Agent.spec`.
5. Validates the resulting bundle size (ensuring AI models weren't omitted).
6. Executes a dry-run test (`--verify-imports`) against the compiled binary.
7. Generates the final platform-specific distributable (DMG or EXE).

---

## 3. How to Build

### macOS
Open a terminal at the project root and execute the wrapper script:

```bash
chmod +x package_mac.sh
./package_mac.sh
```

### Windows
Open a Command Prompt or PowerShell terminal at the project root and execute the batch script:

```cmd
package_windows.bat
```

*(Note: Both scripts automatically provision an isolated Python virtual environment (`venv`) and install all required dependencies from `requirements.txt` before initiating the build).*

---

## 4. Output Locations

Once the build pipeline completes, the final artifacts will be placed in the `dist/` directory at the project root.

- **macOS:** `dist/AI Attendance Agent.dmg` (A disk image containing the `.app` bundle).
- **Windows:** `dist/AI Attendance Agent Setup.exe` (A standalone Inno Setup installer).

*Note: The intermediate PyInstaller folders are also preserved in `dist/` for debugging purposes.*

---

## 5. Testing the Build

Before distributing an artifact, you should verify its integrity locally.

1. **Clean Installation**: Install the application using the DMG or Setup.exe.
2. **Launch Verification**: Double-click the application icon.
   - You should immediately see the Tkinter splash screen.
   - Your default web browser should open to `http://127.0.0.1:<random-port>`.
3. **Database Check**: Ensure the application loads correctly. The local SQLite database is automatically generated at `~/.ai_attendance_agent/database.sqlite3`.
4. **Shutdown Verification**: Click the Power/Shutdown icon in the top right of the application header to verify the Uvicorn server shuts down cleanly without leaving background zombie processes.

---

## 6. Known Limitations

### macOS Gatekeeper
The build script performs **ad-hoc code signing** (`codesign --sign -`). Because it does not utilize a paid Apple Developer ID certificate, Gatekeeper will flag the application as "damaged" or from an "unidentified developer" when downloaded from the internet.
- **Workaround:** Users must right-click the application and select "Open," or manually strip quarantine attributes via terminal: `xattr -cr "/Applications/AI Attendance Agent.app"`.

### Windows SmartScreen
The generated executable and installer lack an **Extended Validation (EV) Code Signing Certificate**. Windows Defender will issue a bright blue SmartScreen warning stating "Windows protected your PC".
- **Workaround:** Users must click **"More info" -> "Run anyway"**.

---

## 7. Troubleshooting

**Error: "Bundle size shrank massively!"**
- **Cause:** PyInstaller failed to correctly collect heavy data files or dynamic libraries (often `onnxruntime`, `ctranslate2`, or `faster-whisper`).
- **Fix:** Ensure you are using Python 3.12. Check that the PyInstaller version is locked to `6.9.0` as specified in `build.py`.

**Error: `iscc` is not recognized (Windows)**
- **Cause:** Inno Setup is not installed, or the `iscc` compiler is not in your system environment variables.
- **Fix:** Install Inno Setup and add its installation path (e.g., `C:\Program Files (x86)\Inno Setup 6`) to your `PATH`.

**Server ghost processes / Application won't start on same port**
- **Cause:** The application utilizes dynamic port allocation to avoid collisions, but if a previous instance did not shut down gracefully, you may experience performance anomalies.
- **Fix:** Always use the Shutdown button in the UI. If a zombie process exists, terminate `AI Attendance Agent` via Activity Monitor (macOS) or Task Manager (Windows).

---

## 8. Release Procedures (Optional Enhancements)

If the application is ready for commercial distribution to enterprise clients, you **must** eliminate the Gatekeeper and SmartScreen security warnings.

1. **Procure Certificates**: Obtain an Apple Developer ID Application certificate and a Windows Code Signing Certificate.
2. **macOS Modification**: Update `build.py` to sign using the Apple certificate identity, and integrate `xcrun notarytool` to upload the bundle for Apple's automated malware scan. Staple the resulting ticket to the `.app` using `xcrun stapler`.
3. **Windows Modification**: Update `build.py` to invoke `signtool.exe sign /tr http://timestamp.digicert.com /td sha256 /fd sha256 /a "dist\AI Attendance Agent.exe"` prior to Inno Setup, and run it again on the final `Setup.exe`.
