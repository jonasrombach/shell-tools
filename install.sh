#!/usr/bin/env bash

# Shell Tools Installation Script
# This script makes shell-tools scripts accessible from the command line
# by adding the scripts directory to your PATH

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

# Function to add PATH to shell profile
add_to_path() {
    local shell_profile
    shell_profile="$(get_shell_profile)"
    local path_line="export PATH=\"$SCRIPTS_DIR:\$PATH\""
    
    echo -e "${BLUE}📦 Adding scripts directory to PATH...${NC}"
    
    # Check if already in PATH
    if is_in_path "$SCRIPTS_DIR"; then
        echo -e "${GREEN}✅ Scripts directory is already in PATH${NC}"
        return 0
    fi
    
    # Check if the line already exists in the profile
    if [[ -f "$shell_profile" ]] && grep -q "export PATH.*$SCRIPTS_DIR" "$shell_profile"; then
        echo -e "${GREEN}✅ PATH export already exists in $shell_profile${NC}"
        echo -e "${YELLOW}💡 Restart your terminal or run: source $shell_profile${NC}"
        return 0
    fi
    
    # Create directory for profile if it doesn't exist (for fish)
    local profile_dir
    profile_dir="$(dirname "$shell_profile")"
    if [[ ! -d "$profile_dir" ]]; then
        mkdir -p "$profile_dir"
    fi
    
    # Add the export line to the profile
    {
        echo ""
        echo "# Added by shell-tools install script"
        echo "$path_line"
    } >> "$shell_profile"
    
    echo -e "${GREEN}✅ Added scripts directory to PATH in $shell_profile${NC}"
    echo -e "${YELLOW}💡 Restart your terminal or run: source $shell_profile${NC}"
    
    # List available scripts
    echo -e "${BLUE}📋 Available scripts:${NC}"
    for script in "$SCRIPTS_DIR"/*; do
        if [[ -f "$script" && -x "$script" ]]; then
            local script_name
            script_name="$(basename "$script")"
            echo -e "${GREEN}  ✅ $script_name${NC}"
        fi
    done
    
    return 0
}

# Function to show usage
show_usage() {
    echo "Shell Tools Installation Script"
    echo ""
    echo "Usage: $0 [OPTIONS]"
    echo ""
    echo "This script adds the shell-tools scripts directory to your PATH,"
    echo "making all scripts accessible from the command line without copying them."
    echo ""
    echo "Options:"
    echo "  --help      Show this help message"
    echo ""
    echo "The script will automatically detect your shell and update the appropriate"
    echo "profile file (.bashrc, .zshrc, etc.) to include the scripts directory in PATH."
}

# Main installation logic
main() {
    # Parse command line arguments
    case "${1:-}" in
        --help|-h)
            show_usage
            exit 0
            ;;
        "")
            echo -e "${BLUE}🚀 Shell Tools Installation${NC}"
            echo ""
            echo "This will add the scripts directory to your PATH, making all"
            echo "shell-tools scripts accessible from anywhere in your terminal."
            echo ""
            # Ensure all scripts are executable
            echo -e "${BLUE}🔑 Ensuring all scripts are executable...${NC}"
            chmod +x "$SCRIPTS_DIR"/*
            add_to_path
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