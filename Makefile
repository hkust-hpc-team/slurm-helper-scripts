# Makefile for venv-based install of slurm-helper-scripts
# - Install/upgrade into a dedicated venv under $(PREFIX)/lib/slurm-helper-scripts/venv
# - Symlink entrypoints into $(PREFIX)/bin: squota, savail
# - Uninstall removes both the venv and the symlinks
#
# Usage:
#   make build                # build wheel into dist/
#   make install              # install/upgrade into venv and link bins
#   make uninstall            # remove venv and bin symlinks
#   make status               # show where things are installed
#
# Vars (override as needed):
#   PREFIX=/usr/local         # or /usr
#   PYTHON_BIN=/usr/bin/python3
#   WHEEL=dist/...whl         # default: latest matching wheel in dist/
#   SUDO=sudo                 # set to empty if already root (SUDO=)

SHELL := /usr/bin/env bash
.SHELLFLAGS := -euo pipefail -c

NAME        := slurm-helper-scripts
BINS        := squota savail
PREFIX      ?= /usr/local
PYTHON_BIN  ?= /usr/bin/python3
SUDO        ?= sudo
ifeq ($(shell id -u),0)
SUDO        :=
endif

LIBBASE     := $(PREFIX)/lib/$(NAME)
VENV        := $(LIBBASE)/venv
BINDIR      := $(PREFIX)/bin

# Pick the newest prebuilt wheel by default (py3-none-any)
WHEEL ?= $(shell ls -1t dist/slurm_helper_scripts-*-py3-none-any*.whl 2>/dev/null | head -n1)

.PHONY: help build install upgrade uninstall status wheel-path ensure-venv fix-perms

help:
	@echo "Targets:"
	@echo "  build     - Build wheel into dist/"
	@echo "  install   - Install/upgrade into venv and link $(BINS) into $(BINDIR)"
	@echo "  upgrade   - Alias of install"
	@echo "  uninstall - Remove venv and bin symlinks"
	@echo "  status    - Show current install paths and versions"
	@echo
	@echo "Vars: PREFIX=$(PREFIX)  PYTHON_BIN=$(PYTHON_BIN)  WHEEL=$(WHEEL)  SUDO=$(SUDO)"

build:
	@command -v uv >/dev/null || { echo "uv not found. Install uv or build the wheel another way."; exit 1; }
	uv build

wheel-path:
	@if [[ -z "$(WHEEL)" ]]; then \
	  echo "No wheel found in dist/. Run 'make build' or set WHEEL=..."; exit 1; \
	else \
	  echo "$(WHEEL)"; \
	fi

ensure-venv:
	@$(PYTHON_BIN) -c 'import venv' 2>/dev/null || { \
	  echo "Python venv module not available in $(PYTHON_BIN). On Debian/Ubuntu: apt install -y python3-venv" >&2; \
	  exit 1; }

install upgrade: ensure-venv wheel-path
	@echo "==> Installing $(NAME) into venv"
	@echo "    PREFIX      : $(PREFIX)"
	@echo "    PYTHON_BIN  : $(PYTHON_BIN)"
	@echo "    VENV        : $(VENV)"
	@echo "    BINDIR      : $(BINDIR)"
	@echo "    WHEEL       : $(WHEEL)"
	$(SUDO) install -d -m 0755 "$(LIBBASE)" "$(BINDIR)"
	@if [[ ! -x "$(VENV)/bin/python" ]]; then \
	  $(SUDO) "$(PYTHON_BIN)" -m venv "$(VENV)"; \
	else \
	  echo "    Reusing existing venv: $(VENV)"; \
	fi
	$(SUDO) "$(VENV)/bin/python" -m pip install --upgrade pip
	$(SUDO) "$(VENV)/bin/python" -m pip install --no-deps --no-compile --upgrade "$(WHEEL)"

	@echo "==> Fixing permissions (world-readable/executable for traversal)"
	$(SUDO) chmod -R a+rX "$(VENV)"

	@echo "==> Linking entrypoints into $(BINDIR)"
	@for b in $(BINS); do \
	  $(SUDO) ln -sfn "$(VENV)/bin/$$b" "$(BINDIR)/$$b"; \
	  echo "    -> $(BINDIR)/$$b -> $(VENV)/bin/$$b"; \
	done
	@echo "==> Done. Try: $(BINDIR)/squota --help ; $(BINDIR)/savail --help"

uninstall:
	@echo "==> Removing symlinks from $(BINDIR)"
	@for b in $(BINS); do \
	  if [[ -L "$(BINDIR)/$$b" || -f "$(BINDIR)/$$b" ]]; then \
	    $(SUDO) rm -f "$(BINDIR)/$$b"; \
	    echo "    removed $(BINDIR)/$$b"; \
	  fi; \
	done
	@echo "==> Removing venv and library dir: $(LIBBASE)"
	$(SUDO) rm -rf "$(LIBBASE)"
	@echo "==> Uninstall complete."

status:
	@echo "PREFIX     : $(PREFIX)"
	@echo "PYTHON_BIN : $(PYTHON_BIN)"
	@echo "LIBBASE    : $(LIBBASE)"
	@echo "VENV       : $(VENV)"
	@echo "BINDIR     : $(BINDIR)"
	@echo "WHEEL      : $(WHEEL)"
	@echo "--- python versions ---"
	@($(PYTHON_BIN) -V || true)
	@([[ -x "$(VENV)/bin/python" ]] && $(VENV)/bin/python -V || echo "venv python: (missing)")
	@echo "--- entrypoints ---"
	@for b in $(BINS); do \
	  if [[ -x "$(BINDIR)/$$b" || -L "$(BINDIR)/$$b" ]]; then \
	    echo "$$b -> $$(readlink -f "$(BINDIR)/$$b" 2>/dev/null || echo "$(BINDIR)/$$b")"; \
	  else \
	    echo "$$b (not installed)"; \
	  fi; \
	done

# Optional target if you ever need to re-fix permissions post-install
fix-perms:
	$(SUDO) chmod -R a+rX "$(VENV)"