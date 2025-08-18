# shell-tools
MacOS specific tools that make life easier.

## Installation

### Quick Install
```bash
# Clone the repository
git clone https://github.com/jonasrombach/shell-tools.git
cd shell-tools

# Install (adds scripts directory to PATH)
./install.sh
```

### How It Works

The installation script adds the repository's `scripts` directory to your PATH by modifying your shell profile (`.bashrc`, `.zshrc`, etc.). This means:

- Scripts remain in the repository directory
- No files are copied or symlinked elsewhere
- Updates via `git pull` immediately affect your installed tools
- Easy to uninstall by removing the PATH entry

### Installation Options

#### Interactive Installation
```bash
./install.sh
```
The script will automatically detect your shell and add the scripts directory to your PATH.

#### Command Line Options
```bash
./install.sh          # Interactive installation
./install.sh --help   # Show help
```

### Updating
Since scripts remain in the repository, updating is simple:
```bash
cd shell-tools
git pull origin main
# Scripts are immediately updated, no reinstallation needed
```

### Uninstallation
```bash
./uninstall.sh        # Remove scripts directory from PATH
./uninstall.sh --help # Show help
```

## Available Tools

### magic-repair
A tool to repair Apple Magic device Bluetooth connections. This tool searches for Bluetooth devices matching specified search terms and attempts to repair their connections by unpairing and re-pairing them.

**Dependencies:**
- `blueutil` (install with `brew install blueutil`)
- `jq` (install with `brew install jq`)

**Usage:**

Basic usage with configuration file:
```bash
magic-repair
```

Advanced usage with command-line options:
```bash
# Search for devices containing specific terms
magic-repair -s "Magic" -s "Jonas"

# Search for different device types
magic-repair -s "Dell" -s "Tom"
```

**Configuration:**

If no search terms are provided via command-line options, the script will look for a configuration file at `scripts/config/magic-repair.conf`.

Example configuration file content:
```bash
# Search for Apple Magic devices belonging to Jonas
search_terms="Magic Jonas"

# Or search for Dell devices belonging to Tom
# search_terms="Dell Tom"
```

**Options:**
- `-s TERM` - Add search term for device names (can be used multiple times)
- `-h, --help` - Show help message
- `-v, --version` - Show version information

The script will search for devices that contain ALL of the specified search terms in their names.

## Notes

- The installation modifies your shell profile to add the scripts directory to PATH
- Scripts remain in the repository directory and are not copied elsewhere
- Updates to the repository immediately affect your installed tools
- If you move or delete the repository directory, remove it from PATH using `./uninstall.sh` first
