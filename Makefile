PYTHON ?= .venv/bin/python
TEST_BASH ?= /bin/bash
SHELL_FILES := install.sh uninstall.sh scripts/magic-repair scripts/mirror-repair scripts/lib/magic-repair/setup-ui

.PHONY: help setup-dev check lint test demo
.DEFAULT_GOAL := help

help:
	@printf '%s\n' 'make setup-dev  Create/update isolated development dependencies' 'make check      Run all hardware-free checks' 'make lint       Check shell and Python syntax and ShellCheck' 'make test       Run fake-device behavior tests' 'make demo       Render a static UI preview without Bluetooth'

setup-dev:
	python3 -m venv .venv
	.venv/bin/python -m pip install --upgrade pip -r scripts/lib/magic-repair/requirements.txt

check: lint test demo
	git diff --check

lint:
	@for file in $(SHELL_FILES); do /bin/bash -n "$$file" || exit; done
	shellcheck $(SHELL_FILES)
	$(PYTHON) -c 'import ast, pathlib; [ast.parse(p.read_text(), filename=str(p)) for root in ("scripts", "tests") for p in pathlib.Path(root).rglob("*.py")]'

test:
	TEST_BASH="$(TEST_BASH)" $(PYTHON) -m unittest discover -s tests -v

demo:
	TERM=dumb NO_COLOR=1 $(PYTHON) scripts/lib/magic-repair/ui.py --engine scripts/magic-repair -- --demo
