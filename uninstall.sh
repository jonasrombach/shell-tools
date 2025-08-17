#!/usr/bin/env bash

# Terminal Tools Uninstallation Script
# This script removes the terminal-tools scripts directory from your PATH

set -e

# Colors for output
RED="\033[0;31m"
GREEN="\033[1;32m"
YELLOW="\033[1;33m"
BLUE="\033[1;34m"
NC="\033[0m"

# Get the directory where this script is located
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SCRIPTS_DIR="$SCRIPT_DIR/scripts"

# Function to detect shell and get profile file
get_shell_profile() {
    local shell_name
    shell_name="$(basename "$SHELL")"
    
    case "$shell_name" in
        bash)
            if [[ -f "$HOME/.bashrc" ]]; then
                echo "$HOME/.bashrc"
            elif [[ -f "$HOME/.bash_profile" ]]; then
                echo "$HOME/.bash_profile"
            else
                echo "$HOME/.bashrc"
            fi
            ;;
        zsh)
            echo "$HOME/.zshrc"
            ;;
        fish)
            echo "$HOME/.config/fish/config.fish"
            ;;
        *)
            echo "$HOME/.profile"
            ;;
    esac
}

# Function to remove PATH from shell profile
remove_from_path() {
    local shell_profile
    shell_profile="$(get_shell_profile)"
    
    echo -e "${BLUE}🗑️  Removing scripts directory from PATH...${NC}"
    
    if [[ ! -f "$shell_profile" ]]; then
        echo -e "${YELLOW}ℹ️  Profile file $shell_profile does not exist${NC}"
        return 0
    fi
    
    # Check if the PATH export exists
    if ! grep -q "export PATH.*$SCRIPTS_DIR" "$shell_profile"; then
        echo -e "${YELLOW}ℹ️  No terminal-tools PATH entry found in $shell_profile${NC}"
        return 0
    fi
    
    # Create a backup of the profile
    cp "$shell_profile" "$shell_profile.backup.$(date +%s)"
    echo -e "${BLUE}📋 Created backup: $shell_profile.backup.$(date +%s)${NC}"
    
    # Remove the terminal-tools lines
    # Remove the comment line and the export line
    sed -i.tmp '/# Added by terminal-tools install script/,+1d' "$shell_profile"
    rm "$shell_profile.tmp" 2>/dev/null || true
    
    # Also remove any standalone export lines (in case comment was removed manually)
    sed -i.tmp "\|export PATH.*$SCRIPTS_DIR|d" "$shell_profile"
    rm "$shell_profile.tmp" 2>/dev/null || true
    
    echo -e "${GREEN}✅ Removed terminal-tools from PATH in $shell_profile${NC}"
    echo -e "${YELLOW}💡 Restart your terminal or run: source $shell_profile${NC}"
    
    return 0
}

# Function to show usage
show_usage() {
    echo "Terminal Tools Uninstallation Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "This script removes the terminal-tools scripts directory from your PATH."
    echo ""
    echo "Options:"
    echo "  --help      Show this help message"
    echo ""
    echo "The script will automatically detect your shell and remove the PATH entry"
    echo "from the appropriate profile file (.bashrc, .zshrc, etc.)."
}

# Main uninstallation logic
main() {
    # Parse command line arguments
    case "${1:-}" in
        --help|-h)
            show_usage
            exit 0
            ;;
        "")
            echo -e "${BLUE}🗑️  Terminal Tools Uninstallation${NC}"
            echo ""
            echo "This will remove the scripts directory from your PATH."
            echo ""
            remove_from_path
            ;;
        *)
            echo -e "${RED}❌ Error:${NC} Unknown option: $1"
            echo ""
            show_usage
            exit 1
            ;;
    esac
}

# Run main function
main "$@"