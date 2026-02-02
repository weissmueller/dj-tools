import os
import shutil
import soundfile as sf
import subprocess
from rich.progress import Progress

class HealthGuard:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.corrupt_files = []

    def scan_flac(self, root_path):
        """Scans FLAC files for corruption using soundfile and flac -t."""
        self.corrupt_files = []
        flac_files = []
        
        # Collect FLAC files
        for root, _, files in os.walk(root_path):
            for file in files:
                if file.startswith('.'):
                    continue
                if file.lower().endswith('.flac'):
                    flac_files.append(os.path.join(root, file))
        
        if not flac_files:
            return []

        with Progress() as progress:
            task = progress.add_task("[red]Checking FLAC integrity...", total=len(flac_files))
            
            for file_path in flac_files:
                is_corrupt = False
                # Method 1: Try opening with soundfile
                try:
                    with sf.SoundFile(file_path) as f:
                        pass
                except Exception:
                    is_corrupt = True
                
                # Method 2: 'flac -t' (Test) if method 1 passed but we want to be sure, 
                # or if method 1 failed we already know. 
                # Ideally 'flac -t' is better. Let's try subprocess if installed.
                if not is_corrupt:
                    try:
                        # -t: test, -s: silent
                        subprocess.check_call(['flac', '-t', '-s', file_path], stderr=subprocess.DEVNULL)
                    except (subprocess.CalledProcessError, FileNotFoundError):
                        # If flac is not found, we rely on soundfile. 
                        # If CalledProcessError, it failed the test.
                        # Check if it was FileNotFoundError (tool missing) or CalledProcessError (corrupt)
                        # We can check if shutil.which('flac') exists once ideally.
                        if shutil.which('flac'):
                             # It really failed the test
                             is_corrupt = True
                        
                if is_corrupt:
                    self.corrupt_files.append(file_path)
                
                progress.advance(task)
                
        return self.corrupt_files

    def quarantine(self, root_path):
        """Moves corrupt files to a quarantine folder."""
        quarantine_dir = os.path.join(root_path, "_CORRUPT_FILES")
        if not os.path.exists(quarantine_dir):
            os.makedirs(quarantine_dir, exist_ok=True)
            
        results = []
        for file_path in self.corrupt_files:
            if self.dry_run:
                results.append(f"[DRY-RUN] Would move to quarantine: {file_path}")
                continue
                
            try:
                dest = os.path.join(quarantine_dir, os.path.basename(file_path))
                if os.path.exists(dest):
                    base, ext = os.path.splitext(dest)
                    import uuid
                    dest = f"{base}_{uuid.uuid4().hex[:6]}{ext}"
                    
                shutil.move(file_path, dest)
                results.append(f"Quarantined: {file_path}")
            except Exception as e:
                results.append(f"[ERROR] Failed to quarantine {file_path}: {e}")
                
        return results
