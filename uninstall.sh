#!/usr/bin/env bash

# Terminal Tools Uninstallation Script
# This script removes terminal-tools scripts from your system

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

# Function to remove scripts from a directory
remove_from_dir() {
    local target_dir="$1"
    local removed_count=0
    
    echo -e "${BLUE}🗑️  Removing scripts from $target_dir...${NC}"
    
    if [[ ! -d "$target_dir" ]]; then
        echo -e "${YELLOW}⚠️  Directory $target_dir does not exist${NC}"
        return 0
    fi
    
    # Remove each script that was installed
    for script in "$SCRIPTS_DIR"/*; do
        if [[ -f "$script" && -x "$script" ]]; then
            local script_name
            script_name="$(basename "$script")"
            local target_path="$target_dir/$script_name"
            
            if [[ -L "$target_path" ]]; then
                # Check if it's a symlink to our script
                local link_target
                link_target="$(readlink "$target_path")"
                if [[ "$link_target" == "$script" ]]; then
                    rm "$target_path"
                    echo -e "${GREEN}✅ Removed: $script_name${NC}"
                    removed_count=$((removed_count + 1))
                else
                    echo -e "${YELLOW}⚠️  Skipped: $script_name (not linked to this repository)${NC}"
                fi
            elif [[ -f "$target_path" ]]; then
                echo -e "${YELLOW}⚠️  Found: $script_name (not a symlink, manual removal required)${NC}"
            fi
        fi
    done
    
    if [[ $removed_count -eq 0 ]]; then
        echo -e "${YELLOW}ℹ️  No terminal-tools scripts found in $target_dir${NC}"
    else
        echo -e "${GREEN}🎉 Successfully removed $removed_count script(s)${NC}"
    fi
    
    return 0
}

# Function to show usage
show_usage() {
    echo "Terminal Tools Uninstallation Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --user      Remove from ~/.local/bin"
    echo "  --system    Remove from /usr/local/bin (requires sudo)"
    echo "  --dir DIR   Remove from custom directory DIR"
    echo "  --all       Remove from common installation directories"
    echo "  --help      Show this help message"
    echo ""
    echo "If no option is specified, the script will prompt for removal location."
}

# Function to prompt for removal location
prompt_for_location() {
    echo -e "${BLUE}🗑️  Terminal Tools Uninstallation${NC}"
    echo ""
    echo "Choose removal location:"
    echo "1) ~/.local/bin (user-specific)"
    echo "2) /usr/local/bin (system-wide, requires sudo)"
    echo "3) All common locations"
    echo "4) Custom directory"
    echo "5) Cancel uninstallation"
    echo ""
    
    while true; do
        read -r -p "Enter your choice (1-5): " choice
        case $choice in
            1)
                remove_from_dir "$HOME/.local/bin"
                return $?
                ;;
            2)
                if [[ $EUID -eq 0 ]]; then
                    remove_from_dir "/usr/local/bin"
                else
                    echo -e "${YELLOW}🔐 Removing from /usr/local/bin requires sudo...${NC}"
                    sudo "$0" --system
                fi
                return $?
                ;;
            3)
                remove_from_dir "$HOME/.local/bin"
                if [[ $EUID -eq 0 ]]; then
                    remove_from_dir "/usr/local/bin"
                else
                    echo -e "${YELLOW}🔐 Checking /usr/local/bin requires sudo...${NC}"
                    sudo "$0" --system
                fi
                return $?
                ;;
            4)
                read -r -p "Enter custom directory path: " custom_dir
                if [[ -n "$custom_dir" ]]; then
                    remove_from_dir "$custom_dir"
                    return $?
                else
                    echo -e "${RED}❌ Invalid directory${NC}"
                fi
                ;;
            5)
                echo -e "${YELLOW}Uninstallation cancelled${NC}"
                return 1
                ;;
            *)
                echo -e "${RED}Invalid choice. Please enter 1, 2, 3, 4, or 5.${NC}"
                ;;
        esac
    done
}

# Function to remove from all common locations
remove_from_all() {
    echo -e "${BLUE}🗑️  Removing from all common locations...${NC}"
    
    # User directory
    if [[ -d "$HOME/.local/bin" ]]; then
        remove_from_dir "$HOME/.local/bin"
    fi
    
    # System directory (requires sudo if not root)
    if [[ -d "/usr/local/bin" ]]; then
        if [[ $EUID -eq 0 ]]; then
            remove_from_dir "/usr/local/bin"
        else
            echo -e "${YELLOW}🔐 Checking /usr/local/bin requires sudo...${NC}"
            sudo "$0" --system
        fi
    fi
}

# Main uninstallation logic
main() {
    # Parse command line arguments
    case "${1:-}" in
        --help|-h)
            show_usage
            exit 0
            ;;
        --user)
            remove_from_dir "$HOME/.local/bin"
            ;;
        --system)
            remove_from_dir "/usr/local/bin"
            ;;
        --dir)
            if [[ -z "${2:-}" ]]; then
                echo -e "${RED}❌ Error:${NC} --dir requires a directory argument"
                exit 1
            fi
            remove_from_dir "$2"
            ;;
        --all)
            remove_from_all
            ;;
        "")
            prompt_for_location
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