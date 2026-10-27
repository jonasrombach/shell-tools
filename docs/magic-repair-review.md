# magic-repair: review and research

Reviewed 2026-10-25. Goal: use the same Apple Magic Keyboard and Magic Trackpad
with a personal and a work Mac, with different Apple Accounts. The user briefly
power-cycles the accessories, then runs the command on the desired Mac.
Installing additional applications on the work Mac is not an option. Sometimes
both Macs are awake and nearby. The implementation therefore retains the existing
Bash + blueutil + jq toolchain and requires no remote service.

## Findings in version 1

| Severity | Finding | Consequence and fix |
| --- | --- | --- |
| High | Initial argument handling rejected any first option except help/version, including documented `-s`. | One argument parser now handles all options and missing values. |
| High | User terms were interpolated into jq source and regular expressions. | Quotes could break selection; regex symbols changed which devices were unpaired. Terms now enter jq as data and match literal substrings. |
| High | All targets were unpaired at once; discovery only used the current paired list. | A failed run could leave every device unavailable and make subsequent runs unable to find them. Save target addresses before changes and repair sequentially. |
| High | Unpair errors were ignored; the final message always claimed success. | Check each step, verify unpair and connection state, report per-device outcomes and return nonzero for any failure. |
| High | Pairing and other blueutil calls had no time limit. | A run could hang indefinitely. Bound each child process, kill/reap it on timeout or interruption. |
| Medium | Discovery ran in process substitution, hiding pipeline errors. | Permission/API failures looked like absent devices. Explicitly check commands and JSON schema. |
| Medium | Device names used `|` as a delimiter. | Names containing that delimiter were misread. Keep selection in JSON and quote names for terminal display. |
| Medium | Global Bluetooth restart could interrupt unrelated peripherals and had unchecked errors. | Repair only selected devices; retain diagnostics and a cable fallback. |
| Medium | No preview, persistent recovery, concurrency protection or automated tests. | Add read-only modes, atomic address storage, a per-user lock and behavior tests. |

## What the primary sources support

- [Apple: setup Magic accessories](https://support.apple.com/en-us/119917):
  rechargeable Magic accessories pair automatically through a USB-C/Lightning
  connection. This is a supported alternative to a Bluetooth pairing script.
- [Apple: connection troubleshooting](https://support.apple.com/en-us/102498):
  power-cycle the accessory; cable pairing can be retried by connecting to the
  desired Mac for one minute and then unplugging. This is the documented fallback
  rather than silently restarting the whole Mac Bluetooth controller.
- [blueutil documentation](https://github.com/toy/blueutil):
  uses private IOBluetooth APIs; `--unpair` and connection waiting are experimental.
  `--pair` has no timeout argument. Exit code 134 may indicate missing Bluetooth
  permission. The implementation checks both `.paired` and `.connected` using
  a single `--info --format json` observation.
- [blueutil source](https://github.com/toy/blueutil/blob/main/blueutil.m):
  JSON includes address/name/paired/connected. `--unpair` can return success after
  calling an undeclared removal method without checking the final pairing state.
  The new script therefore checks `.paired` afterwards.
- [blueutil issue 46](https://github.com/toy/blueutil/issues/46):
  direct reports about switching a keyboard between Macs show that disconnecting
  and connecting alone is not consistently sufficient. Coordinated unpair/pair
  worked in the reported setup. This is evidence of a useful workflow, not a
  guarantee for every macOS/accessory generation.
- [blueutil issue 93](https://github.com/toy/blueutil/issues/93):
  the same two-Mac scenario includes reports of a hanging pair operation, which
  motivates an external process timeout and recoverable target storage.
- [blueutil issue 90](https://github.com/toy/blueutil/issues/90):
  reported differences between framework device lists and Bluetooth settings,
  including failures of pairing/removal on some macOS releases. Treat command
  success and hardware compatibility as separate questions.

The installed blueutil used for a read-only preview is 2.13.0. Its command help
and the current upstream source were checked. Subsequent dependency maintenance
updated blueutil to 2.14.0, jq to Homebrew 1.8.2 and Homebrew Bash to 5.3.20. The
2.14.0 release fixes disconnect hanging on an unknown device; the command
interface remains compatible. The developer performed only read-only hardware
queries; actual pairing tests were initiated by the user.

## Alternatives for this setup

| Approach | Fit | Decision |
| --- | --- | --- |
| Power-cycle + local `magic-repair` | Same workflow, existing dependencies; no shared account or remote access. | Implemented. Re-pair stale local records; skip already connected devices unless `--force`. |
| Connection refresh without unpairing | Useful for a temporarily stuck connection; may not repair keys replaced by pairing to the other Mac. | Available as `--reconnect`; not assumed sufficient for switching. |
| USB-C/Lightning cable | Apple-supported automatic pairing; Keyboard and Trackpad can also be used while cabled. | Best supported fallback if Bluetooth switching fails. |
| Universal Control | Requires the same Apple Account with 2FA, as well as awake nearby supported devices and enabled Wi-Fi/Bluetooth/Handoff. | Excluded: the user's accounts differ. [Apple requirements](https://support.apple.com/en-us/102459). |
| Coordinated helper on both Macs | Can ask the source Mac to release accessories before taking them; avoids relying only on local availability. | Excluded: additional apps are not permitted on the work Mac. [MagicSwitch](https://github.com/Fouadktb/MagicSwitch) demonstrates this approach but is an early release, not hardware-tested here. |
| USB switch with both accessories cabled | Inference: routing their USB data connections to one Mac could avoid repeated wireless switching. | Possible hardware alternative, not validated here; Touch ID and particular switch/accessory combinations need their own checks. No purchase recommendation. |

No reviewed source establishes a reliable way for one Mac alone to take a Magic
accessory from an actively connected second Mac without the accessory becoming
available. The local script cannot guarantee that the second Mac will not win a
reconnection race after power-cycling. It reports this limit instead of requiring
manual work on the other Mac as part of the normal workflow.

## Recovery policy: technical and UX research

The user's confirmed preferences are name selection by **both Magic and Jonas**,
English output, no additional applications, and a better recovery strategy than
repeating the same operation three times with a 30-second timeout.

### Why recovery follows state

[Apple's `openConnection()` documentation](https://developer.apple.com/documentation/iobluetooth/iobluetoothdevice/openconnection%28%29)
explains that this call is synchronous, creates a baseband connection, and can
return an error when a connection already exists. The checked
[blueutil v2.13.0 source](https://github.com/toy/blueutil/blob/v2.13.0/blueutil.m)
uses this call directly for `--connect`. Therefore an additional long
`--wait-connect` after every successful connect is unnecessary for the common
path; a short state-confirmation window handles observed completion instead.
A command's exit status alone is insufficient evidence for repeating it.

[Apple's pairing API](https://developer.apple.com/documentation/iobluetooth/iobluetoothdevicepair)
also documents that a single pairing object can already make two low-level
pairing attempts and reports progress asynchronously. A wrapper should not
multiply full unpair/pair/connect sequences independently at several layers.
Its `stop()` removes the delegate and attempts a disconnect. Killing blueutil
is **not** equivalent to calling that method: an OS-side operation may complete
late. State observations and cooldowns reduce duplicate work, but cannot prove
that every daemon-side operation has stopped.

[AWS's retry guidance](https://aws.amazon.com/builders-library/timeouts-retries-and-backoff-with-jitter/)
distinguishes transient failures, timeout ambiguity and operations with side
effects; it recommends bounded retries at one layer. Applied here as an
engineering inference: remove stale pairing once, then retry only the missing
step, after observing the result of the previous operation. The script does not
parse human-readable HCI error strings to invent precise failure categories:
blueutil groups device failures under exit 1. Known usage/API/system exit codes
are handled separately; unknown device failures remain ambiguous and bounded.

### Concrete policy

| Situation | Action | Why |
| --- | --- | --- |
| Already paired and connected | Skip, unless `--force`. | Avoid needless loss of an available input device. |
| Stale local pairing in default repair mode | Remove once; observe `.paired == false` for up to 3s. | Account for delayed state change without repeatedly removing keys. |
| Unpair reports failure, but pairing is gone | Continue with pairing. | Postcondition matters more than a generic command failure. |
| Local pairing removal cannot be confirmed | Stop this device; continue others. | Repeating a destructive operation blindly is not recovery. |
| Not paired | Pair for up to 12s, then observe pairing for up to 2s. | Give the async exchange time while bounding a hung CLI. |
| Pair fails/times out but `.paired` is true | Continue to connection, or finish if also connected. | Preserve successful side effects and avoid duplicate pairing. |
| Paired but not connected | Connect for up to 8s, then observe both states for up to 2s. | Retain the new pairing instead of undoing it on connection failure. |
| Connect reports failure but both states are true | Count as successful. | Handles concurrent/late connection and already-connected errors. |
| Device remains unavailable | Schedule another state-aware round after a 2s/5s cooldown. | Allow state/availability to change; show a power-cycle hint. |
| Another device has not been tried | Give it a first attempt before retries. | One absent accessory should not monopolize recovery. |
| Invalid state JSON | Stop this device without more changes. | The next safe mutation cannot be determined. |
| Exit 64, 69, 70, 71, 134 or other unexpected process failure | Stop further repairs with the available diagnosis. | A retry against another address will not fix unsupported commands, API access or a system failure. Exit 69 can also mean unsupported unpair, so do not claim that the controller alone is at fault. |
| `--reconnect` without a pairing | Stop this device and explain default mode. | This explicit mode must never silently unpair or create a pairing. |

Each device has a 45s elapsed deadline starting at its first attempt. Every call,
confirmation window and cooldown is capped by the remaining budget. Work on
other devices counts against an already started deadline. At most three rounds
are allowed, not three attempts for every individual substep. No budget resets
on partial success. Calls that normally only inspect local state have a 3s
limit; initial discovery and local unpair/disconnect have a 5s limit. Process
cleanup can add small overhead. These values are implementation starting
points, **not measured device-specific percentiles or Bluetooth-standard
requirements**. `--timeout`, `--attempts` and `--pair-timeout` allow adjustment;
a longer pairing limit is particularly useful for human PIN confirmation.

Jitter is not added: one foreground invocation holds a local lock, targets are
processed sequentially, and there is no fleet of clients to spread out. Random
pauses would make this short interactive workflow harder to predict. The other
Mac's behavior cannot be coordinated under the user's constraints. A global
power reset is not used as a retry strategy. Inquiry is also not a normal
readiness gate: addresses are already known, a scan costs time, and absence from
a scan is not proof that an already known accessory cannot accept a connection.
Local state queries themselves are not proof that an accessory is discoverable.

### Terminal feedback (v3)

The normal terminal presentation uses Rich 15 in a small, isolated environment;
Bluetooth remains in the existing Bash engine. Device cards show observed
Release/Pair/Connect steps, retry state and results. Layout adapts to terminal
width/height; the final result stays in scrollback. Color is accompanied by
words/symbols, and redirected output remains append-only text automatically.
`--demo` runs a local screenplay without starting the engine or touching Bluetooth.

The design follows [CLI Guidelines](https://clig.dev/) on purposeful color,
readable output and non-TTY behavior, [GitHub CLI's accessibility work](https://github.blog/engineering/user-experience/building-a-more-accessible-github-cli/)
on status meaning beyond color, and [NN/g's waiting guidance](https://www.nngroup.com/articles/designing-for-waits-and-interruptions/)
on showing current steps rather than fabricated completion percentages.
[Rich Live](https://rich.readthedocs.io/en/latest/live.html) supplies terminal
redraw/cursor handling. The engine sends ephemeral JSON events; the renderer
never reads stdin. Bluetooth responses suspend redraws so PIN input remains
usable. Ctrl-C is forwarded to the engine for its existing cleanup.

Scope stays small: one rendering library, one renderer file, no menus, theme
system, extra service or separate TUI framework. Focused pseudo-terminal smoke
checks cover success, real prompt input and cancellation; the existing engine
checks remain authoritative for Bluetooth behavior. Rendered layouts are checked
at wide, normal and narrow terminal sizes. Direct WezTerm automation was denied
by the computer-use tool, so visual review uses generated renders and PTYs.

## Remembered targets, first-time discovery and concurrency

The two selection paths are combined: selected addresses/names are stored locally
before pairing changes, and `--scan` adds discoverable unpaired devices using the
same name filter. No unrelated discovered addresses/names are saved. A single
10s inquiry has a 20s outer deadline and runs before any pairing changes; normal
invocations use paired and remembered targets without scanning. Off devices
cannot be radio-discovered; remembered addresses can be used once they are on.
New matching devices are remembered even if the subsequent pairing fails.

[Apple's inquiry documentation](https://developer.apple.com/documentation/iobluetooth/iobluetoothdeviceinquiry/inquirylength)
warns that inquiry throttling and device-name updates can extend discovery beyond
the requested length. Accordingly this is one bounded inquiry, with no repeated
scan loop. [blueutil issue 110](https://github.com/toy/blueutil/issues/110) reports
BLE discovery limitations: the scan is not a guarantee that every Bluetooth-mode
accessory appears. A known address or initial cable pairing remains a fallback;
no unreviewed private-API patches or extra companion apps are installed.

The scan/setup mode allows up to 30s per pair operation for human confirmation,
still capped by the normal 45s device budget. Explicit `--pair-timeout` wins over
this default. Fast operations return immediately. The ordinary switch path
retains its 12s pairing cap.

Parallel pairing was considered. Each blueutil process shares terminal input;
simultaneous confirmation/PIN prompts can interleave and consume the wrong input.
Also, [Apple's inquiry guidance](https://developer.apple.com/documentation/iobluetooth/iobluetoothdeviceinquiry)
warns against certain name requests during inquiry. The implementation therefore
keeps scan and pairing separate and serializes device mutations. This is a
simplicity/interaction decision, not a claim that macOS universally forbids
concurrent pairing. First attempts are interleaved across targets before any
retries, preserving progress on other devices without adding worker-process and
prompt coordination. The next Keyboard hardware test can assess total latency.

## Validation and remaining hardware check

Finishing review: the lock now covers discovery and state reads as well as
repairs, avoiding competing state snapshots. Remembered names are refreshed when
devices are renamed. Configuration also supports fixed `device` addresses, with
strict address validation and errors for mixed selectors or unclosed quotes.
Discovery error test cases are isolated so each malformed response is actually
exercised rather than hidden behind an earlier simulated command failure.

The Python standard-library test suite substitutes a stateful blueutil executable
and invokes `/bin/bash` 3.2. It checks normal switching, literal selectors,
read-only preview, config parsing, connected-device skipping, forced renewal,
reconnect mode, exact unpaired addresses, retained targets after failure,
discovery errors, invalid state, disabled Bluetooth, failed/ineffective unpair,
unconfirmed connections, partial success, bounded timeouts, retries, concurrent
runs and signal cleanup. Recovery tests also cover delayed state updates,
partial success after failed/timed-out commands, round-robin first attempts,
preservation of new pairing, global failure handling, total budgets, progress
feedback and terminal/color behavior. ShellCheck and Bash syntax checks
supplement these tests.

The real-device preview found the configured Magic Trackpad without changing
Bluetooth or remembered targets. In a subsequent user-run live test, the user
started `magic-repair --diagnose` and immediately switched on the previously
powered-off Trackpad. The log recorded local pairing removal, an initial pair
failure with HCI 0x02, a successful second pair and a successful connection.
Both paired/connected states were true after about 10.2 seconds. The late power-on
is consistent with initial unavailability; the log alone cannot establish the
radio-level cause. The user confirmed that the Trackpad had previously been paired to the other
Mac and that movement, clicks and gestures all worked afterwards. The Keyboard
and reverse direction still need hardware validation; whether the other Mac
was awake and in range during the Trackpad test has not been established.

That live run also exposed an internal timing bug: an info query with a displayed
1s limit was cancelled after about 0.12s, on the next integer `SECONDS` tick.
Version 2.0.1 uses a relative sleep timer for actual per-call timeout decisions;
integer counters remain for coarse progress and overall budgeting. Timer children
are stopped/reaped on completion and cancellation. A regression test aligns a
0.4s pairing operation across a clock-second boundary with a 1s limit: it fails
with the previous implementation and succeeds with the fix. Diagnostic numeric
timestamps preserve fractional precision; `elapsed_s` and `duration_s` are coarse
integer counters, so use event timestamps for precise measured durations.

## Keyboard live test

A user-run `--scan --diagnose` test on version 2.1.0, with blueutil 2.14.0,
Homebrew jq 1.8.2 and Bash 5.3.20, found the Keyboard and selected it together
with the remembered Trackpad. blueutil reported an existing local Keyboard
pairing, which was removed once. The first pair call returned HCI 0x02; the
second succeeded after about 2.7s and already left the Keyboard connected, so
no redundant connect call was made. The Trackpad was already connected and
was skipped without mutation. Both target addresses/names are now retained.

Total observed runtime was about 19.3s, including a 10.7s inquiry. Version 2.1.1
corrects the summary duration to include discovery and initialization; the old
summary counted only the roughly 8s repair portion. A behavior test with a
known discovery delay checks that the reported total includes this work.
The user subsequently confirmed that all Keyboard functions worked. Both
accessories have therefore passed the requested live functional test. Additional
Mac/device combinations or the reverse direction are not implied by this result.

## Fresh installation verification (2026-10-27)

The installer now checks macOS and installs missing blueutil, jq and Python
3.10+ through Homebrew before creating the isolated Rich environment. If
Homebrew is needed but unavailable, it exits with setup instructions before
editing a shell profile. README clone instructions use the actual repository
URL and cover installation on each Mac, initial discovery, Bluetooth permission,
local settings/state and updates.

A temporary checkout and fresh HOME/XDG directories verified actual UI dependency
installation, repeated installation without duplicate PATH entries, an installed
demo without Bluetooth state, zsh startup, macOS Bash login-shell startup and
uninstallation. The checkout path included spaces, an apostrophe and a literal
dollar sign. A separate package-manager double verified installation of only a
missing dependency and the missing-Homebrew failure path. These checks did not
modify live Bluetooth or the user's shell profile. All 57 engine behavior tests,
ShellCheck, Bash syntax checks and `pip check` passed. This isolates installation
from existing user state; it does not substitute for hardware testing on a
second physical Mac.
