
MAKEFILE_PATH := $(abspath $(lastword $(MAKEFILE_LIST)))
PROJECT_DIR := $(patsubst %/,%,$(dir $(MAKEFILE_PATH)))

PIPUSER ?= 1

ifeq ($(OS),Windows_NT)
	PYTHON ?= python.exe
	VENV_BIN_DIR = Scripts
	EXE_EXT = .exe

	VENV_INIT = activate.bat
	VENV_CMD = call
	PATH_SEP = /
else
	PYTHON ?= python3
	VENV_BIN_DIR = bin
	EXE_EXT =
	
	VENV_INIT = activate
	VENV_CMD = .
	PATH_SEP = /
endif

VENV_BIN_DIR := .venv$(PATH_SEP)$(VENV_BIN_DIR)
VENV_ACTIVATE = $(VENV_CMD) $(VENV_BIN_DIR)$(PATH_SEP)$(VENV_INIT)
VENV_ACTIVATE_CMD := $(VENV_ACTIVATE) && 

TOX_EXE = $(VENV_BIN_DIR)$(PATH_SEP)tox$(EXE_EXT)
PRECOMMIT_EXE = $(VENV_BIN_DIR)$(PATH_SEP)pre-commit$(EXE_EXT)

ifeq ($(PIPUSER),1)
TOX_CMD = $(VENV_ACTIVATE_CMD) $(PYTHON) -m tox
else
TOX_CMD = tox
endif

MNOPD = --no-print-directory

.DEFAULT_GOAL = help

## -- Global makefile rules ---------------------------------------------------
all: | $(VENV_BIN_DIR) ## Setup local environment with pre-commit and tox
	$(NOISE)env PATH="$(PROJECT_DIR)/.venv/$(VENV_BIN_DIR):$(PATH)" hash tox$(EXE_EXT) pre-commit$(EXE_EXT) > /dev/null 2>&1  || $(MAKE) $(MFLAGS) $(MNOPD) setup

pkgs: ## Generate pythong packages
	$(NOISE)$(PYTHON) setup.py sdist
	$(NOISE)$(PYTHON) setup.py bdist_wheel --universal

include help.mk

## -- Setup -------------------------------------------------------------------

setup: $(TOX_EXE) $(PRECOMMIT_EXE) ## Setup local environment with pre-commit and tox
	@$(call infomsg,"venv can be activate using $(VENV_ACTIVATE)")

$(TOX_EXE): | $(VENV_BIN_DIR)
	$(call actionmsg, installing $@ ...)
	$(NOISE)$(VENV_ACTIVATE_CMD) $(PYTHON) -m pip install $(basename $(@F))

$(PRECOMMIT_EXE): | $(VENV_BIN_DIR)
	$(call actionmsg, installing $@ ...)
	$(NOISE)$(VENV_ACTIVATE_CMD) $(PYTHON) -m pip install pre-commit

$(VENV_BIN_DIR):
	$(NOISE)$(PYTHON) -m venv .venv

## -- Tox ---------------------------------------------------------------------

tox: | $(TOX_EXE) ## Execute specific tox environment using e parameter (ex. make tox e=py311)
	$(NOISE)$(eval e ?= ALL)
	$(NOISE)$(TOX_CMD) -e $(e) $(TOX_ARG)

syntax: e=syntax ## Perform all formatting, styling and coding checks
syntax: tox

black: e=black ## Run black as code formatter
black: tox

isort: e=isort ## Run isort to review import order
isort: tox

mypy: e=mypy ## Run mypy as static typing checker
mypy: tox

flake8: e=flake8 ## Run flake8 as style guide checker
flake8: tox

pylint: e=pylint ## Run pylint as static code analyser
pylint: tox

cover: e=cover ## Generate coverate report
cover: tox

doc: e=doc ## Generate documentation
doc: tox

## -- Testing -----------------------------------------------------------------

test: e=unit,cli ## Run all tests
test: tox

test-unit: e=unit ## Run unit tests
test-unit: tox

test-cli: e=cli ## Run cli tests
test-cli: tox


