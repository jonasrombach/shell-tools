# Copilot Instructions for terminal-tools

## Repository Overview

This repository contains a collection of macOS terminal tools designed to automate common tasks and make daily terminal usage more efficient. Each tool solves a specific problem that would otherwise require manual, repetitive actions.

## Repository Structure

```
terminal-tools/
├── README.md                    # Brief project description
├── LICENSE                      # Apache 2.0 license
├── scripts/                     # All terminal tools/scripts
│   └── magic-repair            # Bluetooth device re-pairing tool
└── .github/
    └── copilot-instructions.md  # This file
```

## Purpose and Goals

The primary goal is to create terminal tools that:
- **Automate tedious manual processes** on macOS
- **Save time** for repetitive tasks
- **Provide clear user feedback** with colors and emojis
- **Handle errors gracefully** with helpful messages
- **Follow consistent patterns** across all tools

## Existing Tools

### magic-repair
**Problem**: Apple Magic devices (Keyboard, Trackpad, Mouse) don't support multidevice connection. When you pair a Magic device with Device A and then with Device B, it stops working on Device A. To fix this, users must manually disconnect all devices through Bluetooth settings, wait for them to appear for pairing, and reconnect them.

**Solution**: A bash script that automates this entire process with a single command: `magic-repair`

**Key Features**:
- Searches for paired Magic devices containing "Magic" and a user-configurable name (e.g., "Jonas") in the name
- Unpairs all matching devices in parallel for efficiency
- Re-pairs and connects devices sequentially with retry logic
- Provides clear visual feedback with colors and emojis
- Handles errors with helpful suggestions (restart Bluetooth, toggle devices)

## Coding Standards and Patterns

### Script Structure
All scripts should follow this pattern:

1. **Shebang and setup**:
   ```bash
   #!/usr/bin/env bash
   
   # Colors for output
   RED="\033[0;31m"
   GREEN="\033[1;32m"
   YELLOW="\033[1;33m"
   BLUE="\033[1;34m"
   MAGENTA="\033[1;35m"
   NC="\033[0m"  # No Color
   ```

2. **Dependency checks**:
   ```bash
   # Check if required tools are installed
   if ! command -v required_tool &> /dev/null; then
       echo -e "${RED}❌ Error:${NC} 'required_tool' not found."
       echo -e "${YELLOW}Install with:${NC} brew install required_tool"
       exit 1
   fi
   ```

3. **Function definitions**: Use descriptive function names with clear parameters

4. **Main logic**: Clear, well-commented implementation

5. **User feedback**: Consistent use of colors and emojis for status messages

### Visual Feedback Standards

- **🔍** Search/discovery operations
- **⌨️** Keyboard-related actions
- **🖱️** Mouse/trackpad-related actions
- **🔗** Connection/pairing operations
- **✅** Success messages (GREEN)
- **❌** Error messages (RED)
- **⚠️** Warning messages (YELLOW)
- **💡** Tips and suggestions (YELLOW)
- **🔄** Processing/restart operations (BLUE)
- **🎉** Completion messages (GREEN)

### Error Handling

- Always provide helpful error messages
- Include installation instructions for missing dependencies
- Offer alternatives when operations fail
- Use appropriate exit codes

### Naming Conventions

- **Scripts**: Use descriptive hyphenated names (e.g., `magic-repair`, `dock-reset`)
- **Functions**: Use underscores (e.g., `pair_with_retries`, `restart_bluetooth`)
- **Variables**: Use descriptive names with underscores

## Creating New Tools

When adding a new terminal tool:

1. **Identify the problem**: What manual process can be automated?
2. **Research dependencies**: What CLI tools are needed?
3. **Design the solution**: Plan the automation steps
4. **Choose a name**: Use a clear, descriptive hyphenated name
5. **Follow the patterns**: Use the established script structure
6. **Test thoroughly**: Ensure it works in various scenarios
7. **Add to scripts/**: Place the executable script in the scripts directory
8. **Update README**: Document the new tool (if significant)

### Good Tool Ideas

- **dock-reset**: Reset and restart the macOS Dock
- **cache-clear**: Clear various system caches (DNS, font, etc.)
- **permission-fix**: Fix common permission issues
- **network-diagnose**: Automated network troubleshooting
- **backup-settings**: Backup system preferences and dotfiles
- **dev-setup**: Set up development environment for different languages

## File Permissions

All scripts in the `scripts/` directory should be executable:
```bash
chmod +x scripts/script-name
```

## Dependencies

Current tools depend on:
- `blueutil` - Bluetooth management (installable via Homebrew)
- `jq` - JSON processing (installable via Homebrew)

When adding new dependencies:
- Prefer tools available via Homebrew
- Always check for availability and provide installation instructions
- Document dependencies in script comments

## Testing

Test all scripts on:
- Different macOS versions when possible
- Various hardware configurations
- Edge cases (no devices, missing dependencies, etc.)

## Contributing Guidelines

When creating or modifying tools:
- Keep scripts focused on a single task
- Make them idempotent when possible
- Provide clear feedback to users
- Handle edge cases gracefully
- Follow the established patterns and coding standards
- Test thoroughly before committing

## Examples for Copilot

When suggesting new terminal tools or modifications, reference the `magic-repair` script as a pattern for:
- User interaction and feedback
- Error handling and dependency checking
- Retry logic with exponential backoff
- Parallel vs sequential operations
- Color coding and emoji usage