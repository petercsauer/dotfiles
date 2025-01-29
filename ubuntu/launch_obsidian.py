#!/usr/bin/env python3
import platform
import subprocess
import sys
import os
import logging
from pathlib import Path

# Set up logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler(Path.home() / '.obsidian-launcher.log'),
        logging.StreamHandler()
    ]
)

def get_os():
    """Detect the operating system."""
    system = platform.system().lower()
    if system not in ['darwin', 'linux']:
        logging.error(f"Unsupported operating system: {system}")
        sys.exit(1)
    return system

def launch_obsidian_macos():
    """Launch Obsidian on macOS."""
    try:
        subprocess.run(['open', '-n', '-a', 'Obsidian'], check=True)
        logging.info("Successfully launched Obsidian on macOS")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to launch Obsidian on macOS: {e}")
        sys.exit(1)

def launch_obsidian_linux():
    """Launch Obsidian on Linux."""
    appimage_path = os.path.expanduser('~/snap/obsidian/Obsidian.AppImage')
    
    try:
        if not os.path.isfile(appimage_path):
            logging.error(f"Obsidian AppImage not found at: {appimage_path}")
            sys.exit(1)
            
        subprocess.run([appimage_path, '--new-window'], check=True)
        logging.info("Successfully launched Obsidian")
    except subprocess.CalledProcessError as e:
        logging.error(f"Failed to launch Obsidian: {e}")
        sys.exit(1)

def main():
    """Main function to handle Obsidian launching."""
    try:
        os_type = get_os()
        
        if os_type == 'darwin':
            launch_obsidian_macos()
        elif os_type == 'linux':
            launch_obsidian_linux()
            
    except Exception as e:
        logging.error(f"Unexpected error: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()