#!/usr/bin/env bash

# Terminal Tools Installation Script
# This script installs terminal-tools scripts to your system

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

# Check if scripts directory exists
if [[ ! -d "$SCRIPTS_DIR" ]]; then
    echo -e "${RED}❌ Error:${NC} Scripts directory not found at $SCRIPTS_DIR"
    exit 1
fi

# Function to check if a directory is in PATH
is_in_path() {
    local dir="$1"
    case ":$PATH:" in
        *":$dir:"*) return 0 ;;
        *) return 1 ;;
    esac
}

# Function to install scripts to a directory
install_to_dir() {
    local target_dir="$1"
    local created_links=()
    
    echo -e "${BLUE}📦 Installing scripts to $target_dir...${NC}"
    
    # Create target directory if it doesn't exist
    if [[ ! -d "$target_dir" ]]; then
        mkdir -p "$target_dir"
        echo -e "${YELLOW}📁 Created directory: $target_dir${NC}"
    fi
    
    # Install each script
    for script in "$SCRIPTS_DIR"/*; do
        if [[ -f "$script" && -x "$script" ]]; then
            local script_name="$(basename "$script")"
            local target_path="$target_dir/$script_name"
            
            # Remove existing link/file if it exists
            if [[ -e "$target_path" ]]; then
                rm "$target_path"
                echo -e "${YELLOW}🔄 Replaced existing: $script_name${NC}"
            fi
            
            # Create symlink
            ln -s "$script" "$target_path"
            created_links+=("$target_path")
            echo -e "${GREEN}✅ Installed: $script_name${NC}"
        fi
    done
    
    if [[ ${#created_links[@]} -eq 0 ]]; then
        echo -e "${YELLOW}⚠️  No executable scripts found to install${NC}"
        return 1
    fi
    
    echo -e "${GREEN}🎉 Successfully installed ${#created_links[@]} script(s)${NC}"
    
    # Check if target directory is in PATH
    if ! is_in_path "$target_dir"; then
        echo -e "${YELLOW}⚠️  Warning: $target_dir is not in your PATH${NC}"
        echo -e "${YELLOW}💡 Add this line to your shell profile (.bashrc, .zshrc, etc.):${NC}"
        echo -e "${BLUE}export PATH=\"$target_dir:\$PATH\"${NC}"
    fi
    
    return 0
}

# Function to show usage
show_usage() {
    echo "Terminal Tools Installation Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "Options:"
    echo "  --user      Install to ~/.local/bin (user-specific)"
    echo "  --system    Install to /usr/local/bin (system-wide, requires sudo)"
    echo "  --dir DIR   Install to custom directory DIR"
    echo "  --help      Show this help message"
    echo ""
    echo "If no option is specified, the script will prompt for installation location."
}

# Function to prompt for installation location
prompt_for_location() {
    echo -e "${BLUE}🚀 Terminal Tools Installation${NC}"
    echo ""
    echo "Choose installation location:"
    echo "1) ~/.local/bin (user-specific, recommended)"
    echo "2) /usr/local/bin (system-wide, requires sudo)"
    echo "3) Custom directory"
    echo "4) Cancel installation"
    echo ""
    
    while true; do
        read -p "Enter your choice (1-4): " choice
        case $choice in
            1)
                install_to_dir "$HOME/.local/bin"
                return $?
                ;;
            2)
                if [[ $EUID -eq 0 ]]; then
                    install_to_dir "/usr/local/bin"
                else
                    echo -e "${YELLOW}🔐 Installing to /usr/local/bin requires sudo...${NC}"
                    sudo "$0" --system
                fi
                return $?
                ;;
            3)
                read -p "Enter custom directory path: " custom_dir
                if [[ -n "$custom_dir" ]]; then
                    install_to_dir "$custom_dir"
                    return $?
                else
                    echo -e "${RED}❌ Invalid directory${NC}"
                fi
                ;;
            4)
                echo -e "${YELLOW}Installation cancelled${NC}"
                return 1
                ;;
            *)
                echo -e "${RED}Invalid choice. Please enter 1, 2, 3, or 4.${NC}"
                ;;
        esac
    done
}

# Main installation logic
main() {
    # Parse command line arguments
    case "${1:-}" in
        --help|-h)
            show_usage
            exit 0
            ;;
        --user)
            install_to_dir "$HOME/.local/bin"
            ;;
        --system)
            install_to_dir "/usr/local/bin"
            ;;
        --dir)
            if [[ -z "${2:-}" ]]; then
                echo -e "${RED}❌ Error:${NC} --dir requires a directory argument"
                exit 1
            fi
            install_to_dir "$2"
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