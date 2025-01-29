#!/bin/bash

# Define colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to check required commands
check_requirements() {
    local missing_tools=()
    
    for tool in dconf gsettings wget curl gnome-shell; do
        if ! command -v "$tool" &> /dev/null; then
            missing_tools+=("$tool")
        fi
    done
    
    if [ ${#missing_tools[@]} -ne 0 ]; then
        echo -e "${RED}Error: Missing required tools: ${missing_tools[*]}${NC}"
        echo "Please install them using:"
        echo "sudo apt install dconf-cli gnome-settings-daemon wget curl gnome-shell"
        exit 1
    fi
}

# Function to backup installed packages
backup_packages() {
    local backup_dir="$1"
    
    # Backup manually installed packages
    echo -e "${YELLOW}Backing up package list...${NC}"
    apt list --manual-installed 2>/dev/null | grep -v "Listing..." > "$backup_dir/manual-packages.list"
    
    # Backup PPAs
    echo -e "${YELLOW}Backing up PPAs...${NC}"
    grep -r "^deb" /etc/apt/sources.list /etc/apt/sources.list.d/ > "$backup_dir/sources.list"
    
    # Backup Flatpak packages
    if command -v flatpak &> /dev/null; then
        echo -e "${YELLOW}Backing up Flatpak packages...${NC}"
        flatpak list --app --columns=application > "$backup_dir/flatpak-packages.list"
    fi
    
    # Backup Snap packages
    if command -v snap &> /dev/null; then
        echo -e "${YELLOW}Backing up Snap packages...${NC}"
        snap list | awk 'NR>1 {print $1}' > "$backup_dir/snap-packages.list"
    fi
}

# Function to backup GNOME extensions
backup_extensions() {
    local backup_dir="$1"
    
    echo -e "${YELLOW}Backing up GNOME extensions...${NC}"
    
    # Get list of enabled extensions
    enabled_extensions=$(gsettings get org.gnome.shell enabled-extensions | tr -d '[],' | tr "'" '\n' | grep -v '^$')
    
    # Create extensions directory
    mkdir -p "$backup_dir/extensions"
    
    # Save enabled extensions list
    echo "$enabled_extensions" > "$backup_dir/enabled-extensions.list"
    
    # For each enabled extension, save its UUID and version
    for ext in $enabled_extensions; do
        if [ -d "$HOME/.local/share/gnome-shell/extensions/$ext" ]; then
            # Copy the entire extension directory
            cp -r "$HOME/.local/share/gnome-shell/extensions/$ext" "$backup_dir/extensions/"
            
            # Get metadata
            if [ -f "$HOME/.local/share/gnome-shell/extensions/$ext/metadata.json" ]; then
                cp "$HOME/.local/share/gnome-shell/extensions/$ext/metadata.json" "$backup_dir/extensions/$ext-metadata.json"
            fi
        fi
    done
}

# Function to backup web apps
backup_web_apps() {
    local backup_dir="$1"
    
    echo -e "${YELLOW}Backing up web apps...${NC}"
    
    # Create web apps directory
    mkdir -p "$backup_dir/web-apps"
    
    # Backup Chrome web apps if they exist
    if [ -d "$HOME/.local/share/applications" ]; then
        find "$HOME/.local/share/applications" -name "chrome-*.desktop" -exec cp {} "$backup_dir/web-apps/" \;
    fi
    
    # Backup Firefox web apps if they exist
    if [ -d "$HOME/.mozilla/firefox" ]; then
        find "$HOME/.mozilla/firefox" -name "*.desktop" -exec cp {} "$backup_dir/web-apps/" \;
    fi
}

# Function to backup settings
backup_settings() {
    local backup_dir="$1"
    local timestamp=$(date +%Y%m%d_%H%M%S)
    
    # Create backup directory
    mkdir -p "$backup_dir"
    
    echo -e "${YELLOW}Backing up GNOME settings...${NC}"
    
    # Backup all dconf settings
    dconf dump / > "$backup_dir/dconf-settings-$timestamp.ini"
    
    # Backup specific GNOME settings
    dconf dump /org/gnome/ > "$backup_dir/gnome-settings-$timestamp.ini"
    
    # Backup keyboard shortcuts
    dconf dump /org/gnome/desktop/wm/keybindings/ > "$backup_dir/keyboard-shortcuts-$timestamp.ini"
    dconf dump /org/gnome/shell/keybindings/ > "$backup_dir/shell-shortcuts-$timestamp.ini"
    
    # Backup terminal settings
    dconf dump /org/gnome/terminal/ > "$backup_dir/terminal-settings-$timestamp.ini"
    
    # Backup favorite apps
    dconf dump /org/gnome/shell/favorite-apps > "$backup_dir/favorite-apps-$timestamp.ini"
    
    # Backup packages, extensions, and web apps
    backup_packages "$backup_dir"
    backup_extensions "$backup_dir"
    backup_web_apps "$backup_dir"
    
    # Create manifest file
    {
        echo "Backup created on: $(date)"
        echo "Ubuntu version: $(lsb_release -ds)"
        echo "GNOME version: $(gnome-shell --version)"
        echo "Hostname: $(hostname)"
        echo "User: $USER"
    } > "$backup_dir/manifest-$timestamp.txt"
    
    # Create restore script
    cat > "$backup_dir/restore.sh" << 'EOL'
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
        
        # Enable extensions
        while read -r uuid; do
            gnome-shell-extension-tool -e "$uuid" || true
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
EOL
    
    # Make restore script executable
    chmod +x "$backup_dir/restore.sh"
    
    # Generate backup summary
    echo -e "\n${GREEN}=== Backup Summary ===${NC}"
    
    # List backed up settings
    echo -e "\n${YELLOW}GNOME Settings Backed Up:${NC}"
    echo "- General GNOME settings and configurations"
    echo "- Keyboard shortcuts and keybindings"
    echo "- Terminal preferences and profiles"
    echo "- Favorite applications and dock settings"
    
    # List extensions
    if [ -f "$backup_dir/enabled-extensions.list" ]; then
        echo -e "\n${YELLOW}GNOME Extensions Backed Up:${NC}"
        while read -r ext; do
            if [ -f "$backup_dir/extensions/$ext-metadata.json" ]; then
                name=$(grep -o '"name"[^,]*' "$backup_dir/extensions/$ext-metadata.json" | cut -d'"' -f4)
                [ -n "$name" ] && echo "- $name ($ext)" || echo "- $ext"
            else
                echo "- $ext"
            fi
        done < "$backup_dir/enabled-extensions.list"
    fi
    
    # List manually installed packages
    if [ -f "$backup_dir/manual-packages.list" ]; then
        echo -e "\n${YELLOW}Manually Installed Packages Backed Up:${NC}"
        grep -v '^Listing' "$backup_dir/manual-packages.list" | cut -d'/' -f1 | head -n 10 | sed 's/^/- /'
        pkg_count=$(grep -v '^Listing' "$backup_dir/manual-packages.list" | wc -l)
        if [ $pkg_count -gt 10 ]; then
            echo "- ... and $((pkg_count - 10)) more packages"
        fi
    fi
    
    # List Flatpak packages
    if [ -f "$backup_dir/flatpak-packages.list" ] && [ -s "$backup_dir/flatpak-packages.list" ]; then
        echo -e "\n${YELLOW}Flatpak Packages Backed Up:${NC}"
        head -n 10 "$backup_dir/flatpak-packages.list" | sed 's/^/- /'
        pkg_count=$(wc -l < "$backup_dir/flatpak-packages.list")
        if [ $pkg_count -gt 10 ]; then
            echo "- ... and $((pkg_count - 10)) more Flatpak packages"
        fi
    fi
    
    # List Snap packages
    if [ -f "$backup_dir/snap-packages.list" ] && [ -s "$backup_dir/snap-packages.list" ]; then
        echo -e "\n${YELLOW}Snap Packages Backed Up:${NC}"
        head -n 10 "$backup_dir/snap-packages.list" | sed 's/^/- /'
        pkg_count=$(wc -l < "$backup_dir/snap-packages.list")
        if [ $pkg_count -gt 10 ]; then
            echo "- ... and $((pkg_count - 10)) more Snap packages"
        fi
    fi
    
    # List web apps
    if [ -d "$backup_dir/web-apps" ]; then
        echo -e "\n${YELLOW}Web Apps Backed Up:${NC}"
        find "$backup_dir/web-apps" -name "*.desktop" -exec basename {} .desktop \; | sed 's/^/- /'
    fi
    
    echo -e "\n${GREEN}Backup completed successfully!${NC}"
    echo "Backup files are stored in: $backup_dir"
    echo -e "\n${YELLOW}To restore on another machine:${NC}"
    echo "1. Copy the entire backup directory to the target machine"
    echo "2. Navigate to the backup directory"
    echo "3. Run ./restore.sh"
}

# Main script
main() {
    if [ "$EUID" -eq 0 ]; then
        echo -e "${RED}Please do not run this script as root. It will ask for sudo when needed.${NC}"
        exit 1
    fi
    
    check_requirements
    
    backup_dir="$HOME/gnome-settings-backup"
    backup_settings "$backup_dir"
}

# Run main function
main