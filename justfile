_banner_line := "------------------------------------------------------------"

# Native Windows is not supported for development (ADR 4). Shows 
_platform_guard := if os() == "windows" { error("\n" + RED + _banner_line + "\nRobbie is developed on Linux or WSL 2.\nRun just from a WSL or Linux shell.\n" + _banner_line + NORMAL + "\n") } else { "" }

# List the available recipes
default:
    @just --justfile {{ quote(justfile()) }} --list

#  This target gets the repo 100% ready for all development work (virtual environments etC)
#   - it will ask some questions like where AI models are typically downloaded to etc.
#   - it will copy .env.example to .env and set it up
setup:


# Basic unit test run
test:


# Full testing including model evals etc.
vet: test
    # Check container pattern stops cleanly when Docker sends SIGTERM.
    bash scripts/tests/check_lifecycle.sh "testing/service_proforma"



# remove temporary files
clean:


# install robbie to a pi, or update the installation on a pi
deploy:

# RAG data to help robbie perform tasks
#   - A wizard that asks questions and informs about licence of downloaded work.
fetch-data:



## --------------------------------------------------------------------------------------------------------------------
# utils

# Print a message inside a coloured banner. color: green, yellow, red or blue.
[private]
banner msg color="green":
    @printf '%s\n%s\n%s%s\n' "{{ if color == "red" { RED } else if color == "yellow" { YELLOW } else if color == "blue" { BLUE } else { GREEN } }}{{ _banner_line }}" {{ quote(msg) }} "{{ _banner_line }}" "{{ NORMAL }}"
