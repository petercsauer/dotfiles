#!/bin/bash

# Check if gsettings is available
if ! command -v gsettings &> /dev/null; then
    echo "Error: gsettings is not installed. Please install it first."
    exit 1
fi

# Backup current keybindings
echo "Creating backup of current keybindings..."
timestamp=$(date +%Y%m%d_%H%M%S)
dconf dump /org/gnome/desktop/wm/keybindings/ > ~/keybindings_backup_$timestamp.dconf
dconf dump /org/gnome/shell/keybindings/ > ~/shell_keybindings_backup_$timestamp.dconf

# Set Super+Shift+Tab to switch between windows of current application
echo "Setting up Super+Shift+Tab for switching between windows of current application..."
gsettings set org.gnome.desktop.wm.keybindings switch-group "['<Super><Shift>Tab']"

# Verify the changes
echo "Verifying settings..."
current_binding=$(gsettings get org.gnome.desktop.wm.keybindings switch-group)
echo "Current binding for switch-group: $current_binding"

echo "Setup complete!"
echo "Backup files have been created in your home directory:"
echo "~/keybindings_backup_$timestamp.dconf"
echo "~/shell_keybindings_backup_$timestamp.dconf"
echo ""
echo "To restore the backup if needed, run:"
echo "dconf load /org/gnome/desktop/wm/keybindings/ < ~/keybindings_backup_$timestamp.dconf"
echo "dconf load /org/gnome/shell/keybindings/ < ~/shell_keybindings_backup_$timestamp.dconf"