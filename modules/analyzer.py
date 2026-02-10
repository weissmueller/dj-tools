import os
import csv
from rich.console import Console
from rich.progress import track

class QualityAnalyzer:
    def __init__(self, dry_run=False):
        self.dry_run = dry_run
        self.console = Console()
        self.mutagen = None  # Lazy load

    def _load_mutagen(self):
        if self.mutagen is None:
            try:
                import mutagen
                self.mutagen = mutagen
            except ImportError:
                self.console.print("[red]Error: mutagen not installed.[/red]")
                return False
        return True

    def scan(self, root_path):
        if not self._load_mutagen():
            return {}

        results = []
        audio_exts = ('.mp3', '.flac', '.m4a', '.wav', '.aiff')
        
        # Count total files for progress bar
        file_paths = []
        for root, _, files in os.walk(root_path):
            for file in files:
                if file.lower().endswith(audio_exts):
                    file_paths.append(os.path.join(root, file))

        for file_path in track(file_paths, description="Analyzing audio quality..."):
            info = self.analyze_file(file_path)
            if info:
                results.append(info)
        
        return results

    def analyze_file(self, file_path):
        try:
            f = self.mutagen.File(file_path)
            if not f:
                return None

            bitrate = 0
            sample_rate = 0
            file_type = os.path.splitext(file_path)[1].lower().replace('.', '').upper()

            if hasattr(f, 'info'):
                if hasattr(f.info, 'bitrate') and f.info.bitrate:
                    bitrate = int(f.info.bitrate / 1000) # kbps
                
                # Fallback: Calculate from size/duration if 0 (common for VBR or some containers)
                if bitrate == 0 and hasattr(f.info, 'length') and f.info.length > 0:
                     size_bits = os.path.getsize(file_path) * 8
                     bitrate = int(size_bits / f.info.length / 1000)

                if hasattr(f.info, 'sample_rate'):
                    sample_rate = f.info.sample_rate

            # Detect FLAC-in-M4A or ALAC
            if file_type == 'M4A' and hasattr(f, 'info'):
                 codec = getattr(f.info, 'codec', '').lower()
                 desc = getattr(f.info, 'codec_description', '').lower()
                 
                 if 'flac' in codec or 'flac' in desc:
                     file_type = 'M4A (FLAC)'
                     bitrate = 0 # Treat as lossless/variable
                 elif 'alac' in codec or 'alac' in desc:
                     file_type = 'M4A (ALAC)'
                     bitrate = 0
            
            # If still M4A and bitrate is 0/Unknown but file is large (>20MB) -> Likely ALAC/Lossless without metadata
            if file_type == 'M4A' and bitrate == 0:
                 size_mb = os.path.getsize(file_path) / (1024 * 1024)
                 if size_mb > 15: # Arbitrary threshold for a typical song
                     file_type = 'M4A (Lossless?)'

            return {
                'filename': os.path.basename(file_path),
                'path': file_path,
                'type': file_type,
                'bitrate': bitrate,
                'sample_rate': sample_rate
            }
        except Exception:
            return None

    def generate_report(self, data):
        if not data:
            self.console.print("[yellow]No audio files analyzed.[/yellow]")
            return

        # Aggregate stats
        stats = {}
        for track in data:
            key = (track['type'], track['bitrate'])
            stats[key] = stats.get(key, 0) + 1

        self.console.print("\n[bold blue]== Audio Quality Report ==[/bold blue]")
        from rich.table import Table
        table = Table(title="Bitrate Distribution")
        table.add_column("Format", style="cyan")
        table.add_column("Bitrate (kbps)", style="magenta")
        table.add_column("Count", style="green")

        # Sort by format then bitrate
        sorted_keys = sorted(stats.keys(), key=lambda x: (x[0], x[1]))

        for fmt, br in sorted_keys:
            # Display logic
            display_fmt = fmt
            br_is_lossless = br == 0 or "Lossless" in fmt or "FLAC" in fmt or "ALAC" in fmt
            
            if fmt == 'M4A' and not br_is_lossless:
                # Heuristic for AAC
                if br > 500:
                    display_fmt = "M4A (ALAC?)"
                else:
                    display_fmt = "M4A (AAC)"
            
            br_display = f"{br} kbps" if br > 0 else "Lossless/Var"
            table.add_row(display_fmt, br_display, str(stats[(fmt, br)]))

        self.console.print(table)
        self.console.print("[dim]Note: 'Lossless/Var' includes FLAC, ALAC, WAV, and AIFF files.[/dim]")
        return stats

    def export_csv(self, data, output_path):
        if not data:
            return
        
        keys = ['filename', 'type', 'bitrate', 'sample_rate', 'path']
        try:
            with open(output_path, 'w', newline='', encoding='utf-8') as f:
                writer = csv.DictWriter(f, fieldnames=keys)
                writer.writeheader()
                writer.writerows(data)
            self.console.print(f"[green]Report saved to: {output_path}[/green]")
        except Exception as e:
            self.console.print(f"[red]Error saving CSV: {e}[/red]")
