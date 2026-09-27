# Prompt Optimizer

A CLI tool that **analyzes and rewrites prompts** following established prompt engineering best practices. Powered by **LangChain** + **Groq** (free tier, no credit card).

## Why I Built This

Prompt engineering is no longer about trial and error — it's a discipline with repeatable patterns (role definition, output contracts, chain-of-thought, constraints). Most developers still write vague, unstructured prompts that leave LLMs guessing. This tool automates the optimization cycle:

1. **Analyze** — identify exactly what's wrong with a prompt against 10 principles
2. **Structure** — rewrite it with role, objective, context, step-by-step instructions, constraints, and output format
3. **Iterate** — test the optimized prompt, refine, and repeat

The goal is to make production-quality prompting accessible from the terminal.

## Architecture

```
                    ┌──────────────┐
                    │  principles  │  10 rules + both system prompts
                    │     .py      │  (generated from one table)
                    └──────┬───────┘
                           │
   ┌───────────┐   ┌───────┴────────┐   ┌────────────┐   ┌──────────┐
   │  cli.py   │──▶│  analyzer.py   │──▶│   llm.py   │──▶│  Groq    │
   │ Click+Rich│   │  optimizer.py │   │ ChatGroq + │   │  API     │
   └─────┬─────┘   └───────┬────────┘   │ structured │   └──────────┘
         │                 │            │  output    │
         │            ┌────┴─────┐      └─────┬──────┘
         │            │ schemas  │            │
         │            │  .py     │      ┌─────┴──────┐
         │            │ Pydantic │      │ config.py  │
         │            └──────────┘      │ settings  │
         │                              │  + API key│
         ▼                              └────────────┘
   ┌──────────┐
   │ storage  │  one timestamped file per run, into saved/
   │   .py    │
   └──────────┘
```

| Module | Role |
|---|---|
| `cli.py` | Click entry point, Rich rendering, input gathering (arg / `--file` / stdin) |
| `analyzer.py` | Step 1 — prompt + grading instructions → `PromptAnalysis` |
| `optimizer.py` | Step 2 — prompt + analysis + rewrite instructions → `OptimizedPrompt` |
| `principles.py` | The 10 rules as one table; both system prompts are generated from it |
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
| **Groq** (`openai/gpt-oss-20b`) | `llm.py:35` | Powers both LLM calls via `ChatGroq`. Free tier, no credit card required |
| **LangChain** (`ChatGroq`, `ChatPromptTemplate`) | `llm.py:61`, `analyzer.py:33`, `optimizer.py:34` | Provider abstraction, prompt templates, chain composition with LCEL |
| **Structured Outputs** (`with_structured_output`) | `llm.py:61` | Groq's `json_schema` mode in **strict** mode uses constrained decoding, so every response matches the Pydantic schema — no JSON parse errors, and `Literal` fields can only return declared values |
| **Pydantic v2** (`BaseModel`, `Field`) | `schemas.py:19-56` | Data contracts for `PromptWeakness`, `PromptAnalysis`, `OptimizedPrompt` — validation + serialization |
| **Click** (`@click.group`, `@click.command`, `@click.option`) | `cli.py:208-256` | CLI framework with composable commands, argument parsing, and auto-generated `--help` |
| **Rich** (`Console`, `Panel`, `Table`, `Markdown`, `Columns`) | `cli.py:53-137` | Terminal UI — color-coded score panels, weakness tables, markdown rendering, status spinners |
| **python-dotenv** (`load_dotenv`) | `config.py:15` | Auto-loads `GROQ_API_KEY` from `.env` file — no manual config flags |
| **pytest** | `tests/` | 17 offline tests; no API key or network needed |
| **uv** | `pyproject.toml` | Package manager — single `uv sync` installs deps, builds package, registers CLI entry point |
| **Python 3.12** | `.python-version`, `pyproject.toml` | Type hints (`list[str]`, `dict[str, str]`), `str.removeprefix`/`removesuffix` |

## Installation

```bash
# 1. Clone the repository
git clone https://github.com/khadarbashajilan/prompt-optimizer-tool.git
cd prompt-optimizer-tool

# 2. Set your Groq API key (free, no credit card: https://console.groq.com/keys)
cp .env.example .env
# Then edit .env and add your key: GROQ_API_KEY=gsk_your-key-here

# 3. Run it
./run.sh
```

### Quick start

```bash
# Interactive menu — the easiest way in
./run.sh

# Or pass arguments straight through to the CLI
./run.sh optimize "write code in python to fetch api data"
./run.sh optimize --file prompt.txt
./run.sh list
```

`./run.sh` with no arguments opens a menu: optimize a pasted prompt, optimize
a file, list the 10 principles, show help, or quit. It verifies
`GROQ_API_KEY` is set and creates the virtualenv on first run.

## Usage

```bash
# Basic — analyze + optimize a prompt
uv run prompt-optimizer optimize "write code in python to fetch api data"

# Read from file
uv run prompt-optimizer optimize --file prompt.txt

# Pipe from stdin
echo "explain quantum computing to a 5 year old" | uv run prompt-optimizer optimize

# Each run is auto-saved to its own timestamped file in saved/
uv run prompt-optimizer optimize "write a blog post"
#   → saved/optimized-20260927-143205.md

# Choose a different output folder
uv run prompt-optimizer optimize "write a blog post" --out ~/prompts

# List all 10 prompting principles
uv run prompt-optimizer list
```

### Configuration

Every setting has a default and can be overridden with an environment
variable, so none of them require a code change:

| Variable | Default | Means |
|---|---|---|
| `GROQ_API_KEY` | *(required)* | Authorises the calls. Read from `.env` |
| `PROMPT_OPTIMIZER_MODEL` | `openai/gpt-oss-20b` | Which Groq model to use |
| `PROMPT_OPTIMIZER_TEMPERATURE` | `0.6` | Higher means more varied wording |
| `PROMPT_OPTIMIZER_MAX_TOKENS` | `4096` | Reply ceiling; lower values truncate long rewrites |
| `PROMPT_OPTIMIZER_MAX_RETRIES` | `3` | Attempts per call, handles free-tier rate limits |
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

## Limitations and Roadmap

What this tool does **not** do yet, so expectations are clear:

| Limitation | Current behavior | Fix |
|---|---|---|
| **No logging** | Errors print to the terminal only; no debug trail | Add structured logging (log file + `--debug` flag) |
| **No caching** | Analyze + Optimize each hit the API on every run | Cache analyses by prompt hash to avoid repeat cost |
| **No live-chain tests** | The 17 tests cover pure logic only; the two LLM steps are verified by hand | Add tests with a recorded or mocked Groq response |
| **No model fallback** | If the configured model is unavailable the run fails after retries | Add a second model to fall back to |
| **Console only** | No way to diff a rewrite against its previous version | Add `--diff <file>` to compare two saved runs |
| **No CI** | Tests only run locally | Add a GitHub Actions workflow running `uv run pytest` |

Planned next: logging, and live-chain tests with a mocked Groq response.

## Key Design Decisions

- **Structured Outputs in strict mode** — using `with_structured_output(Model, method="json_schema", strict=True)`. Groq's strict mode uses constrained decoding, so the response is guaranteed to match the Pydantic schema. Tool calling would be the alternative, but Groq does not support tool use together with Structured Outputs, and strict mode is the stronger guarantee.
- **Constrained decoding doubles as validation** — because the decoder can only emit declared values, `Literal` fields (`severity`, `principle`, `principles_applied`) cannot come back as typos or invented names. This is what guarantees the "Principles Applied" panel can always resolve a principle, instead of silently rendering nothing when the model returns a name rather than a key.
- **Closed schemas only** — strict mode requires every field to be required and every object to set `additionalProperties: false`. A free-form `dict[str, str]` collapses to an always-empty object under those rules, so `sections` is a `list[PromptSection]` (explicit `name` + `content`) instead.
- **Model choice: `openai/gpt-oss-20b`** — free tier, ~1000 tokens/sec, and one of only three models supporting strict-mode Structured Outputs. The old `llama-3.x` ids are Enterprise-only now, so they are not free.
- **`temperature=0.6`** — Groq recommends 0.5–0.7 for gpt-oss; the low values typical of deterministic chat models degrade into repetition and incoherent output on this model.
- **`max_tokens=4096`** — Groq's default of 1024 completion tokens truncates long rewritten prompts, which breaks JSON parsing.
- **One table, three consumers** — the 10 principles live in a single `PRINCIPLES` dict. The `list` command renders it, and both system prompts are generated from it. Previously the rules were hand-copied into both prompt strings, so editing a rule in one place silently left the other two stale.
- **Keys, not names, cross the wire** — the LLM is asked for principle *keys* (`role`), and `principle_name()` maps a key to a display title at render time. Fewer tokens in the prompt, and lookups cannot fail.
- **`config.py` owns every setting** — no `os.environ` reads and no magic numbers outside it. `llm.py` is the only module that knows how to reach Groq, so the two pipeline steps never construct a client themselves.
- **One-way dependencies** — `cli` → `analyzer`/`optimizer` → `llm` → `config`, with `principles` and `schemas` at the bottom. The optimizer used to import its client from the analyzer, which inverted the natural reading order for no benefit.
- **Flat module layout** — no `src/` nesting; every module is importable by name. Keeps the entry point simple: `cli:cli`.
- **Rich for DX** — color-coded severity, panel layouts, markdown rendering, and status spinners give instant visual feedback without a single HTML page.
- **Config-free API Key** — `python-dotenv` loads `.env` automatically; no `--api-key` flag cluttering the interface.
- **Zero-config Package Management** — `uv` handles deps, build, and entry point registration in one command.

## Development

```bash
uv sync                 # install deps
uv run pytest           # 17 offline tests, no API key needed
uv run prompt-optimizer list
```

## Project Structure

```
prompt-optimizer/
  pyproject.toml          # uv project config with entry point
  run.sh                  # bootstrap + interactive menu
  .env.example            # GROQ_API_KEY template
  .gitignore
  cli.py                  # Click commands + Rich rendering
  analyzer.py             # Step 1: grade a prompt
  optimizer.py            # Step 2: rewrite it
  principles.py           # 10 principles; generates both system prompts
  schemas.py              # Pydantic contracts for structured I/O
  llm.py                  # the only module that talks to Groq
  config.py               # all settings + API key loading
  storage.py              # timestamped path per run, then write
  tests/                  # offline tests, no network
  saved/                  # one file per run, gitignored
```


