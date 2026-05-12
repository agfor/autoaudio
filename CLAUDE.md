# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

AutoAudio is a PySide6-based audio routing application that automatically routes audio from an input device to either a primary or fallback output device. It includes optional volume boosting functionality and runs as a system tray application on Windows/Linux.

## Architecture

The application uses a **multi-threaded architecture** with Qt signals for communication:

- **main.py**: Contains the `AutoAudio` GUI class (QMainWindow) that runs on the main thread
- **router.py**: Contains the `AutoAudioRouter` class (QObject) that handles audio processing and runs on a separate QThread

### Thread Communication

All communication between the UI thread and the audio router thread happens via Qt signals:
- UI → Router: `input_changed`, `primary_changed`, `fallback_changed`, `boost_state_changed` (main.py:10-13)
- Router → UI: `devices_changed` (router.py:6)

The router is moved to a separate thread using `moveToThread()` (main.py:20) and started/stopped via the thread's `started` and `finished` signals.

### Audio Processing Flow

1. **Device Detection**: `AutoAudioRouter.detect_device()` (router.py:52) identifies input/output devices by matching filter strings against available devices
2. **Source/Sink Management**: When devices change, `build_source()` and `build_sink()` create new QAudioSource/QAudioSink instances
3. **Audio Routing**: `process_input()` (router.py:112) reads from the input stream and writes to the output stream
4. **Volume Boost**: When enabled, uses numpy to analyze peak levels over a 1000-sample history and applies dynamic gain (router.py:115-121)

### Device Filtering

The application uses partial string matching to identify devices:
- Default input filter: "Virtual Audio Cable" (router.py:14)
- Default primary output: "Headphones" (router.py:16)
- Default fallback output: "Speakers" (router.py:15)

Primary device can be disconnected/unavailable - the app will fallback automatically.

## Running the Application

```bash
# Run the GUI application
python main.py

# Run the router standalone (no GUI, for testing)
python router.py
```

The application uses a QTimer with 500ms interval to keep the Qt event loop responsive to SIGINT signals (main.py:33-34).

## Building

The project uses PyInstaller for building standalone executables:

```bash
# Build using spec file
pyinstaller main.spec
```

**Known Issue**: PyInstaller build is currently broken (noted in git commit and notes file). Consider using pyside6-deploy instead (see notes file for reference).

## Dependencies

Managed via `pyproject.toml` with uv:
- PySide6 (Qt for Python) - GUI framework
- numpy - Audio processing and gain calculation
- PyInstaller - Executable building (currently has issues)

Python version: >=3.12

## System Tray Behavior

- Window minimizes to system tray (if available)
- Click tray icon to restore window (main.py:132-138)
- Right-click tray menu has quit option
- The app prevents quit-on-last-window-closed behavior when tray is available (main.py:30)

## Audio Format

Hardcoded to 48kHz, 2-channel, 16-bit signed integer (router.py:101-103).

## Signal Handling

Both main.py and router.py include SIGINT handlers to enable graceful shutdown with Ctrl+C. A custom exception hook prints full tracebacks instead of Qt's abbreviated output.
