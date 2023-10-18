MAKEFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
PROJECT_PATH := $(patsubst %/,%,$(dir $(MAKEFILE_PATH)))

PIPUSER ?= 1

ifeq ($(OS),Windows_NT)
	PYTHON ?= python.exe
	VENV_BIN_DIR = Scripts
	EXE_EXT = .exe

	VENV_INIT = activate
	VENV_CMD = .
	PATH_SEP = /
else
	EXE_EXT =
	PYTHON ?= python3
	VENV_BIN_DIR = bin
	VENV_CMD = .
	VENV_INIT = activate
	PATH_SEP = /
endif

VENV_BIN_DIR := .venv$(PATH_SEP)$(VENV_BIN_DIR)
VENV_ACTIVATE = $(VENV_CMD) $(VENV_BIN_DIR)$(PATH_SEP)$(VENV_INIT)

MNOPD = --no-print-directory

.DEFAULT_GOAL = help

## -- Global makefile rules ---------------------------------------------------
all: | .venv ## Setup local environment with tox
	$(NOISE) hash $(*) > /dev/null 2>&1  || $(MAKE) $(MFLAGS) $(MNOPD) setup

pkgs: ## Generate pythong packages
	$(NOISE)$(PYTHON) setup.py sdist
	$(NOISE)$(PYTHON) setup.py bdist_wheel --universal

include help.mk

## -- Setup -------------------------------------------------------------------

setup: $(VENV_BIN_DIR)$(PATH_SEP)tox$(EXE_EXT) $(VENV_BIN_DIR)$(PATH_SEP)pre-commit$(EXE_EXT) ## Setup local environment with tox
	@$(call infomsg,"You need to manually activate your venv: $(VENV_ACTIVATE)")

setup-venv: $(VENV_BIN_DIR) ## Create local virtual environment inv .venv directory
	$(NOISE)set -a && $(VENV_ACTIVATE) && $(MAKE) $(MFLAGS) $(MNOPD) setup


$(VENV_BIN_DIR)$(PATH_SEP)tox$(EXE_EXT) $(VENV_BIN_DIR)$(PATH_SEP)pre-commit$(EXE_EXT):
	$(call actionmsg, installing $@ ...)
ifneq ($(PIPUSER),1)
ifneq ($(FORCE), 1)
ifeq ($(VIRTUAL_ENV),)
	$(call errormsg,"tox cannot be installed without a virtual environment (make setup-venv && $(VENV_ACTIVATE))")
endif
endif
	$(NOISE)$(PYTHON) -m pip install $(basename $(@F))
else
ifneq ($(VIRTUAL_ENV),)
	$(NOISE)$(PYTHON) -m pip install $(basename $(@F))
else
	$(NOISE)$(PYTHON) -m pip install --user $(basename $(@F))

endif
endif
$(VENV_BIN_DIR):
	$(NOISE)$(PYTHON) -m venv .venv

## -- Syntax checkers ---------------------------------------------------------

syntax: ## Perform all formatting, styling and coding checks
	$(NOISE)tox -e syntax

black: ## Run black as code formatter
	$(NOISE)tox -e black

isort: ## Run isort to review import order
	$(NOISE)tox -e isort

mypy: ## Run mypy as static typing checker
	$(NOISE)tox -e mypy

flake8: ## Run flake8 as style guide checker
	$(NOISE)tox -e flake8

pylint: ## Run pylint as static code analyser
	$(NOISE)tox -e pylint

cov: ## Generate coverate report
	coverage erase
	./test --coverage
	coverage combine
	coverage html

## -- Testing -----------------------------------------------------------------

test: test-unit test-cli ## Run all tests

test-unit: ## Run unit tests
	$(NOISE)tox -e unit

test-cli: ## Run cli tests
	$(NOISE)tox -e cli


