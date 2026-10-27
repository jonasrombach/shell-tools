# shell-tools
MacOS specific tools that make life easier.

## Installation

### Quick Install
```bash
# Clone the repository
git clone https://github.com/jonasrombach/shell-tools.git
cd shell-tools

# Install (sets up the terminal UI and adds scripts to PATH)
./install.sh

# Open a new terminal, then preview without touching Bluetooth:
magic-repair --demo
```

Run this on each Mac where you want to use the tool. macOS and internet access
are required for installation. If dependencies are missing, the installer uses
Homebrew to install `blueutil`, `jq` and Python 3.10+. Install
[Homebrew](https://brew.sh) first if needed; if those dependencies are already
available, Homebrew is not required. No `sudo`, companion app or background
service is added by this project. Managed Macs must permit these command-line
dependencies and terminal Bluetooth access.

On the second Mac, start with `magic-repair --scan --dry-run` to check the
matching devices, then power-cycle the accessories and run
`magic-repair --scan` to pair them. If discovery cannot find an accessory,
pair it once using a cable or macOS Bluetooth settings, then run `magic-repair`.
The first run checks Bluetooth authorization. If access is missing, an
interactive run opens the Bluetooth privacy settings. Enable or add the app
hosting the command, then quit and reopen that app before running again.
The bundled name filter
is **Magic + Jonas**; change it as described below if needed.

Each Mac keeps its own remembered devices, settings and diagnostics. They are
not part of this repository and do not need to be copied between Macs. Keep the
clone in a permanent location: the installed commands run directly from it.

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
It also installs Rich for Magic Repair in an isolated environment under
`~/.local/share/shell-tools/magic-repair-ui` (respecting `XDG_DATA_HOME`).
Python 3.10+ and macOS 10.15+ are required; system Python packages are not changed. PyObjC's
CoreBluetooth bridge is also installed there to read authorization safely. Installation
can be rerun to refresh the UI dependencies without duplicating the PATH entry.

### Updating
Since scripts remain in the repository, updating is simple:
```bash
cd shell-tools
git pull origin main
./install.sh  # Also refresh isolated UI dependencies and check prerequisites
```

### Uninstallation
```bash
./uninstall.sh        # Remove scripts directory from PATH
./uninstall.sh --help # Show help
```

The isolated UI environment and local settings/device history are retained.
Their locations are documented below so they can be removed separately if desired.

## Available Tools

### magic-repair
Switch a Magic Keyboard, Trackpad or Mouse back to this Mac after using it
with another Mac. Turn the devices off and on, then run `magic-repair` on the
Mac you want to use. No companion app, background service, shared Apple Account
or access to the other Mac is needed.

**Dependencies:**
- `blueutil` (install with `brew install blueutil`)
- `jq` (install with `brew install jq`)
- Python 3.10+, Rich 15+ and PyObjC CoreBluetooth (installed in an isolated environment)

**Usage:**
```bash
magic-repair
magic-repair --demo                     # Preview the design without Bluetooth access
magic-repair --dry-run                  # Preview the selected devices and plan
magic-repair --scan --diagnose          # Find and pair a previously unknown device
magic-repair --scan --list              # Discover matching devices without pairing
magic-repair --list                     # Show matching devices only
magic-repair -s Magic -s Jonas          # All terms must match (literal, case-insensitive)
magic-repair --device AA:BB:CC:DD:EE:FF # Target a known address, even if unpaired
magic-repair --reconnect                # Preserve pairing; only reconnect
magic-repair --force                    # Renew even an already connected device
```

By default, matching devices already connected to this Mac are skipped. For
each other target the tool removes its stale local pairing, pairs again,
connects and verifies both pairing and connection state. Every device gets a
first attempt before retries start, so an unavailable Trackpad does not consume
all its retries before the Keyboard is tried. Already completed steps are kept:
pairing is removed at most once per device, and a failed connection does not
discard a newly established pairing. After a command fails or times out, the
tool checks what actually happened before deciding what to do next.

Devices already selected on this Mac are remembered by their Bluetooth address,
so they remain targets even if they later disappear from the paired list.
To add a new Keyboard/Trackpad, run `magic-repair --scan --diagnose` and switch it
on when the scan starts. The single 10-second inquiry includes unpaired nearby
devices, with a 20-second limit including name lookup. The same **Magic + Jonas**
name filter applies to known and newly discovered devices. Only selected devices
are saved and paired; unrelated scan results are not remembered. Afterwards an
ordinary `magic-repair` uses the saved address without scanning again.
For this initial setup mode, pairing has a 30-second limit to allow human
confirmation/PIN entry; `--pair-timeout` can override it. The total per-device
budget still applies, and automatic pairing returns immediately when complete.

An off device cannot be discovered by radio. A known address allows direct
pair/connect attempts once the device becomes available. Inquiry support depends
on blueutil and the device's Bluetooth mode; some BLE-only devices do not appear.
If a new accessory is not found, pair it once by cable/Bluetooth settings or
specify its address with `--device`. Failed, timed-out or invalid scans stop
before any device pairing is changed. `--scan --list` and `--scan --dry-run`
perform discovery only; diagnostic logging remains optional.

Recovery has a **45-second elapsed budget per device**, starting with its first
attempt. Pauses and time spent on other devices count toward that deadline;
it is never reset. The total run can take longer than 45 seconds for multiple
devices, and process cleanup adds a small amount of overhead. Pairing calls
have a 12-second limit, connection calls 8 seconds, and local state queries
3 seconds. Local unpair/disconnect calls and initial discovery are limited to
5 seconds. All steps are also capped by the remaining device budget.

Up to three recovery rounds are allowed, with 2-second and then 5-second
cooldowns; time spent trying another device can satisfy that cooldown. Waiting
observes late completion and can finish immediately on success. Set
`--timeout 60 --attempts 2` to change the total device budget and round limit.
For a slow PIN/confirmation interaction, use
`--pair-timeout 30 --timeout 90`. These are adjustable starting values, not
hardware-calibrated Bluetooth timing guarantees.

Usage, Bluetooth-unavailable, internal/system and API-access errors stop further
repairs immediately. Generic device errors and timeouts get bounded, state-aware
recovery. A failed local unpair/disconnect that leaves the original state intact
stops work on that device rather than repeating the destructive operation.
`--reconnect` never pairs or unpairs: if there is no local pairing, use the
default mode. Pairing prompts and original Bluetooth errors stay visible.

The normal English terminal UI is a live dashboard: responsive device cards,
lavender/mint status accents, a Release → Pair → Connect rail, retry states and
a final per-device result. It stays in the normal terminal scrollback rather
than taking over the whole screen. `magic-repair --demo` previews the design
without accessing Bluetooth. There is no appearance-mode choice to configure.

Pairing prompts pause redraws and keep stdin attached to the terminal. Original
Bluetooth responses remain visible; the dashboard resumes when the step ends.
Time labels describe limits, never invented completion percentages. Colors
respect `NO_COLOR` and `--no-color`; redirected output and `TERM=dumb` get
append-only text automatically. Press **Ctrl-C** to cancel; the child process
and lock are cleaned up, while saved addresses stay available for the next run.
Stopping the CLI cannot guarantee that macOS's Bluetooth daemon has undone an
in-flight operation.

For a live test, run `magic-repair --diagnose`. This keeps the normal terminal
UI and saves timestamped JSONL events under
`~/.local/state/magic-repair/logs/run-…/events.jsonl` (respecting
`XDG_STATE_HOME`). `logs/latest.jsonl` points to the latest diagnostic run.
The log includes tool/OS versions, terminal type, selected names/addresses,
step limits, exit codes, extracted HCI error codes, observed pairing/connection
states and the final result. It does not record typed input, pairing PINs or
the complete list of unrelated paired devices. Original Bluetooth errors and
prompts remain visible in the terminal. Only their HCI error code is retained;
temporary stderr capture is deleted on exit. Log files are private to your user
(directory mode 700, file mode 600), stay local and are retained until you remove
them. Logging is opt-in. `--diagnose --dry-run` writes diagnostics while leaving
Bluetooth and remembered target addresses untouched.

The bundled configuration retains the existing `Magic` + `Jonas` filter.
Override it with `-s` / `--search` or repeat `--device` for exact addresses.
For personal configuration, create `~/.config/magic-repair/config`
(`$XDG_CONFIG_HOME/magic-repair/config` when set):

```bash
search_term="Magic"
search_term="Jonas"
```

Each `search_term` is one literal phrase; all must match. The legacy
`search_terms="Magic Jonas"` syntax still splits on whitespace. Configuration
is read as data, never executed. `--config FILE` selects another file;
otherwise the bundled `scripts/config/magic-repair.conf` is the fallback.

For a fixed device set, use repeated `device` entries instead of search terms:

```bash
device="AA:BB:CC:DD:EE:FF"
device="11:22:33:44:55:66"
```

Fixed addresses work even when a device is not currently paired with this Mac
or its name has changed. Use either device addresses or search terms in a config.
Both address formats with colons or hyphens, and 12 hexadecimal digits without
separators, are accepted. Name matching ignores ASCII letter case.

Before removing pairings, selected names and addresses are saved atomically to
`~/.local/state/magic-repair/devices.json` (or `$XDG_STATE_HOME/magic-repair/`).
This allows the next invocation to find a device even after failed pairing.
`--list` and `--dry-run` do not write target state or change pairings/connections.
With `--scan`, they can perform a read-only device inquiry. A lock prevents
concurrent repairs using the same state directory. A forced termination such as
`kill -9` can leave `repair.lock` there; remove that empty directory only after
checking that no repair is running.

**Limits:** The tool cannot make another Mac release a device or prevent it
from reconnecting first. Power-cycling is the normal switching step; manual
disconnection on the other Mac is not a prerequisite. If pairing still fails,
connect rechargeable Magic devices to this Mac by USB/Lightning for one minute,
then unplug them. macOS may require pairing confirmation or a PIN.
Bluetooth connection checks cannot prove that keys or gestures work.

**Bluetooth permissions:** The tool reads authorization before device discovery
or pairing. If permission is undecided, denied or restricted, interactive runs
open **System Settings → Privacy & Security → Bluetooth** and stop safely.
Noninteractive runs print instructions without opening settings. `--demo` and
`--help` do not check Bluetooth access.

Some terminal apps, including versions of WezTerm, lack the
`NSBluetoothAlwaysUsageDescription` required for a native consent request.
Creating a Bluetooth manager under that host can make macOS abort Python instead
of displaying a dialog. The tool therefore only reads authorization; it never
creates a Bluetooth manager to request permission. It does not modify or re-sign
your terminal app. A reliable "Allow" dialog cannot be guaranteed in this CLI's
execution context.

If access was denied, enable the app hosting the command (e.g. WezTerm, Terminal,
or the app containing an integrated terminal) in **System Settings → Privacy &
Security → Bluetooth**, then quit and reopen that app. If it is missing, use
the **+** button to add the app if your macOS version offers it. Consent belongs
to the responsible application, so allowing one terminal does not necessarily
allow another. The dashboard also links to the settings pane and stops further
Bluetooth work rather than retrying a denied request. Corporate restrictions
may require your administrator. The installer cannot grant permission itself;
it sets up dependencies without requesting Bluetooth access. Reinstalling is
not a remedy for missing authorization. An abort with
code 134 may indicate denied API access, but is not proof of its cause.

Exit status is `0` when all targets are connected, `1` for discovery or repair
failure (including partial success), and `2` for invalid arguments or config.
See [review, research and alternatives](docs/magic-repair-review.md) for the
design rationale and sources.

### mirror-repair
A tool to patch your Mac's iPhone Mirroring eligibility file for use with iPhone Mirroring.

**Usage:**
```bash
mirror-repair
```

- The script will scan and patch `/private/var/db/os_eligibility/eligibility.plist` for iPhone Mirroring support.
- You may be prompted for your password, as root permissions are required to update the file.

**Important:**
- Your Apple Account on your iPhone for "Media & Purchases" must be outside of the EU (e.g., Norway). You can set up a new Apple ID for this purpose. Only running the `mirror-repair` command is not enough if your account is still set to an EU country.
- You may need to grant Full Disk Access to your terminal app for the script to work.

## Notes

- The installation modifies your shell profile to add the scripts directory to PATH
- Scripts remain in the repository directory and are not copied elsewhere
- Updates to the repository immediately affect your installed tools
- If you move or delete the repository directory, remove it from PATH using `./uninstall.sh` first

## Development checks

Repository guidance for coding agents lives in [AGENTS.md](AGENTS.md).
It records the product constraints, architecture, verification commands and
Bluetooth pitfalls that need to survive between sessions. Update it when a
concrete lesson changes how future work should be done. Copilot's instruction
file points to the same guidance to avoid conflicting copies.

Development setup is separate from user installation: it creates a local,
ignored `.venv` without editing your shell profile or accessing Bluetooth.

```bash
brew install python jq shellcheck bash
make setup-dev
make check
```

`make check` runs syntax checks for all shell/Python files, ShellCheck, the
unittest behavior suite and a static Rich demo. Tests use a stateful fake
`blueutil`, mocked authorization and temporary state; they do not change real
Bluetooth connections. The demo does not start the engine. `mirror-repair` is
linted but never executed. No hardware, installed `blueutil` or Bluetooth
permission is needed for these checks.

For smaller iterations, use `make lint`, `make test` or `make demo`. To check
the engine with current Homebrew Bash instead of macOS Bash 3.2:

```bash
make test TEST_BASH="$(brew --prefix)/bin/bash"
```

GitHub Actions runs the same `make check` on macOS for pushes and pull requests,
and weekly to catch dependency drift. The two configurations cover Python 3.10
with system Bash and Python 3.14 with Homebrew Bash. CI validates simulated
behavior and rendering; terminal permission attribution and accessory handoff
still require an explicit live test on the target Mac.

Runtime requirements have one source:
[`requirements.txt`](scripts/lib/magic-repair/requirements.txt), shared by the
installer and development setup. Dependabot proposes weekly grouped updates for
those requirements and the SHA-pinned GitHub Actions. Updates are not automatically
merged. Requirements intentionally allow newer compatible releases; run
`make setup-dev` to refresh development dependencies and `./install.sh` to refresh
installed dependencies. Homebrew tools remain a manual maintenance step below.

This setup follows the official recommendations to keep agent instructions short
and repository-specific, and to provide executable verification commands:
[OpenAI agent guidance](https://learn.chatgpt.com/docs/agent-configuration/agents-md),
[OpenAI development practices](https://learn.chatgpt.com/guides/best-practices),
[GitHub instruction support](https://docs.github.com/en/copilot/reference/custom-instructions-support).
For this small project, one guide and one check entry point keep maintenance
manageable; per-agent frameworks and persistent session journals add little value.

Keep the installed runtime dependencies current via Homebrew:

```bash
brew update
brew upgrade blueutil jq python
# Refresh the isolated dashboard dependencies:
/bin/bash scripts/lib/magic-repair/setup-ui
```

As of 2026-10-25, validation used blueutil 2.14.0 and Homebrew jq 1.8.2.
Use `command -v jq` to check which jq your shell selects; the macOS-bundled copy
may be older. The tool supports macOS Bash 3.2 and is also checked with the
current Homebrew Bash. Updates are performed during maintenance, outside repair
runs, to keep switching free of package-manager prompts and network delays.
