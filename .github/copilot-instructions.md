# Copilot Instructions for shell-tools

## Repository Overview

This repository contains a collection of macOS terminal tools designed to automate common tasks and make daily terminal usage more efficient. Each tool solves a specific problem that would otherwise require manual, repetitive actions.

## Repository Structure

```
shell-tools/
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

## Example Tool

### magic-repair (Example Implementation)
**Problem**: Switching the same Apple Magic accessories between a personal and a work Mac can leave stale local Bluetooth pairings. The intended workflow is to power-cycle the accessories and run `magic-repair` on the desired Mac, without manually disconnecting on the other Mac or installing a companion app.

**Solution**: A bash script that automates this entire process with a single command: `magic-repair`

**Key Features**:
- Selects names containing all literal search terms (default: "Magic" and "Jonas")
- Remembers selected addresses before changes, allowing recovery after failed pairing
- Includes unpaired discoverable devices with the explicit `--scan` option
- Removes stale local pairing at most once per device, then recovers from observed pairing/connection state
- Gives every target a first attempt before retries, within bounded per-device and per-call time limits
- Processes pairing operations sequentially to keep confirmation/PIN input unambiguous
- Supports read-only preview/list modes and private opt-in JSONL diagnostics without PINs or typed input
- Uses a Rich dashboard by default in terminals, with automatic text output for redirected streams
- Keeps presentation in `scripts/lib/magic-repair/ui.py`; the Bash engine emits small JSON events
- Leaves stdin with the engine and pauses redraws for pairing prompts; respects `NO_COLOR`
- Does not reset the global Bluetooth controller or require remote access to the other Mac

## Coding Standards and Patterns

### Script Structure
All scripts should follow this pattern:

1. **Shebang and setup**:
   ```bash
   #!/usr/bin/env bash
   
   # Constants needed for the script
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

When adding new dependencies:
- Prefer tools available via Homebrew
- Always check for availability and provide installation instructions
- Document dependencies in script comments
- Keep task-relevant Homebrew dependencies current during maintenance; verify versions and compatibility after updates
- Do not run package updates inside Bluetooth repair operations

## Testing

For magic-repair, run the standard-library Python behavior suite, Bash syntax checks and ShellCheck documented in README.md. Tests substitute blueutil and never mutate real Bluetooth. Exercise macOS Bash 3.2 and the current Homebrew Bash when changing process handling. Live hardware tests belong to the user's requested test session.

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
