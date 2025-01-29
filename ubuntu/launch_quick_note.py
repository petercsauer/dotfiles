#!/usr/bin/env python3
import subprocess
import sys
import os
import logging
from pathlib import Path
from datetime import datetime
import time
from urllib.parse import quote

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / '.obsidian-launcher.log'),
        logging.StreamHandler()
    ]
)

def launch_obsidian():
    """Launch Obsidian and create/open a quick note."""
    try:
        vault_id = "EpiSci"  # Your vault ID
        timestamp = datetime.now().strftime('%Y-%m-%d-%H%M%S')
        note_path = f"Quick Notes/Note {timestamp}.md"
        
        # Create quick note
        create_quick_note("EpiSci", note_path)
        
        # Launch Obsidian first with vault ID
        subprocess.Popen([
            'flatpak', 'run', 'md.obsidian.Obsidian',
            '--new-window',
            f'obsidian://vault/{vault_id}'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Give Obsidian time to load and index
        time.sleep(0)
        
        # Try to get window focus
        try:
            subprocess.run(['wmctrl', '-a', 'Obsidian'], check=True)
            time.sleep(0.5)
        except subprocess.CalledProcessError:
            logging.warning("Couldn't focus window, continuing anyway")
        
        # Now open the specific note
        encoded_path = quote(note_path)
        subprocess.run([
            'xdg-open',
            f'obsidian://open?vault={vault_id}&file={encoded_path}&line=9999'
        ], check=True)
        
        logging.info(f"Launched Obsidian and opened note: {note_path}")
        
    except Exception as e:
        logging.error(f"Failed to launch Obsidian: {e}")
        sys.exit(1)

def create_quick_note(vault_name, note_path):
    """Create a quick note."""
    vault_path = os.path.expanduser(f"~/Documents/{vault_name}")
    full_note_path = os.path.join(vault_path, note_path)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(full_note_path), exist_ok=True)
    
    # Create the note
    if not os.path.exists(full_note_path):
        timestamp = datetime.now().strftime('%Y-%m-%d %H:%M:%S')
        template = f"""-
"""
        with open(full_note_path, 'w') as f:
            f.write(template)
        logging.info(f"Created new quick note: {full_note_path}")

if __name__ == "__main__":
    launch_obsidian()