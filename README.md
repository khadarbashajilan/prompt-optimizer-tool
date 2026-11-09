# Prompt Optimizer

> **Stop guessing. Start engineering.** A CLI tool that scores your prompt against 10 principles and rewrites it into a production-ready, structured prompt — powered by **Groq**.

[![CI](https://github.com/khadarbashajilan/prompt-optimizer-tool/actions/workflows/test.yml/badge.svg)](https://github.com/khadarbashajilan/prompt-optimizer-tool/actions)
[![PyPI version](https://img.shields.io/pypi/v/prompt-optimizer-tool.svg)](https://pypi.org/project/prompt-optimizer-tool/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

![Demo](media/demo.gif)

---

## Architecture

```
principles.py ──▶ prompts.py

cli/ ──▶ analyzer.py / optimizer.py ──▶ llm.py ──▶ Groq API
  │              │                        │
  │              └──▶ schemas.py          └──▶ config.py
  ▼
storage.py
```

| Module | Role |
|---|---|
| `cli/` | Click entry point, input gathering (arg / `--file` / stdin), pipeline orchestration |
| `cli/ui.py` | Rich console, colour helpers, and all report rendering |
| `cli/errors.py` | Turns pipeline failures into actionable terminal messages |
| `analyzer.py` | Step 1 — prompt + grading instructions → `PromptAnalysis` |
| `optimizer.py` | Step 2 — prompt + analysis + rewrite instructions → `OptimizedPrompt` |
| `principles.py` | The 10 rules as one data table |
| `prompts.py` | All LLM prompt text: both system prompts + human templates |
| `schemas.py` | Pydantic contracts: `PromptWeakness`, `PromptAnalysis`, `OptimizedPrompt` |
| `llm.py` | The only module that knows how to talk to Groq |
| `config.py` | Every setting in one place, each overridable by env var |
| `storage.py` | Builds a timestamped path per run and writes it |
| `run.sh` | Bootstraps the venv, checks the API key, then offers an interactive menu |

Dependencies point one way only: `cli` → `analyzer`/`optimizer` → `llm` → `config`.
`principles` and `schemas` sit at the bottom with no internal dependencies, so
either step can be swapped, retried, or tested without touching the other.

### Workflow

```
User Prompt ──▶ Analyze ──▶ Quality Score (0-100)
                    │           + Strengths
                    │           + Weaknesses (with severity & suggestions)
                    ▼
               Optimize ──▶ Structured Prompt
                               + Role / Objective / Context
                               + Step-by-Step Instructions
                               + Constraints & Rules
                               + Output Format
                               + Success Criteria
                               + Changes Made Summary
                               + Principles Applied List
```

### The 10 Principles

Defined once in `principles.py` and reused everywhere:

1. **Role & Persona Definition** — assign expertise level and perspective
2. **Clear Objective** — one-sentence goal statement
3. **Context Provision** — background, audience, environment
4. **Step-by-Step Instructions** — sequential breakdown of complex tasks
5. **Constraints & Rules** — boundaries, exclusions, length limits
6. **Output Format Specification** — JSON, markdown, bullet points, etc.
7. **Few-Shot Examples** — demonstrate desired pattern with examples
8. **Chain of Thought** — request reasoning for multi-step problems
9. **Success Criteria** — define measurable quality bar
10. **Specific Language** — replace vague qualifiers with precise terms

## Tech Stack

| Technology | Where Used | Purpose |
|---|---|---|
| **Groq** (`openai/gpt-oss-20b`) | `src/prompt_optimizer_tool/llm.py` | Powers both LLM calls via `ChatGroq`. Free tier available |
| **LangChain** (`ChatGroq`, `ChatPromptTemplate`) | `src/prompt_optimizer_tool/llm.py`, `analyzer.py`, `optimizer.py` | Provider abstraction, prompt templates, chain composition with LCEL |
| **Structured Outputs** (`with_structured_output`) | `src/prompt_optimizer_tool/llm.py` | Groq's `json_schema` mode in **strict** mode uses constrained decoding, so every response matches the Pydantic schema — no JSON parse errors, and `Literal` fields can only return declared values |
| **Pydantic v2** (`BaseModel`, `Field`) | `src/prompt_optimizer_tool/schemas.py` | Data contracts for `PromptWeakness`, `PromptAnalysis`, `OptimizedPrompt` — validation + serialization |
| **Click** (`@click.group`, `@click.command`, `@click.option`) | `src/prompt_optimizer_tool/cli/__init__.py` | CLI framework with composable commands, argument parsing, and auto-generated `--help` |
| **Rich** (`Console`, `Panel`, `Table`, `Markdown`, `Columns`) | `src/prompt_optimizer_tool/cli/ui.py` | Terminal UI — color-coded score panels, weakness tables, markdown rendering, status spinners |
| **python-dotenv** (`load_dotenv`) | `src/prompt_optimizer_tool/config.py` | Auto-loads `GROQ_API_KEY` from `.env` file — no manual config flags |
| **pytest** (offline suite) | `tests/` | 80+ cases, no API key or network needed: CLI flow via `CliRunner`, the LLM seam with a fake provider, schemas, principles, config, storage, eval |
| **uv** | `pyproject.toml` | Package manager — single `uv sync` installs deps, builds package, registers CLI entry point |
| **Python 3.12** | `.python-version`, `pyproject.toml` | Type hints (`list[str]`, `dict[str, str]`), `str.removeprefix`/`removesuffix` |

## Installation

Published on PyPI as [`prompt-optimizer-tool`](https://pypi.org/project/prompt-optimizer-tool/).

```bash
# Try it instantly, nothing is installed
uvx --from prompt-optimizer-tool prompt-optimizer list

# Install as an isolated tool (recommended)
uv tool install prompt-optimizer-tool

# or with pipx
pipx install prompt-optimizer-tool
```

### Set your Groq API key

Get a key at <https://console.groq.com/keys>.

```bash
# Interactive setup — saves key permanently to ~/.prompt-optimizer/config.env
prompt-optimizer setup

# Or export it manually for the current session
export GROQ_API_KEY=gsk_your-key-here
```

### Install from source (alternative)

```bash
git clone https://github.com/khadarbashajilan/prompt-optimizer-tool.git
cd prompt-optimizer-tool
cp .env.example .env   # then edit .env: GROQ_API_KEY=gsk_your-key-here
./run.sh
```

## Usage

```bash
# 1. First-time setup — save your Groq API key permanently
prompt-optimizer setup

# 2. Analyze + optimize a prompt
prompt-optimizer optimize "write code in python to fetch api data"

# Read from file
prompt-optimizer optimize --file prompt.txt

# Pipe from stdin
echo "explain quantum computing to a 5 year old" | prompt-optimizer optimize

# Each run is auto-saved to its own timestamped file in saved/
prompt-optimizer optimize "write a blog post"
#   → saved/optimized-20260927-143205.md

# Choose a different output folder
prompt-optimizer optimize "write a blog post" --out ~/prompts

# List all 10 prompting principles
prompt-optimizer list
```

### Configuration

Every setting has a default and can be overridden with an environment
variable, so none of them require a code change:

| Variable | Default | Means |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Authorises the calls. Read from `.env` |
| `PROMPT_OPTIMIZER_MODEL` | `openai/gpt-oss-20b` | Which Groq model to use |
| `PROMPT_OPTIMIZER_TEMPERATURE` | `0.6` | Higher means more varied wording |
| `PROMPT_OPTIMIZER_MAX_TOKENS` | `8192` | Reply ceiling; lower values truncate long rewrites |
| `PROMPT_OPTIMIZER_MAX_RETRIES` | `3` | Attempts per call, handles transient rate limits |
| `PROMPT_OPTIMIZER_TIMEOUT` | `60` | Per-request seconds, so a stalled call cannot hang |
| `PROMPT_OPTIMIZER_OUTPUT_DIR` | `saved` | Default folder for saved rewrites |

### Example Output

The tool produces a structured report:

- **Quality Score** — color-coded (green ≥70, yellow ≥40, red <40)
- **Strengths** — what the original prompt does well
- **Weaknesses & Improvements** — each issue with severity, violated principle, and concrete fix
- **Changes Made** — summary of all improvements applied
- **Optimized Prompt** — the complete rewritten prompt (copy-ready)
- **Principles Applied** — which of the 10 principles were used
- **Auto-save** — every run writes its own file to `saved/`, named for the date and time of the run, so results accumulate instead of overwriting

## Project Structure

```
prompt-optimizer/
  pyproject.toml          # uv project config with entry point
  run.sh                  # bootstrap + interactive menu
  CONTRIBUTING.md         # setup, tests, and PR guidelines
  .env.example            # GROQ_API_KEY template
  .gitignore
  src/
    prompt_optimizer_tool/
      __init__.py         # package version + layering notes
      cli/
        __init__.py       # Click commands + pipeline orchestration
        ui.py             # Rich console, renderers, colour helpers
        errors.py         # user-facing error messages
        __main__.py       # python -m prompt_optimizer_tool.cli
      analyzer.py         # Step 1: grade a prompt
      optimizer.py        # Step 2: rewrite it
      principles.py       # 10 principles as data
      prompts.py          # system prompts + human templates
      schemas.py          # Pydantic contracts for structured I/O
      llm.py              # the only module that talks to Groq
      config.py           # all settings + API key loading
      storage.py          # timestamped path per run, then write
  eval/
    run_eval.py           # stable entry point + facade
    harness/              # internal harness modules
      rubric.py           # rubric constants + section detection
      prompt_io.py        # JSONL prompt loading
      pipeline.py         # Row + analyze/optimize/rescore execution
      metrics.py          # aggregation and headline metrics
      report.py           # markdown/JSON rendering + writing
    data/
      prompts.jsonl       # 24 benchmark prompts
    results/              # timestamped eval outputs
  tests/
    support.py            # FakeProvider + fresh-model factories
    conftest.py           # fixtures for the two test seams
    test_cli.py           # end-to-end: input modes, exit codes, saving
    test_pipeline.py      # schema + message contracts at the LLM seam
    test_principles.py    # table/Literal/prompt consistency
    test_schemas.py       # validation bounds and Literal values
    test_config.py        # API key resolution + placeholder rejection
    test_storage.py       # timestamped naming, collision, folders
  saved/                  # one file per run, gitignored
  media/
    demo.gif              # animated demo (auto-generated)
```

---

## Evaluation Results

Benchmark run across 24 real-world prompts on 2026-11-08 (20 scored, 4 failed) — full metrics, scores, and principle coverage:

📄 **[eval/results/20261108-220810.md](eval/results/20261108-220810.md)**

---

## Contributing

See **[CONTRIBUTING.md](CONTRIBUTING.md)** for setup, tests, code layout, and PR guidelines.

1. Fork → branch → PR against `main`
2. Run the offline test suite: `uv run pytest` — CI enforces **94% coverage**
3. No API key needed for tests; the LLM seam is faked via `FakeProvider` in `tests/support.py`
4. Run `prompt-optimizer setup` to configure your Groq key for manual testing

---

## License

[MIT](LICENSE)
