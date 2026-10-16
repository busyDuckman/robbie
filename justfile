_banner_line := "------------------------------------------------------------"

# Native Windows is not supported for development (ADR 4). Shows 
_platform_guard := if os() == "windows" { error("\n" + RED + _banner_line + "\nRobbie is developed on Linux or WSL 2.\nRun just from a WSL or Linux shell.\n" + _banner_line + NORMAL + "\n") } else { "" }

# List the available recipes
default:
    @just --justfile {{ quote(justfile()) }} --list


## --------------------------------------------------------------------------------------------------------------------
# Dev helpers

#  This target gets the repo 100% ready for all development work (virtual environments etC)
#   - it will ask some questions like where AI models are typically downloaded to etc.
#   - it will copy .env.example to .env and set it up
#   - just setup --redo  offers to set up the AI model again
setup *flags:
    @python3 scripts/setup/setup_models.py {{ flags }}
    @for f in config/*/.env.example; do [ -e "${f%.example}" ] || cp "$f" "${f%.example}"; done

# Basic unit test run
test:
    # robbie-lib, Python and the Rust port, against the shared cases in common/robbie-lib-test.
    cd common/robbie-lib-py && uv run pytest -q
    cargo test -q --manifest-path common/robbie-lib-rs/Cargo.toml


# Full testing including model evals etc.
vet: test
    # Robbie's RELM table must load (relm exits non-zero on a bad table).
    uv run -q --project common/robbie-lib-py relm --table config/relm_table.yaml < /dev/null > /dev/null
    cargo run -q --manifest-path common/robbie-lib-rs/Cargo.toml --bin relm -- --table config/relm_table.yaml < /dev/null > /dev/null
    # Check container pattern stops cleanly when Docker sends SIGTERM.
    bash scripts/tests/check_lifecycle.sh "testing/service_proforma"



# remove temporary files
clean:


# RAG data to help robbie perform tasks
#   - A wizard that asks questions and informs about licence of downloaded work.
fetch-data:



## --------------------------------------------------------------------------------------------------------------------
# robbie managment
# install robbie to a pi, or update the installation on a pi
deploy-robbie: _update_configs

# get the pi version of robbie, and the backend running
run-robbie: backend-up

stop-robbie: backend-up


# get the pi version of robbies backend running
backend-up:

# get the pi version of robbies backend running
backend-down:


## --------------------------------------------------------------------------------------------------------------------
# local dev

_compose_local := "docker compose -f deploy/compose.local.yaml"

# (re-)start deploy/compose.local.yaml with any changes applied, so
up: _update_configs
    {{ _compose_local }} up -d --build --remove-orphans
    @just --justfile {{ quote(justfile()) }} banner "Phoenix (traces):  http://localhost:6006" blue


# stop all containers started by just up
down:
    {{ _compose_local }} down


# force rebuild (all by default) docker containers
rebuild *services:
    {{ _compose_local }} build --no-cache {{ services }}


_say_default_file := "testing/misc/wakeup_lines.txt"

# speak text with the voice service (needs just up); with no text, speaks the wake-up lines
say text="": _update_configs
    @{{ if text == "" { "just --justfile " + quote(justfile()) + " banner " + quote("No text given, speaking " + _say_default_file) + " yellow" } else { "true" } }}
    @mkdir -p .temp
    @{{ if text == "" { "cat " + _say_default_file } else { "printf '%s' " + quote(text) } }} | curl -fsS --data-binary @- -o .temp/say.wav http://127.0.0.1:8100/say
    @ffplay -nodisp -autoexit -loglevel error .temp/say.wav


## --------------------------------------------------------------------------------------------------------------------
# utils

# Resolve config/ into .config/default (for the Pi) and .config/local (for just up).
_update_configs:
    @python3 scripts/resolve_config.py .config config/robbie_agent config/robbie_services

# Print a message inside a coloured banner. color: green, yellow, red or blue.
[private]
banner msg color="green":
    @printf '%s\n%s\n%s%s\n' "{{ if color == "red" { RED } else if color == "yellow" { YELLOW } else if color == "blue" { BLUE } else { GREEN } }}{{ _banner_line }}" {{ quote(msg) }} "{{ _banner_line }}" "{{ NORMAL }}"
