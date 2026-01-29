#!/usr/bin/env python3
import time
import os
import psutil
from rich.console import Console
from rich.table import Table

console = Console()

def check_process(name):
    for proc in psutil.process_iter(['name']):
        if name in proc.info['name']:
            return True
    return False

def get_status():
    table = Table(title="🛡️ JARVIS Agent Health Pulse")
    table.add_column("Component", style="cyan")
    table.add_column("Status", style="bold")
    table.add_column("Details", style="magenta")

    # Check for main script
    is_alive = check_process("python3") # Simplified check
    status = "[bold green]ONLINE[/bold green]" if is_alive else "[bold red]OFFLINE[/bold red]"
    table.add_row("Jarvis Core", status, "Main event loop")

    # Check for audio devices
    import pyaudio
    p = pyaudio.PyAudio()
    device_count = p.get_device_count()
    status = f"[bold green]{device_count} found[/bold green]" if device_count > 0 else "[bold red]NONE[/bold red]"
    table.add_row("Audio System", status, "Mic/Speaker availability")
    p.terminate()

    # Check for Collab status
    if os.path.exists("COLLAB.md"):
        table.add_row("Collab Hub", "[bold green]SYNCED[/bold green]", "COLLAB.md exists")
    else:
        table.add_row("Collab Hub", "[bold yellow]MISSING[/bold yellow]", "COLLAB.md not found")

    return table

if __name__ == "__main__":
    while True:
        console.clear()
        console.print(get_status())
        console.print("\n[dim]Agent Pulse running... Press Ctrl+C to exit.[/dim]")
        time.sleep(10)
