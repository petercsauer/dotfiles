#!/bin/bash

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

# Function to install packages
install_packages() {
    local backup_dir="$1"
    
    # Add PPAs
    if [ -f "$backup_dir/sources.list" ]; then
        echo -e "${YELLOW}Restoring PPAs...${NC}"
        while read -r source; do
            sudo add-apt-repository -y "$source"
        done < "$backup_dir/sources.list"
        sudo apt update
    fi
    
    # Install packages
    if [ -f "$backup_dir/manual-packages.list" ]; then
        echo -e "${YELLOW}Installing packages...${NC}"
        while read -r package; do
            package_name=$(echo "$package" | cut -d'/' -f1)
            sudo apt install -y "$package_name"
        done < "$backup_dir/manual-packages.list"
    fi
    
    # Install Flatpak packages
    if [ -f "$backup_dir/flatpak-packages.list" ]; then
        echo -e "${YELLOW}Installing Flatpak packages...${NC}"
        while read -r package; do
            flatpak install -y "$package"
        done < "$backup_dir/flatpak-packages.list"
    fi
    
    # Install Snap packages
    if [ -f "$backup_dir/snap-packages.list" ]; then
        echo -e "${YELLOW}Installing Snap packages...${NC}"
        while read -r package; do
            sudo snap install "$package"
        done < "$backup_dir/snap-packages.list"
    fi
}

# Function to install GNOME extensions
install_extensions() {
    local backup_dir="$1"
    
    if [ -f "$backup_dir/enabled-extensions.list" ]; then
        echo -e "${YELLOW}Installing GNOME extensions...${NC}"
        
        # Install GNOME Shell integration for browsers if not present
        sudo apt install -y chrome-gnome-shell || true
        
        # Create extensions directory if it doesn't exist
        mkdir -p "$HOME/.local/share/gnome-shell/extensions"
        
        # Copy backed up extensions
        if [ -d "$backup_dir/extensions" ]; then
            cp -r "$backup_dir/extensions"/* "$HOME/.local/share/gnome-shell/extensions/"
        fi
        
        # Enable extensions and restore their settings
        while read -r uuid; do
            gnome-shell-extension-tool -e "$uuid" || true
            
            # Restore extension settings
            if [ -f "$backup_dir/extensions/$uuid-settings.dconf" ]; then
                dconf load "/org/gnome/shell/extensions/$uuid/" < "$backup_dir/extensions/$uuid-settings.dconf"
            fi
            
            # Restore settings from alternative paths if they exist
            for settings_file in "$backup_dir/extensions/$uuid-settings-"*.dconf; do
                if [ -f "$settings_file" ]; then
                    # Extract path from filename
                    path=$(echo "$settings_file" | sed 's/.*settings-//' | sed 's/\.dconf$//' | tr '-' '/' | sed 's/^/\//' | sed 's/$/\//')
                    dconf load "$path" < "$settings_file"
                fi
            done
        done < "$backup_dir/enabled-extensions.list"
    fi
}

# Function to restore web apps
restore_web_apps() {
    local backup_dir="$1"
    
    if [ -d "$backup_dir/web-apps" ]; then
        echo -e "${YELLOW}Restoring web apps...${NC}"
        
        # Create applications directory if it doesn't exist
        mkdir -p "$HOME/.local/share/applications"
        
        # Copy web app desktop files
        cp "$backup_dir/web-apps"/*.desktop "$HOME/.local/share/applications/"
    fi
}

# Function to restore settings
restore_settings() {
    local backup_dir="$1"
    
    # Get the most recent backup files
    dconf_backup=$(ls -t "$backup_dir"/dconf-settings-*.ini | head -1)
    gnome_backup=$(ls -t "$backup_dir"/gnome-settings-*.ini | head -1)
    kb_backup=$(ls -t "$backup_dir"/keyboard-shortcuts-*.ini | head -1)
    shell_backup=$(ls -t "$backup_dir"/shell-shortcuts-*.ini | head -1)
    term_backup=$(ls -t "$backup_dir"/terminal-settings-*.ini | head -1)
    apps_backup=$(ls -t "$backup_dir"/favorite-apps-*.ini | head -1)
    
    echo -e "${YELLOW}Restoring GNOME settings...${NC}"
    
    # Restore settings
    dconf load / < "$dconf_backup"
    dconf load /org/gnome/ < "$gnome_backup"
    dconf load /org/gnome/desktop/wm/keybindings/ < "$kb_backup"
    dconf load /org/gnome/shell/keybindings/ < "$shell_backup"
    dconf load /org/gnome/terminal/ < "$term_backup"
    dconf load /org/gnome/shell/favorite-apps < "$apps_backup"
}

# Main restore function
main() {
    if [ "$EUID" -eq 0 ]; then
        echo -e "${RED}Please do not run this script as root. It will ask for sudo when needed.${NC}"
        exit 1
    fi
    
    # Get the directory where the script is located
    SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
    
    # Install packages first
    install_packages "$SCRIPT_DIR"
    
    # Install GNOME extensions
    install_extensions "$SCRIPT_DIR"
    
    # Restore web apps
    restore_web_apps "$SCRIPT_DIR"
    
    # Restore settings
    restore_settings "$SCRIPT_DIR"
    
    echo -e "${GREEN}Restore completed!${NC}"
    echo "Please log out and log back in for all settings to take effect."
}

# Run main function
main
