# DJ Library Manager (CLI)

An interactive CLI tool for managing your DJ music library.

## Features
- **Clean:** Find and deduplicate redundant audio files.
- **Doctor:** Check FLAC files for corruption.
- **Match:** Sync Spotify playlists (via Exportify CSV) to local files.

## Installation

1.  **Prerequisites:**
    - Python 3.9+
    - `ffmpeg` or `flac` installed on your system (for audio integrity checks).
      - macOS: `brew install flac`

2.  **Setup:**
    ```bash
    python3 -m venv .venv
    source .venv/bin/activate
    pip install -r requirements.txt
    ```

## Usage

```bash
python dj_manager.py
```

Or with arguments:
```bash
python dj_manager.py --root "/Volumes/MusicUSB" --dry-run
```
