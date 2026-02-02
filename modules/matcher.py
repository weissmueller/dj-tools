import os
import pandas as pd
from thefuzz import process, fuzz
from rich.progress import Progress

class MatchMaker:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.local_files = []
        self.local_index = {} # simplified string -> path

    def _index_files(self, root_path):
        """Indexes all audio files in the directory for faster matching."""
        self.local_files = []
        self.local_index = {}
        
        allowed_exts = ('.mp3', '.flac', '.wav', '.aiff', '.m4a')
        
        with Progress() as progress:
            task = progress.add_task("[green]Indexing local library...", total=None)
            
            for root, _, files in os.walk(root_path):
                for file in files:
                    if file.startswith('.'):
                        continue
                    if file.lower().endswith(allowed_exts):
                        full_path = os.path.join(root, file)
                        self.local_files.append(full_path)
                        
                        # Create a simplified search string: "Artist - Title" based on filename
                        # This is a heuristic. Ideally we'd read ID3 tags, but filename is faster 
                        # and often sufficient for DJs who organize files cleanly.
                        # Let's use the basename without extension as the searchable string.
                        clean_name = os.path.splitext(file)[0].lower().replace('_', ' ').replace('-', ' ')
                        self.local_index[clean_name] = full_path
                        
            progress.update(task, completed=100, total=100)
            
    def match(self, csv_path, library_path, threshold=85):
        """Matches CSV entries to local files."""
        # 1. Load CSV
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            return {"error": f"Could not read CSV: {e}"}
            
        # Check required columns (adapt to Exportify standard)
        # Exportify usually has: "Track Name", "Artist Name(s)", "Album Name"
        required_cols = ['Track Name', 'Artist Name(s)']
        if not all(col in df.columns for col in required_cols):
             return {"error": f"CSV missing columns. Required: {required_cols}"}

        # 2. Index Library
        if not self.local_files:
            self._index_files(library_path)
            
        matches = []
        missing = []
        
        local_search_keys = list(self.local_index.keys())
        
        with Progress() as progress:
            task = progress.add_task("[magenta]Matching tracks...", total=len(df))
            
            for index, row in df.iterrows():
                track = str(row['Track Name'])
                artist = str(row['Artist Name(s)'])
                query = f"{artist} {track}".lower().replace('-', ' ')
                
                # Fuzzy match
                # extractOne returns (best_match_string, score)
                best_match = process.extractOne(query, local_search_keys, scorer=fuzz.token_set_ratio)
                
                if best_match and best_match[1] >= threshold:
                    matched_path = self.local_index[best_match[0]]
                    matches.append(matched_path)
                else:
                    missing.append(f"{artist} - {track}")
                    
                progress.advance(task)
                
        return {
            "found_tracks": matches,
            "missing_tracks": missing
        }

    def deduplicate_csv(self, csv_path, library_path, threshold=85):
        """Creates a new CSV containing only tracks NOT found in the library."""
        # 1. Load CSV
        try:
            df = pd.read_csv(csv_path)
        except Exception as e:
            return {"error": f"Could not read CSV: {e}"}
            
        required_cols = ['Track Name', 'Artist Name(s)']
        if not all(col in df.columns for col in required_cols):
             return {"error": f"CSV missing columns. Required: {required_cols}"}

        # 2. Index Library
        if not self.local_files:
            self._index_files(library_path)
            
        local_search_keys = list(self.local_index.keys())
        rows_to_keep = []
        
        with Progress() as progress:
            task = progress.add_task("[magenta]Deduplicating CSV...", total=len(df))
            
            for index, row in df.iterrows():
                track = str(row['Track Name'])
                artist = str(row['Artist Name(s)'])
                query = f"{artist} {track}".lower().replace('-', ' ')
                
                # Check if it exists in library
                best_match = process.extractOne(query, local_search_keys, scorer=fuzz.token_set_ratio)
                
                if not (best_match and best_match[1] >= threshold):
                    # Not found -> Keep it in the new CSV
                    rows_to_keep.append(row)
                    
                progress.advance(task)
                
        # 3. Write Deduped CSV
        if not rows_to_keep:
            return {"message": "All tracks found in library! No new CSV needed.", "path": None}
            
        new_df = pd.DataFrame(rows_to_keep)
        
        base_name = os.path.splitext(os.path.basename(csv_path))[0]
        output_dir = os.path.dirname(os.path.abspath(csv_path))
        output_path = os.path.join(output_dir, f"{base_name}_deduped.csv")
        
        try:
            new_df.to_csv(output_path, index=False)
            return {"message": f"Deduped CSV created with {len(new_df)} tracks.", "path": output_path}
        except Exception as e:
            return {"error": f"Could not write CSV: {e}"}

    def export_m3u(self, matches, output_path):
        """Writes matches to an M3U8 file."""
        if self.dry_run:
            return f"[DRY-RUN] Would generate M3U at {output_path} with {len(matches)} tracks."
            
        try:
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write("#EXTM3U\n")
                for path in matches:
                    f.write(f"{path}\n")
            return f"Successfully created playlist: {output_path}"
        except Exception as e:
            return f"Error writing M3U: {e}"
