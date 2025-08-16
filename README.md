# terminal-tools
Tools that make life easier.

## Installation

### Quick Install
```bash
# Clone the repository
git clone https://github.com/jonasrombach/terminal-tools.git
cd terminal-tools

# Install to ~/.local/bin (recommended)
./install.sh --user

# Or install system-wide (requires sudo)
./install.sh --system
```

### Installation Options

#### Interactive Installation
```bash
./install.sh
```
The script will prompt you to choose an installation location.

#### Command Line Options
```bash
./install.sh --user      # Install to ~/.local/bin (user-specific)
./install.sh --system    # Install to /usr/local/bin (system-wide, requires sudo)
./install.sh --dir /path # Install to custom directory
./install.sh --help      # Show help
```

### Updating
Since the installation uses symlinks, updating is simple:
```bash
cd terminal-tools
git pull origin main
# Scripts are automatically updated via symlinks
```

### Uninstallation
```bash
./uninstall.sh --user    # Remove from ~/.local/bin
./uninstall.sh --system  # Remove from /usr/local/bin (requires sudo)
./uninstall.sh --all     # Remove from all common locations
./uninstall.sh --help    # Show help
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

- After installation, make sure your installation directory is in your PATH
- The installation uses symlinks, so updates to the repository automatically update the installed scripts
- If you move or delete the repository directory, you'll need to reinstall the scripts
