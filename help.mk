#
# Help & noise
#
# Version 1.0

## Colors
COLOR_RESET    = \033[0m
COLOR_ERROR    = \033[31m
COLOR_INFO     = \033[32m
COLOR_COMMENT  = \033[33m
COLOR_ACTION   = \033[94m

# Keep it silent by default
ifeq ($(VERBOSE),1)
	NOISE=
else
	NOISE=@
endif

# Print a comment
# commentmsg MESSAGE
define commentmsg
    printf "$(COLOR_COMMENT)%s$(COLOR_RESET)\n" $(1)
endef
define show
	@printf "\n$(COLOR_COMMENT)%s$(COLOR_RESET)\n" $(1)
endef

# Print an informative message
# infomsg MESSAGE
define infomsg
    printf "$(COLOR_INFO)%s$(COLOR_RESET)\n" $(1)
endef
define inform
	@printf "==> $(COLOR_INFO)%s$(COLOR_RESET)\n" $(1)
endef

# Print a native message (without color)
# msg MESSAGE
define msg
    printf "%s\n" $(1)
endef

# Print an error message
# errormsg MESSAGE
define errormsg
    printf "$(COLOR_ERROR)ERROR: %s$(COLOR_RESET)\n" $(1) && exit 1
endef

# Print an action message
# actionmsg MESSAGE
define actionmsg
    @if [ -z "$(ECHOCMD)" ]; then \
        printf "$(COLOR_ACTION)%s$(COLOR_RESET)\n" "$(1)";	\
    fi
endef

## -- Help --------------------------------------------------------------------

help: ## Outputs this help screen
	@$(call commentmsg,"Usage:")
	@$(call msg,"  make [target]")
	@$(call msg,"")
	@$(call commentmsg,"Commandes disponibles:")
	@grep -E '(^[a-zA-Z%0-9_-]+:.*?##.*$$)|(^## -- )' $(MAKEFILE_LIST) | grep -v "## Command" | cut -d: -f2- | \
		awk 'BEGIN {FS = ":.*?## "}{printf "$(COLOR_INFO)%-20s$(COLOR_RESET) %s\n", $$1, $$2}' | \
		sed -e 's/\[32m## /\n[33m/'
