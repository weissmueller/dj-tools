import os
import json
import subprocess
from rich.console import Console
from rich.prompt import Confirm

class OneTaggerModule:
    def __init__(self, config_path="onetagger_config.json"):
        self.config_path = config_path
        self.console = Console()

    def run_tagger(self, target_path):
        """Runs onetagger-cli on the target path."""
        
        # 1. Update config with correct path
        if not os.path.exists(self.config_path):
            self.console.print(f"[red]Config file not found: {self.config_path}[/red]")
            return False

        try:
            with open(self.config_path, "r") as f:
                config_data = json.load(f)
            
            # Update path in config
            config_data["path"] = target_path
            
            # Write updated config (temporarily overwriting the file might be okay since we reload each time, 
            # or we could make a temp file. Let's stick with updating the main one for simplicity, 
            # as it's just a config file for this run)
            with open(self.config_path, "w") as f:
                json.dump(config_data, f, indent=4)
                
        except Exception as e:
            self.console.print(f"[red]Failed to update config: {e}[/red]")
            return False

        # 2. Run the command
        cmd = ["./onetagger-cli", "autotagger", "--config", self.config_path, "--path", target_path]
        
        self.console.print(f"[cyan]Running OneTagger on: {target_path}[/cyan]")
        self.console.print(f"[dim]Command: {' '.join(cmd)}[/dim]")

        try:
            # Using Popen to stream output or just run it interactively
            # Since onetagger-cli is a CLI tool, let's just use subprocess.run so user sees output
            # or stream it.
            
            # Using run first to keep it simple, letting it inherit stdout/stderr
            result = subprocess.run(cmd, check=False) 
            
            if result.returncode == 0:
                self.console.print("[green]OneTagger completed successfully![/green]")
                return True
            else:
                self.console.print(f"[red]OneTagger failed with exit code {result.returncode}[/red]")
                return False
                
        except FileNotFoundError:
             self.console.print("[red]onetagger-cli binary not found in current directory![/red]")
             return False
        except Exception as e:
            self.console.print(f"[red]Error running onetagger: {e}[/red]")
            return False
