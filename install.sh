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

# Only installation may invoke a package manager; repair runs stay offline.
install_dependencies() {
    if [[ $(uname -s) != Darwin ]]; then
        echo "These tools require macOS." >&2
        exit 1
    fi
    local missing=() dependency brew_prefix
    for dependency in blueutil jq; do
        command -v "$dependency" >/dev/null 2>&1 || missing+=("$dependency")
    done
    if ! command -v python3 >/dev/null 2>&1 ||
       ! python3 -c 'import sys; sys.exit(sys.version_info < (3, 10))'; then
        missing+=(python)
    fi
    if [[ ${#missing[@]} -gt 0 ]]; then
        if ! command -v brew >/dev/null 2>&1; then
            echo "Install Homebrew from https://brew.sh, open a new terminal, then rerun ./install.sh." >&2
            echo "Missing dependencies: ${missing[*]}" >&2
            exit 1
        fi
        brew install "${missing[@]}"
        # Prefer Homebrew Python over an older macOS/developer-tools copy.
        if [[ " ${missing[*]} " == *" python "* ]]; then
            brew_prefix="$(brew --prefix)"
            export PATH="$brew_prefix/bin:$PATH"
        fi
    fi
    /bin/bash "$SCRIPTS_DIR/lib/magic-repair/setup-ui"
}

# Function to detect shell and get profile file
get_shell_profile() {
    local shell_name
    shell_name="$(basename "$SHELL")"
    
    case "$shell_name" in
        bash)
            # macOS terminal windows normally start login shells.
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

# Function to add PATH to shell profile
add_to_path() {
    local shell_profile
    shell_profile="$(get_shell_profile)"
    local quoted_dir path_line
    # Shell-quote paths, including spaces, quotes and dollar signs.
    quoted_dir="'$(printf '%s' "$SCRIPTS_DIR" | sed "s/'/'\\\\''/g")'"
    if [[ $(basename "$SHELL") == fish ]]; then
        path_line="fish_add_path $quoted_dir"
    else
        path_line="export PATH=$quoted_dir:\$PATH"
    fi
    
    echo -e "${BLUE}📦 Adding scripts directory to PATH...${NC}"
    
    # Check if already in PATH
    if is_in_path "$SCRIPTS_DIR"; then
        echo -e "${GREEN}✅ Scripts directory is already in PATH${NC}"
        return 0
    fi
    
    # Check if the line already exists in the profile
    if [[ -f "$shell_profile" ]] && grep -Fq -- "$path_line" "$shell_profile"; then
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
    echo "It also installs the Magic Repair UI dependencies in an isolated environment."
    echo "Missing blueutil, jq and Python 3.10+ are installed using Homebrew."
    echo "Install Homebrew first from https://brew.sh if needed."
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
            chmod +x "$SCRIPTS_DIR/magic-repair" "$SCRIPTS_DIR/mirror-repair"
            install_dependencies
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
