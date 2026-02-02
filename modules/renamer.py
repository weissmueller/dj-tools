import os
import re
from rich.progress import Progress

class RenamerModule:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.rename_map = {} # old_path -> new_path

    def scan(self, root_path):
        """Scans for files with 'Number - ' prefix."""
        self.rename_map = {}
        # Regex: Start of string, one or more digits, optional whitespace, hyphen, optional whitespace
        pattern = re.compile(r"^\d+\s*-\s*")
        
        files_to_check = []
        for root, _, files in os.walk(root_path):
            for file in files:
                files_to_check.append((root, file))
        
        with Progress() as progress:
            task = progress.add_task("[cyan]Scanning for prefixes...", total=len(files_to_check))
            
            for root, file in files_to_check:
                match = pattern.match(file)
                if match:
                    # Construct new filename
                    prefix = match.group(0)
                    new_name = file[len(prefix):] # Strip prefix
                    
                    # Avoid empty names or collisions (basic check)
                    if not new_name:
                        continue
                        
                    old_path = os.path.join(root, file)
                    new_path = os.path.join(root, new_name)
                    
                    # Store mapping
                    self.rename_map[old_path] = new_path
                
                progress.advance(task)
        
        return self.rename_map

    def execute(self):
        """Executes renaming."""
        results = []
        for old_path, new_path in self.rename_map.items():
            if self.dry_run:
                results.append(f"[DRY-RUN] Rename: '{os.path.basename(old_path)}' -> '{os.path.basename(new_path)}'")
                continue
            
            try:
                if os.path.exists(new_path):
                     results.append(f"[SKIP] Target exists: {os.path.basename(new_path)}")
                     continue
                     
                os.rename(old_path, new_path)
                results.append(f"Renamed: {os.path.basename(old_path)} -> {os.path.basename(new_path)}")
            except Exception as e:
                results.append(f"[ERROR] Failed to rename {os.path.basename(old_path)}: {e}")
                
        return results
