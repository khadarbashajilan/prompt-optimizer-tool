# plint

Give it a rough prompt. Get back a score and a better version.

[![CI](https://github.com/khadarbashajilan/prompt-optimizer-tool/actions/workflows/test.yml/badge.svg)](https://github.com/khadarbashajilan/prompt-optimizer-tool/actions)
[![PyPI version](https://img.shields.io/pypi/v/prompt-lint.svg)](https://pypi.org/project/prompt-lint/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

![Demo](media/demo.gif)

## What it does

1. **Scores** your prompt from 0 to 100 against 10 prompt-writing principles.
2. **Lists** what is good and what is weak, with a fix for each weakness.
3. **Rewrites** it into a clear, structured prompt you can copy and use.
4. **Saves** the result to a file in `saved/`.

It works with any LLM provider through [LiteLLM](https://docs.litellm.ai/docs/providers) (Gemini, OpenAI, Anthropic, Ollama and more). You need an API key for the provider you choose.

## Install

```bash
uv tool install prompt-lint
# or: pipx install prompt-lint
```

Then pick a model and save your key:

```bash
plint setup
```

## Use

```bash
# Optimize a prompt
plint "write code in python to fetch api data"

# From a file
plint --file prompt.txt

# From stdin
echo "explain quantum computing to a 5 year old" | plint

# Save somewhere else (default: ./saved)
plint "write a blog post" --out ~/prompts

# Show the 10 principles
plint list

# Choose a model and save its API key
plint setup
```

`plint "..."` is shorthand for `plint optimize "..."`.

## Choose a model

plint uses [LiteLLM](https://docs.litellm.ai/docs/providers), so the model is a `provider/model` string. `plint setup` asks for it and for the matching API key, and saves both to `~/.plint/config.env`. You can also set them yourself:

| Model (`PLINT_MODEL`) | Key it needs |
|---|---|
| `gemini/gemini-2.5-flash` (default) | `GEMINI_API_KEY` |
| `openai/gpt-4o-mini` | `OPENAI_API_KEY` |
| `anthropic/claude-sonnet-4-5` | `ANTHROPIC_API_KEY` |
| `ollama/llama3.1` | none (local) |

```bash
PLINT_MODEL=openai/gpt-4o-mini plint "write a haiku prompt"
```

Settings are read from the environment, then a `.env` in the current folder, then `~/.plint/config.env`; exported variables win. Optional: `PLINT_API_BASE` (custom endpoint such as vLLM), `PLINT_TEMPERATURE`, `PLINT_MAX_TOKENS`, `PLINT_MAX_RETRIES`, `PLINT_TIMEOUT`, `PLINT_OUTPUT_DIR`. The old `PROMPT_OPTIMIZER_*` names and `~/.prompt-optimizer/` still work.

Each run is saved as `saved/optimized-<date>-<time>.md`, so nothing gets overwritten.

## The 10 principles

1. Role and persona
2. Clear objective
3. Context
4. Step-by-step instructions
5. Constraints and rules
6. Output format
7. Few-shot examples
8. Chain of thought
9. Success criteria
10. Specific language

## Built with

Python, LiteLLM, LangChain, Pydantic, Click, Rich.

## Run from source

```bash
git clone https://github.com/khadarbashajilan/prompt-optimizer-tool.git
cd prompt-optimizer-tool
cp .env.example .env   # set your model and API key
./run.sh
```

## Develop

```bash
uv run pytest
```

Tests run offline and need no API key. See [CONTRIBUTING.md](CONTRIBUTING.md) for the code layout and PR guidelines.

Benchmark results (run on `openai/gpt-oss-20b`, before the move to LiteLLM): [eval/results/20261108-220810.md](eval/results/20261108-220810.md)

## License

[MIT](LICENSE)
