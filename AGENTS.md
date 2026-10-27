# Working in shell-tools

Small macOS terminal tools, developed with AI. Keep implementation and process
proportional to the problem: polished UX, simple code, focused verification.
Product text, code comments and documentation are English.

## Start here

- Read `README.md` for supported behavior and installation.
- `scripts/magic-repair`: Bash engine, selection, recovery, state and diagnostics.
- `scripts/lib/magic-repair/ui.py`: Rich presentation; JSON events from the engine.
- `scripts/lib/magic-repair/permissions.py`: read-only Bluetooth authorization.
- `scripts/lib/magic-repair/setup-ui` and `requirements.txt` beside it: isolated runtime.
- `install.sh` / `uninstall.sh`: dependencies and shell-profile PATH entries.
- `scripts/mirror-repair`: separate privileged plist patcher; do not run for checks.
- `tests/`: unittest behavior tests with fake Bluetooth and temporary state.
- `docs/magic-repair-review.md`: research and historical decisions. Read the
  relevant section for Bluetooth changes; later sections supersede earlier ones.

## Setup and verification

On macOS, install development prerequisites with
`brew install python jq shellcheck bash`, then run `make setup-dev`.
This creates `.venv`; it does not install commands or edit shell profiles.

- `make check`: shell syntax, ShellCheck, Python syntax, fake-device tests and UI demo smoke check.
- `make lint`: fast syntax/static checks only.
- `make test`: behavior suite (about two minutes); defaults to macOS `/bin/bash` 3.2.
- `make test TEST_BASH="$(brew --prefix)/bin/bash"`: current Bash coverage.
- `make demo`: static UI preview without Bluetooth, also useful in headless sessions.
- Focused test: `.venv/bin/python -m unittest discover -s tests -p test_permissions.py -v`.

Use the same Make targets as CI. Do not edit scripts while their tests run.
Run checks relevant to the change; a documentation-only change needs link/command
review and `git diff --check`, not repeated full behavior suites. Add a regression
test for meaningful behavioral fixes; avoid snapshots of every UI detail or tests
that merely restate implementation. Report what ran and any unverified limitation.

## Compatibility and product constraints

- Shell code supports macOS Bash 3.2: no associative arrays, `mapfile`, or `${var,,}`.
  Python supports 3.10+. Quote paths; preserve spaces, apostrophes and dollar signs.
- Magic Repair moves accessories between Macs with different Apple Accounts.
  Both Macs may be awake. No remote disconnect, companion app, daemon or shared account.
- Default selection is names containing both literal terms `Magic` and `Jonas`.
  Remember selected addresses before unpairing; discover unknown devices only with `--scan`.
- Recovery follows observed paired/connected state. Keep elapsed deadlines and
  bounded calls; unpair at most once per device. Pair sequentially because of PIN input.
- The engine owns stdin. The renderer never reads it, pauses for Bluetooth responses,
  respects `NO_COLOR`, and degrades automatically for redirected/dumb terminals.
  Keep one default presentation; do not add appearance-mode choices.
- Config is data, never sourced. `--list` and `--dry-run` must not change pairings
  or remembered targets (explicit diagnostics may write logs; `--scan` may inquire).
- Keep runtime dependencies in `scripts/lib/magic-repair/requirements.txt`.
  Refresh relevant dependencies during maintenance and verify compatibility.
  Repair operations must never invoke package managers or need network access.

## Machine effects and privacy

Normal verification uses fakes and `--demo`; never run a real repair, `--force`,
`mirror-repair`, or reset Bluetooth/TCC merely to validate code. Live hardware
tests belong to an explicitly requested test session. The installed commands run
directly from this checkout, so edits can immediately affect the user's tools.

Bluetooth authorization belongs to the responsible terminal/host app. Only read
`CBManager.authorization()`; do not create a Bluetooth manager to request consent:
hosts missing `NSBluetoothAlwaysUsageDescription` can abort instead of prompting.
Open privacy settings with actionable guidance when access is missing. Do not
modify/re-sign terminal apps or claim reinstalling grants permission.

Keep device addresses/names, pairing input, diagnostics and personal config out of
Git. Diagnostics are opt-in and private; do not capture PINs, stdin or unrelated
devices. Keep atomic state saves, locking, and signal/child-process cleanup intact.
Installation tests must use temporary HOME/XDG/profile paths and mocked package
managers, never the user's actual profile.

## Code Review Rules

Flag unintended machine effects, lost recovery state, unbounded waits, process
leaks and private data entering logs or Git. Prefer findings with a concrete
trigger and consequence; leave formatting and syntax checks to CI.

## Completing a change

Review the diff before finishing. Keep engine/UI version constants aligned when releasing
Magic Repair changes; documentation/tooling-only changes need no product bump.
Update README for user-visible behavior. Add durable lessons here only when they
prevent a concrete recurring mistake; do not accumulate session logs or duplicate
architecture documents. Fix stale guidance in the same change. Do not introduce
frameworks, agent orchestration or persistent planning files for routine tasks.
