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

# Workflows

## Spotify Workflow (Playlist Acquisition)
1. **Source**: Find a Playlist in Spotify and save it to your library.
2. **Export**: use [Exportify](https://exportify.net/) to download the playlist as a `.csv` file.
3. **Filter**: Run `dj_manager.py` -> **5) CSV Deduplicator**.
   - Input: Your Exportify CSV.
   - Action: This removes tracks you *already own* in your main library from the CSV.
   - Result: A "Clean" CSV list of tracks you need to buy/download.
4. **Acquire**: Upload the "Clean" CSV to your download source (e.g., slider.kz, soulseek, etc.) and download the tracks to a temporary folder (e.g. `~/Downloads/New_Playlist`).
5. **Process**: Run `dj_manager.py` -> **9) OneTagger Auto-Tagging**.
   - Input: The folder with your new downloads.
   - Action: **Clean Filenames** (remove "01 - " prefixes) and **Auto-Tag** metadata.
6. **Verify**: Run `dj_manager.py` -> **6) Import Deduplicator** (Optional).
   - Action: Double-check if the downloaded files are duplicates of existing library tracks (audio fingerprint/hash check).
7. **Import**: Move the clean, tagged files to your main library (USB/Drive).
8. **Playlist**: Run `dj_manager.py` -> **3) Playlist Sync (CSV to M3U)**.
   - Input: The "Clean" CSV and your main library path.
   - Action: generate an `.m3u8` playlist file for Rekordbox/Serato.

## Beatport/Chart Workflow
1. **Source**: Copy the URL of a Beatport Top 100 or Playlist.
2. **Scrape**: Run `dj_manager.py` -> **7) Import Beatport Top 100**.
   - Action: Scrapes the metadata and saves a CSV file.
3. **Filter**: Run `dj_manager.py` -> **5) CSV Deduplicator**.
   - Input: The scraped CSV.
   - Action: Removes tracks you already have.
4. **Acquire**: Download the missing tracks using the CSV list.
5. **Process**: Run `dj_manager.py` -> **9) OneTagger Auto-Tagging** on the download folder.
6. **Verify & Import**: Same as Spotify workflow (Steps 6-8).
