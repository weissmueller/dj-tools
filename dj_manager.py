import argparse
import os
import sys
from rich.console import Console
from rich.panel import Panel
from rich.prompt import Prompt, Confirm
from rich import print
import questionary

# Import modules
from modules.cleaner import CleanModule
from modules.doctor import HealthGuard
from modules.matcher import MatchMaker
from modules.renamer import RenamerModule
from modules.scraper import BeatportScraper
from modules.analyzer import QualityAnalyzer

console = Console()

def print_header(root_path):
    header = f"""
  _   _   _   _   _   _   _  
 / \\ / \\ / \\ / \\ / \\ / \\ / \\ 
( D | J | M | A | S | T | E | R )
 \\_/ \\_/ \\_/ \\_/ \\_/ \\_/ \\_/ 
 
>> Root Path detected: [yellow]{root_path}[/yellow]
    """
    console.print(Panel(header, style="bold cyan"))

def get_root_path(args):
    if args.root:
        _save_last_root(args.root)
        return args.root
        
    # Check for last used path
    last_root_file = ".last_root"
    if os.path.exists(last_root_file):
        try:
            with open(last_root_file, "r") as f:
                last_path = f.read().strip()
            if os.path.exists(last_path):
                 if Confirm.ask(f"Use last session's root? [cyan]({last_path})[/cyan]", default=True):
                     return last_path
        except:
            pass

    # Default to current directory or ask
    path = os.getcwd()
    if Confirm.ask(f"Use current directory as root? ({path})", default=False):
        # Note: defaulted to False now since user likely has a specific external drive
        _save_last_root(path)
        return path
        
    path = Prompt.ask("Enter root path").strip().strip("'").strip('"')
    if os.path.exists(path):
        _save_last_root(path)
    return path

def _save_last_root(path):
    try:
        with open(".last_root", "w") as f:
            f.write(path)
    except:
        pass

def run_cleaner(root_path, dry_run=False):
    console.print("[bold blue]== Module A: Interactive Cleaner ==[/bold blue]")
    
    mode = questionary.select(
        "Scan Mode:",
        choices=[
            "1. Deep Scan (Hash Content) - Slow, exact",
            "2. Quick Scan (Filename only) - Fast, ignores '01 - ' prefixes"
        ]
    ).ask()
    
    if mode is None:
        return
    
    cleaner = CleanModule(dry_run=dry_run)
    
    if mode.startswith("1."):
        cleaner.scan(root_path)
    else:
        cleaner.quick_scan(root_path)
        
    report = cleaner.report()
    
    console.print(f"\n[green]Files scanned:[/green] {report['total_files']}")
    console.print(f"[red]Duplicates found:[/red] {report['duplicates']}")
    console.print(f"[yellow]Potential space savings:[/yellow] {report['wasted_size_mb']:.2f} MB")
    
    if report['duplicates'] == 0:
        console.print("No duplicates found. Heading back.")
        return

    action = questionary.select(
        "How do you want to handle duplicates?",
        choices=[
            "a) Delete (Keep oldest file, delete newer duplicates)",
            "b) Move to /_DUPLICATES_TRASH",
            "c) Just show report",
            "d) Cancel"
        ]
    ).ask()
    
    if action.startswith("a)"):
        confirm = Confirm.ask("Are you SURE you want to DELETE files?", default=False)
        if confirm:
            results = cleaner.deduplicate('delete', root_path)
            for res in results:
                console.print(res)
    elif action.startswith("b)"):
        results = cleaner.deduplicate('move', root_path)
        for res in results:
            console.print(res)
    elif action.startswith("c)"):
        # Just show the list?
        # For brevity, let's just say "Done"
        # Ideally we list them.
        pass

def run_doctor(root_path, dry_run=False):
    console.print("[bold blue]== Module B: Health Guard ==[/bold blue]")
    doctor = HealthGuard(dry_run=dry_run)
    corrupt_files = doctor.scan_flac(root_path)
    
    if not corrupt_files:
        console.print("[green]No corrupt FLAC files found![/green]")
        return
        
    console.print(f"[red]Found {len(corrupt_files)} corrupt files.[/red]")
    for f in corrupt_files:
        console.print(f" - {f}")

    # Always save report
    with open("corrupt_files_report.csv", "w") as f:
        f.write("Filename\n")
        f.write("\n".join(corrupt_files))
    console.print("[dim]Report saved to corrupt_files_report.csv[/dim]")

    action = questionary.select(
        "Action:",
        choices=[
            "a) Move to quarantine (/_CORRUPT_FILES)",
            "b) Do nothing"
        ]
    ).ask()
    
    if action.startswith("a)"):
        results = doctor.quarantine(root_path)
        for res in results:
            console.print(res)

def run_matcher(root_path, dry_run=False):
    console.print("[bold blue]== Module C: Matchmaker ==[/bold blue]")
    
    console.print("[bold blue]== Module C: Matchmaker ==[/bold blue]")
    
    csv_path = _select_csv()
    if not csv_path:
        return
    
    if not os.path.exists(csv_path):
        console.print("[red]File not found![/red]")
        return
        
    matcher = MatchMaker(dry_run=dry_run)
    res = matcher.match(csv_path, root_path)
    
    if "error" in res:
        console.print(f"[red]Error:[/red] {res['error']}")
        return
        
    params = res
    found = len(params['found_tracks'])
    missing = len(params['missing_tracks'])
    
    console.print(f"[green]Found:[/green] {found}")
    console.print(f"[red]Missing:[/red] {missing}")
    
    if missing > 0:
        base_name = os.path.splitext(os.path.basename(csv_path))[0]
        output_dir = os.path.dirname(os.path.abspath(csv_path))
        missing_path = os.path.join(output_dir, f"{base_name}_missing.txt")
        
        with open(missing_path, "w") as f:
             f.write("\n".join(params['missing_tracks']))
        console.print(f"Missing tracks saved to: {missing_path}")
        
    if found > 0:
        if Confirm.ask("Save M3U8 playlist?"):
            # Default name based on CSV filename
            base = os.path.splitext(os.path.basename(csv_path))[0]
            
            # Determine prefix
            prefix = "[Spotify]"
            if "beatport" in base.lower() or "chart" in base.lower():
                prefix = "[Beatport]"
                # Remove 'beatport' from base name to avoid particular "[Beatport] Beatport ..."
                import re
                base = re.sub(r'beatport', '', base, flags=re.IGNORECASE).strip()
                base = re.sub(r'\s+', ' ', base).strip() # clean double spaces
            
            # specific format: [Prefix] Title Cased With Spaces
            formatted_name = base.replace("_", " ").title()
            default_name = f"{prefix} {formatted_name}.m3u8"
            
            name = Prompt.ask("Playlist Name", default=default_name)
            
            # Auto-append extension
            if not name.lower().endswith(('.m3u8', '.m3u')):
                name += ".m3u8"
            
            # Save next to CSV
            output_dir = os.path.dirname(os.path.abspath(csv_path))
            output_path = os.path.join(output_dir, name)
            
            msg = matcher.export_m3u(params['found_tracks'], output_path)
            console.print(msg)

def run_renamer(root_path, dry_run=False):
    console.print("[bold blue]== Module D: Prefix Remover ==[/bold blue]")
    renamer = RenamerModule(dry_run=dry_run)
    mapping = renamer.scan(root_path)
    
    if not mapping:
        console.print("[green]No files with prefix 'Number - ' found.[/green]")
        return
        
    console.print(f"[yellow]Found {len(mapping)} files to rename.[/yellow]")
    # Show a few examples
    examples = list(mapping.items())[:5]
    for old, new in examples:
        console.print(f" [dim]{os.path.basename(old)}[/dim] -> [bold cyan]{os.path.basename(new)}[/bold cyan]")
    if len(mapping) > 5:
        console.print(f" ... and {len(mapping)-5} more.")
        
    if Confirm.ask("Proceed with renaming?"):
        results = renamer.execute()
        for res in results:
            console.print(res)

def _select_csv():
    # Auto-discover CSVs in Downloads
    downloads_path = os.path.expanduser("~/Downloads")
    csv_choices = []
    
    if os.path.exists(downloads_path):
        import glob
        files = glob.glob(os.path.join(downloads_path, "*.csv"))
        files.sort(key=os.path.getmtime, reverse=True)
        for f in files[:10]:
            csv_choices.append(f)
            
    choices = csv_choices + ["Enter path manually..."]
    
    selection = questionary.select("Select Exportify CSV:", choices=choices).ask()
    
    if selection == "Enter path manually...":
        return Prompt.ask("Path to Exportify CSV").strip().strip("'").strip('"')
    return selection

def run_deduplicator(root_path, dry_run=False):
    console.print("[bold blue]== Module E: CSV Deduplicator ==[/bold blue]")
    
    csv_path = _select_csv()
    if not csv_path: 
        return

    matcher = MatchMaker(dry_run=dry_run)
    # The message includes the path, so we don't need to print it again unless we want to be explicit
    result = matcher.deduplicate_csv(csv_path, root_path)
    
    if "error" in result:
        console.print(f"[bold red]Error:[/bold red] {result['error']}")
    else:
        console.print(f"[green]{result['message']}[/green]")
        if result['path']:
             console.print(f"Saved to: [bold]{result['path']}[/bold]")

def run_import_deduplicator(root_path, dry_run=False):
    console.print("[bold blue]== Module F: Import Deduplicator (Folder Stager) ==[/bold blue]")
    console.print(f"Main Library: [yellow]{root_path}[/yellow]")
    
    source_path = Prompt.ask("Enter Importer Source Folder (e.g. USB Stick)").strip().strip("'").strip('"')
    if not os.path.exists(source_path):
         console.print("[red]Source path not found![/red]")
         return

    cleaner = CleanModule(dry_run=dry_run)
    
    # 0. Optional: Run Prefix Remover on Source
    if Confirm.ask("Run Prefix Remover on Source Folder first? (Removes '01 - ')", default=False):
        renamer = RenamerModule(dry_run=dry_run)
        mapping = renamer.scan(source_path)
        if mapping:
            console.print(f"[yellow]Found {len(mapping)} files to rename in Source.[/yellow]")
            if Confirm.ask("Proceed with renaming in Source?"):
                res = renamer.execute()
                for r in res: console.print(r)
        else:
            console.print("[dim]No files to rename found.[/dim]")
    
    # 1. Ask for Comparison Method
    comp_choice = questionary.select(
        "Comparison Method:",
        choices=[
            "1. Deep Hash (Exact Content Match)",
            "2. Filename (Match 'Song.mp3' to '01 - Song.mp3')"
        ]
    ).ask()
    
    comparison = 'hash' if comp_choice.startswith('1') else 'filename'
    
    # 2. Run Scan
    duplicates = cleaner.scan_import(source_path, root_path, comparison=comparison)
    
    count = len(duplicates)
    if count == 0:
        console.print("[green]No duplicates found in source! You are good to import.[/green]")
        return
        
    console.print(f"\n[red]Found {count} duplicates in source folder.[/red]")
    
    # 3. Ask for Action
    action = questionary.select(
        f"How do you want to handle these {count} files?",
        choices=[
            "a) Delete from Source (Keep Lib version)",
            "b) Move to _ALREADY_IN_LIB folder",
            "c) View list of duplicates",
            "d) Cancel"
        ]
    ).ask()
    
    if action.startswith('c)'):
        # View list logic could be added here, currently just printing top 10
        console.print("First 10 duplicates:")
        for d in duplicates[:10]:
             console.print(f" - {d}")
        if len(duplicates) > 10:
             console.print(f"... and {len(duplicates)-10} more.")
             
        # Ask again? For now just exit or recursively call? 
        # Simpler to just re-prompt action, but for MVP let's just loop or exit.
        if not Confirm.ask("Proceed to action?"):
            return
            
        # Re-ask action (simplified for now, assume they want to proceed after viewing)
        action = questionary.select(
            "Action:",
            choices=["a) Delete", "b) Move", "d) Cancel"]
        ).ask()
    
    if action.startswith('d)'):
        return

    scan_mode = 'delete' if action.startswith('a') else 'move'

    if scan_mode == 'delete' and not Confirm.ask(f"Are you sure you want to DELETE {count} files from source?", default=False):
        return

    # 4. Resolve
    results = cleaner.resolve_import_duplicates(duplicates, source_path, mode=scan_mode)
    
    for res in results:
        console.print(res)
    console.print(f"[green]Cleaned {len(results)} files from source.[/green]")

def run_scraper(root_path):
    console.print("[bold blue]== Module G: Beatport Scraper ==[/bold blue]")
    
    url = Prompt.ask("Enter Beatport Top 100 URL").strip()
    if not url:
        return
        
    scraper = BeatportScraper()
    
    # Ask about mix name preference
    include_mix = Confirm.ask("Append Mix Name to Track Title? (e.g. 'Song (Extended Mix)')", default=True)
    
    console.print("[cyan]Scraping data...[/cyan]")
    result = scraper.scrape(url, include_mix_name=include_mix)
    
    if "error" in result:
        console.print(f"[red]Error:[/red] {result['error']}")
        return
        
    df = result['df']
    original_count = len(df)
    
    # 2. Deduplicate if necessary (Keep highest rank)
    df.drop_duplicates(subset=['Track Name', 'Artist Name(s)'], keep='first', inplace=True)
    count = len(df)
    
    removed = original_count - count
    if removed > 0:
        console.print(f"[yellow]Removed {removed} duplicates (likely different mixes of same track).[/yellow]")

    genre = result['genre']
    
    console.print(f"[green]Successfully scraped {count} tracks from {genre} Top 100![/green]")
    
    # Show preview
    console.print("\n[bold]Preview (First 5):[/bold]")
    table = df[['Track Name', 'Artist Name(s)']].head(5).to_string(index=False)
    console.print(table)
    
    # Filename suggestion
    default_filename = f"Beatport Top 100 {genre}.csv"
    # Removing any unsafe characters for filename
    default_filename = "".join([c for c in default_filename if c.isalpha() or c.isdigit() or c in (' ', '-', '_')]).strip() + ".csv"
    
    filename = Prompt.ask("Save as:", default=default_filename)
    if not filename.endswith('.csv'):
        filename += ".csv"
        
    # Save options: Examples folder or current dir
    # Default to examples for organization? Or just current dir. 
    # Let's verify 'examples' exists
    save_path = filename
    examples_dir = os.path.join(os.getcwd(), "examples")
    if os.path.exists(examples_dir):
        if Confirm.ask(f"Save to 'examples/' folder?", default=True):
            save_path = os.path.join(examples_dir, filename)
            
    df.to_csv(save_path, index=False, quoting=1) # quote all
    console.print(f"[green]Saved to: {save_path}[/green]")


def run_analyzer(root_path):
    console.print("[bold blue]== Module H: Audio Quality Analyzer ==[/bold blue]")
    analyzer = QualityAnalyzer()
    
    results = analyzer.scan(root_path)
    if not results:
        return

    # Show stats
    analyzer.generate_report(results)
    
    # Export?
    if Confirm.ask("Export detailed CSV report?", default=False):
        timestamp = os.path.basename(root_path) + "_quality_report.csv"
        default_name = timestamp
        filename = Prompt.ask("Report Filename", default=default_name)
        
        if not filename.endswith('.csv'):
            filename += ".csv"
            
        analyzer.export_csv(results, filename)



def main():
    parser = argparse.ArgumentParser(description="DJ Library Manager")
    parser.add_argument("--root", help="Root directory of music library")
    parser.add_argument("--dry-run", action="store_true", help="Simulate actions without deleting/moving")
    args = parser.parse_args()
    
    root_path = get_root_path(args)
    if not os.path.exists(root_path):
        console.print(f"[red]Path does not exist: {root_path}[/red]")
        return
        
    while True:
        print_header(root_path)
        if args.dry_run:
            console.print("[bold magenta]!!! DRY RUN MODE ACTIVE !!![/bold magenta]")
            
        choice = questionary.select(
            "Main Menu",
            choices=[
                "1) Scan & Deduplicate",
                "2) Health Check (FLAC)",
                "3) Playlist Sync (CSV to M3U)",
                "4) Prefix Remover (01 - Song.mp3 -> Song.mp3)",
                "5) CSV Deduplicator (Remove owned tracks from CSV)",
                "6) Import Deduplicator (Clean external folder against Library)",
                "7) Import Beatport Top 100",
                "8) Analyze Audio Quality (Bitrate/Format Report)",
                "9) Full Auto-Mode (Run 1, 2, 3)",
                "q) Quit"
            ]
        ).ask()
        
        if choice.startswith("1)"):
            run_cleaner(root_path, args.dry_run)
        elif choice.startswith("2)"):
            run_doctor(root_path, args.dry_run)
        elif choice.startswith("3)"):
            run_matcher(root_path, args.dry_run)
        elif choice.startswith("4)"):
            run_renamer(root_path, args.dry_run)
        elif choice.startswith("5)"):
            run_deduplicator(root_path, args.dry_run)
        elif choice.startswith("6)"):
            run_import_deduplicator(root_path, args.dry_run)
        elif choice.startswith("7)"):
            run_scraper(root_path)
        elif choice.startswith("8)"):
            run_analyzer(root_path)
        elif choice.startswith("9)"):
            run_cleaner(root_path, args.dry_run)
            run_doctor(root_path, args.dry_run)
            run_matcher(root_path, args.dry_run)
        elif choice.startswith("q)"):
            console.print("Bye!")
            sys.exit(0)
            
        if not Confirm.ask("Back to Main Menu?", default=True):
            sys.exit(0)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        console.print("\n[red]Aborted by user.[/red]")
        sys.exit(1)
