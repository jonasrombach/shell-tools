#!/usr/bin/env bash

# Shell Tools Uninstallation Script
# This script removes the shell-tools scripts directory from your PATH

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
            if [[ -f "$HOME/.bash_profile" ]]; then
                echo "$HOME/.bash_profile"
            elif [[ -f "$HOME/.bash_login" ]]; then
                echo "$HOME/.bash_login"
            elif [[ -f "$HOME/.profile" ]]; then
                echo "$HOME/.profile"
            else
                echo "$HOME/.bash_profile"
            fi
            ;;
        zsh)
            echo "${ZDOTDIR:-$HOME}/.zshrc"
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
    local shell_profile quoted_dir
    shell_profile="$(get_shell_profile)"
    quoted_dir="'$(printf '%s' "$SCRIPTS_DIR" | sed "s/'/'\\\\''/g")'"
    
    echo -e "${BLUE}🗑️  Removing scripts directory from PATH...${NC}"
    
    if [[ ! -f "$shell_profile" ]]; then
        echo -e "${YELLOW}ℹ️  Profile file $shell_profile does not exist${NC}"
        return 0
    fi
    
    # Check if the PATH export exists
    if ! grep -Fq -- "$SCRIPTS_DIR" "$shell_profile" &&
       ! grep -Fq -- "$quoted_dir" "$shell_profile"; then
        echo -e "${YELLOW}ℹ️  No shell-tools PATH entry found in $shell_profile${NC}"
        return 0
    fi
    
    # Create a backup of the profile
    cp "$shell_profile" "$shell_profile.backup.$(date +%s)"
    echo -e "${BLUE}📋 Created backup: $shell_profile.backup.$(date +%s)${NC}"
    
    # Match both older exports and the installer's shell-quoted path literally.
    SHELL_TOOLS_PATH="$SCRIPTS_DIR" SHELL_TOOLS_QUOTED_PATH="$quoted_dir" awk '
        $0 == "# Added by shell-tools install script" { next }
        /^(export PATH=|fish_add_path )/ && (index($0, ENVIRON["SHELL_TOOLS_PATH"]) || index($0, ENVIRON["SHELL_TOOLS_QUOTED_PATH"])) { next }
        { print }
    ' "$shell_profile" > "$shell_profile.tmp"
    cat "$shell_profile.tmp" > "$shell_profile"
    rm "$shell_profile.tmp"
    
    echo -e "${GREEN}✅ Removed shell-tools from PATH in $shell_profile${NC}"
    echo -e "${YELLOW}💡 Restart your terminal or run: source $shell_profile${NC}"
    
    return 0
}

# Function to show usage
show_usage() {
    echo "Shell Tools Uninstallation Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "This script removes the shell-tools scripts directory from your PATH."
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
            echo -e "${BLUE}🗑️  Shell Tools Uninstallation${NC}"
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
