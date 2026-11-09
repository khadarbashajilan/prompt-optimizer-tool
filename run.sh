#!/usr/bin/env bash
# Launch the prompt-optimizer CLI: bootstraps deps, then offers an interactive menu.
set -euo pipefail

cd "$(dirname "$0")"
trap 'echo; exit 130' INT

PROMPT_TEXT=""

# --- preflight: API key -------------------------------------------------
# A placeholder copied straight from .env.example is not a key; fail before
# spending time on `uv sync`.
read_env_key() {
    grep -E '^GROQ_API_KEY=.+$' .env 2>/dev/null | head -1 | cut -d= -f2- || true
}

resolve_api_key() {
    local key="${GROQ_API_KEY:-}"

    if [ -z "$key" ]; then
        key=$(read_env_key)
        case "$key" in
            your-*|gsk_your-*) key="" ;;
        esac
    fi

    if [ -z "$key" ]; then
        echo "GROQ_API_KEY is not set (or is still the .env.example placeholder)."
        echo "Add a real key to .env (see .env.example) or export it:"
        echo "  export GROQ_API_KEY='your-key-here'   # from https://console.groq.com/keys"
        exit 1
    fi
}

# --- preflight: runner ---------------------------------------------------
resolve_runner() {
    if [ -x .venv/bin/prompt-optimizer ]; then
        cli() { .venv/bin/prompt-optimizer "$@"; }
    elif command -v uv >/dev/null 2>&1; then
        echo "Creating virtualenv (uv sync)..."
        uv sync
        cli() { uv run prompt-optimizer "$@"; }
    elif [ -x .venv/bin/python ]; then
        # PYTHONPATH=src so this works even if the project was never installed
        # into that virtualenv.
        cli() { PYTHONPATH=src .venv/bin/python -m prompt_optimizer_tool.cli "$@"; }
    else
        echo "No runner found."
        echo "Install uv: https://docs.astral.sh/uv/getting-started/installation/"
        echo "or create a virtualenv with: python3 -m venv .venv"
        exit 1
    fi
}

resolve_api_key
resolve_runner

# pass-through: ./run.sh optimize "your prompt"
if [ "$#" -gt 0 ]; then
    cli "$@"
    exit $?
fi

# --- helpers -------------------------------------------------------------
# Fills PROMPT_TEXT. No command substitution: that would run this in a
# subshell and swallow the prompt into the captured value.
read_prompt() {
    local line
    PROMPT_TEXT=""
    echo "Paste your prompt. Submit an empty line when done."
    while IFS= read -r line; do
        [ -z "$line" ] && break
        PROMPT_TEXT+="$line"$'\n'
    done
}

prompt_is_empty() {
    [ -z "${PROMPT_TEXT//[[:space:]]/}" ]
}

menu() {
    cat <<'EOF'

  prompt-optimizer
  ----------------
  1) Optimize a prompt      paste it, then press Enter on a blank line
  2) Optimize from a file   path to a .txt / .md file
  3) List the 10 principles
  4) Show CLI help
  0) Quit

EOF
}

# --- menu loop -----------------------------------------------------------
while true; do
    menu
    read -r -p "Choose [0-4]: " choice || exit 0
    case "${choice:-0}" in
        1)
            echo
            read_prompt
            if prompt_is_empty; then
                echo "Empty prompt, skipped."
                continue
            fi
            echo
            printf '%s' "$PROMPT_TEXT" | cli optimize || echo "Optimize failed."
            ;;
        2)
            echo
            read -r -p "File path: " path
            if [ ! -f "$path" ]; then
                echo "No such file: $path"
                continue
            fi
            echo
            cli optimize --file "$path" || echo "Optimize failed."
            ;;
        3) cli list ;;
        4) cli --help ;;
        0|q|Q) echo "Bye."; exit 0 ;;
        *) echo "Invalid choice: $choice" ;;
    esac
done
