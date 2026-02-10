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

# Workflow

1. Find Playlist in Spotify and save it to library.
2. Download playlist csv using Exportify.
3. Deduplicate csv using DJ Manager.
4. Upload playlist to download website.
5. Download playlist.
6. Extract playlist.
7. Remove prefixes using DJ Manager.
8. (Optional) Pre move duplicates to quarantine using DJ Manager.
9. Add Tags using OneTagger.
10. Copy files to library (USB).
11. (Optional) Deduplicate library using DJ Manager.
12. Convert pre-dedupilicate playlist csv to m3u8 using DJ Manager.
13. Import m3u8 to Rekordbox.
14. Scan library for corrupt files using DJ Manager.
