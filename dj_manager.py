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
        return args.root
    # Default to current directory or ask
    path = os.getcwd()
    if Confirm.ask(f"Use current directory as root? ({path})", default=True):
        return path
    return Prompt.ask("Enter root path").strip().strip("'").strip('"')

def run_cleaner(root_path, dry_run=False):
    console.print("[bold blue]== Module A: Interactive Cleaner ==[/bold blue]")
    
    mode = questionary.select(
        "Scan Mode:",
        choices=[
            "1. Deep Scan (Hash Content) - Slow, exact",
            "2. Quick Scan (Filename only) - Fast, ignores '01 - ' prefixes"
        ]
    ).ask()
    
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
            "a) Delete (Keep first found, delete others)",
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
    csv_path = Prompt.ask("Path to Exportify CSV").strip().strip("'").strip('"') # Clean quotes from drag&drop
    
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
            default_name = os.path.splitext(os.path.basename(csv_path))[0] + ".m3u8"
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
                "5) Full Auto-Mode (Run 1, 2, 3)",
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
