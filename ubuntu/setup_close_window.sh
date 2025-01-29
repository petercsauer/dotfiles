#!/bin/bash

# Check if gsettings is available
if ! command -v gsettings &> /dev/null; then
    echo "Error: gsettings is not installed. Please install it first."
    exit 1
fi

# Backup current close window keybinding
echo "Creating backup of current close window keybinding..."
timestamp=$(date +%Y%m%d_%H%M%S)
dconf dump /org/gnome/desktop/wm/keybindings/ > ~/close_window_backup_$timestamp.dconf

# Set Super+Q to close window
echo "Setting up Super+Q for closing windows..."
gsettings set org.gnome.desktop.wm.keybindings close "['<Super>q']"

# Verify the changes
echo "Verifying settings..."
current_binding=$(gsettings get org.gnome.desktop.wm.keybindings close)
echo "Current binding for close window: $current_binding"

echo "Setup complete!"
echo "Backup file has been created: ~/close_window_backup_$timestamp.dconf"
echo ""
echo "To restore the backup if needed, run:"
echo "dconf load /org/gnome/desktop/wm/keybindings/ < ~/close_window_backup_$timestamp.dconf"