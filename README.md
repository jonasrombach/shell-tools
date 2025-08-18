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

```bash
./install.sh          # Install by adding scripts directory to PATH
./install.sh --help   # Show help
```

The script will automatically detect your shell and add the scripts directory to your PATH.

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
A tool to repair Apple Magic device Bluetooth connections.

**Dependencies:**
- `blueutil` (install with `brew install blueutil`)
- `jq` (install with `brew install jq`)

**Usage:**
```bash
magic-repair
```

## Notes

- The installation modifies your shell profile to add the scripts directory to PATH
- Scripts remain in the repository directory and are not copied elsewhere
- Updates to the repository immediately affect your installed tools
- If you move or delete the repository directory, remove it from PATH using `./uninstall.sh` first
