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
    """Launch Obsidian and open daily note."""
    try:
        vault_name = "EpiSci"
        today = datetime.now().strftime('%Y-%m-%d')
        note_path = f"Daily TODO/{today}.md"
        
        # Create daily note first
        create_daily_note(vault_name, note_path)
        
        # Launch Obsidian first without file parameter
        subprocess.Popen([
            'flatpak', 'run', 'md.obsidian.Obsidian',
            '--new-window',
            f'obsidian://open?vault={vault_name}'
        ], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        
        # Give Obsidian time to load and index
        time.sleep(.5)
        
        # Try to get window focus first
        try:
            subprocess.run(['wmctrl', '-a', 'Obsidian'], check=True)
            time.sleep(0.5)
        except subprocess.CalledProcessError:
            logging.warning("Couldn't focus window, continuing anyway")
        
        # Now open the specific note
        encoded_path = quote(note_path)
        subprocess.run([
            'xdg-open',
            f'obsidian://open?vault={vault_name}&file={encoded_path}&line=9999'
        ], check=True)
        
        logging.info(f"Launched Obsidian and opened note: {note_path}")
        
    except Exception as e:
        logging.error(f"Failed to launch Obsidian: {e}")
        sys.exit(1)

def create_daily_note(vault_name, note_path):
    """Create the daily note if it doesn't exist."""
    vault_path = os.path.expanduser(f"~/Documents/{vault_name}")
    full_note_path = os.path.join(vault_path, note_path)
    
    # Create directory if it doesn't exist
    os.makedirs(os.path.dirname(full_note_path), exist_ok=True)
    
    # Create note if it doesn't exist
    if not os.path.exists(full_note_path):
        today = datetime.now().strftime('%Y-%m-%d')
        template = f"""## Tasks
- [ ] 
"""
        with open(full_note_path, 'w') as f:
            f.write(template)
        logging.info(f"Created new daily note: {full_note_path}")

if __name__ == "__main__":
    launch_obsidian()