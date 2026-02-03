import os
import hashlib
import shutil
from collections import defaultdict
from pathlib import Path
from rich.progress import Progress

class CleanModule:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.duplicates = defaultdict(list)
        self.file_count = 0
        self.duplicate_count = 0
        self.wasted_size = 0

    def _get_creation_time(self, path):
        """Returns file creation time (st_birthtime on Mac, ctime on others)."""
        try:
            stat = os.stat(path)
            if hasattr(stat, 'st_birthtime'):
                return stat.st_birthtime
            return stat.st_ctime
        except OSError:
            return 0

    def scan(self, root_path):
        """Recursively scans files and finds duplicates based on hash, keeping the oldest file."""
        self.duplicates.clear()
        self.file_count = 0
        hashes = {}
        
        # Count files first for progress bar
        total_files = sum([len(files) for r, d, files in os.walk(root_path)])
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Scanning files...", total=total_files)
            
            for root, _, files in os.walk(root_path):
                for file in files:
                    if file.startswith('.'):
                        continue
                        
                    file_path = os.path.join(root, file)
                    try:
                        file_hash = self._get_file_hash(file_path)
                        size = os.path.getsize(file_path)
                        
                        if file_hash in hashes:
                            # Collision found! Compare dates to decide who stays.
                            keeper_path = hashes[file_hash]
                            
                            keeper_time = self._get_creation_time(keeper_path)
                            current_time = self._get_creation_time(file_path)
                            
                            if current_time < keeper_time:
                                # Current file is OLDER (smaller timestamp). It becomes the new Keeper.
                                # The old keeper becomes the duplicate (trash).
                                self.duplicates[file_hash].append(keeper_path)
                                hashes[file_hash] = file_path # Update keeper (map hash to NEW keeper)
                                self.wasted_size += os.path.getsize(keeper_path)
                            else:
                                # Current file is NEWER (or same). It is the duplicate.
                                self.duplicates[file_hash].append(file_path)
                                self.wasted_size += size

                            self.duplicate_count += 1
                        else:
                            hashes[file_hash] = file_path
                        
                        self.file_count += 1
                        progress.advance(task)
                    except (OSError, PermissionError):
                        continue
    
    
    def quick_scan(self, root_path):
        """Scans for names based on normalized filenames, keeping the oldest file."""
        import re
        self.duplicates.clear()
        self.file_count = 0
        self.duplicate_count = 0
        self.wasted_size = 0
        
        # Regex to strip "01 - " style prefixes
        pattern = re.compile(r"^\d+\s*-\s*")
        seen_names = {} # normalized_name -> original_path (The KEEPER)
        
        files_to_check = []
        for root, _, files in os.walk(root_path):
            files_to_check.extend([(root, f) for f in files if not f.startswith('.')])
            
        with Progress() as progress:
            task = progress.add_task("[cyan]Quick scanning filenames...", total=len(files_to_check))
            
            for root, file in files_to_check:
                file_path = os.path.join(root, file)
                
                # Normalize name
                match = pattern.match(file)
                if match:
                    norm_name = file[len(match.group(0)):]
                else:
                    norm_name = file
                
                norm_name = norm_name.lower()
                
                if norm_name in seen_names:
                    # Collision
                    keeper_path = seen_names[norm_name]
                    
                    keeper_time = self._get_creation_time(keeper_path)
                    current_time = self._get_creation_time(file_path)
                    
                    if current_time < keeper_time:
                        # Current is Older -> Kick out old keeper
                        self.duplicates[norm_name].append(keeper_path)
                        seen_names[norm_name] = file_path
                        size = os.path.getsize(keeper_path)
                    else:
                        # Current is Newer -> Trash it
                        self.duplicates[norm_name].append(file_path)
                        size = os.path.getsize(file_path)

                    self.duplicate_count += 1
                    self.wasted_size += size
                else:
                    seen_names[norm_name] = file_path
                
                self.file_count += 1
                progress.advance(task)

    def _get_file_hash(self, file_path, block_size=65536):
        """Calculates SHA-256 hash of a file."""
        sha256 = hashlib.sha256()
        with open(file_path, 'rb') as f:
            for block in iter(lambda: f.read(block_size), b''):
                sha256.update(block)
        return sha256.hexdigest()

    def report(self):
        """Returns a summary of the scan."""
        return {
            "total_files": self.file_count,
            "duplicates": self.duplicate_count,
            "wasted_size_mb": self.wasted_size / (1024 * 1024)
        }

    def deduplicate(self, mode, root_path):
        """
        Executes deduplication based on mode.
        mode: 'delete' or 'move'
        """
        trash_dir = os.path.join(root_path, "_DUPLICATES_TRASH")
        if mode == 'move' and not os.path.exists(trash_dir):
            os.makedirs(trash_dir, exist_ok=True)
            
        results = []
        
        for file_hash, paths in self.duplicates.items():
            for file_path in paths:
                # 'paths' contains ONLY the duplicates (2nd, 3rd occurrence etc.)
                # Verify this logic: 
                # In scan: if file_hash in hashes -> self.duplicates[file_hash].append(file_path)
                # Yes, so the first file found is NOT in self.duplicates[file_hash].
                
                action = "Deleted" if mode == 'delete' else "Moved"
                
                if self.dry_run:
                    results.append(f"[DRY-RUN] Would {action}: {file_path}")
                    continue
                    
                try:
                    if mode == 'delete':
                        os.remove(file_path)
                        results.append(f"Deleted: {file_path}")
                    elif mode == 'move':
                        dest = os.path.join(trash_dir, os.path.basename(file_path))
                        # Handle name collision in trash
                        if os.path.exists(dest):
                            base, ext = os.path.splitext(dest)
                            dest = f"{base}_{file_hash[:8]}{ext}"
                        shutil.move(file_path, dest)
                        results.append(f"Moved: {file_path} -> {dest}")
                except Exception as e:
                    results.append(f"[ERROR] Failed to {action} {file_path}: {e}")
                    
        return results

    def scan_import(self, source_path, library_path, comparison='hash'):
        """
        Scans source_path for files that exist in library_path.
        comparison: 'hash' (content) or 'filename' (normalized name)
        Returns list of duplicate file paths in source_path.
        """
        import re
        # 1. Index Library
        library_fingerprints = set()
        
        # Regex for filename normalization
        pattern = re.compile(r"^\d+\s*-\s*")
        
        def normalize(name):
            match = pattern.match(name)
            if match:
                return name[len(match.group(0)):].lower()
            return name.lower()

        with Progress() as progress:
            task = progress.add_task("[cyan]Indexing library...", total=None)
            total_files = sum([len(files) for r, d, files in os.walk(library_path)])
            progress.update(task, total=total_files)
            
            for root, _, files in os.walk(library_path):
                for file in files:
                    if file.startswith('.'):
                        continue
                        
                    file_path = os.path.join(root, file)
                    try:
                        if comparison == 'hash':
                            fingerprint = self._get_file_hash(file_path)
                        else: # filename
                            fingerprint = normalize(file)
                            
                        library_fingerprints.add(fingerprint)
                        progress.advance(task)
                    except:
                        continue
                        
        # 2. Scan Source
        duplicates_found = []
        with Progress() as progress:
            task = progress.add_task(f"[magenta]Scanning import folder ({comparison})...", total=None)
            total_source = sum([len(files) for r, d, files in os.walk(source_path)])
            progress.update(task, total=total_source)
            
            for root, _, files in os.walk(source_path):
                for file in files:
                    if file.startswith('.'):
                        continue
                        
                    file_path = os.path.join(root, file)
                    try:
                        if comparison == 'hash':
                            fingerprint = self._get_file_hash(file_path)
                        else:
                            fingerprint = normalize(file)
                            
                        if fingerprint in library_fingerprints:
                            duplicates_found.append(file_path)
                        progress.advance(task)
                    except:
                        continue
                        
        return duplicates_found

    def resolve_import_duplicates(self, duplicates, source_path, mode='delete'):
        """
        Deletes or moves the list of duplicate files.
        """
        results = []
        trash_dir = os.path.join(source_path, "_ALREADY_IN_LIB")
        
        if mode == 'move' and not os.path.exists(trash_dir):
            os.makedirs(trash_dir, exist_ok=True)
            
        for file_path in duplicates:
            action = "Deleted" if mode == 'delete' else "Moved"
            if self.dry_run:
                results.append(f"[DRY-RUN] Would {action}: {file_path}")
                continue
                
            try:
                if mode == 'delete':
                    os.remove(file_path)
                    results.append(f"Deleted: {file_path}")
                elif mode == 'move':
                    dest = os.path.join(trash_dir, os.path.basename(file_path))
                    # Handle name collision
                    if os.path.exists(dest):
                         base, ext = os.path.splitext(dest)
                         dest = f"{base}_{self._get_file_hash(file_path)[:8]}{ext}"
                    shutil.move(file_path, dest)
                    results.append(f"Moved: {file_path} -> {dest}")
            except Exception as e:
                results.append(f"[ERROR] {file_path}: {e}")
                
        return results
