# Prompt Optimizer

Give it a rough prompt. Get back a score and a better version.

[![CI](https://github.com/khadarbashajilan/prompt-optimizer-tool/actions/workflows/test.yml/badge.svg)](https://github.com/khadarbashajilan/prompt-optimizer-tool/actions)
[![PyPI version](https://img.shields.io/pypi/v/prompt-optimizer-tool.svg)](https://pypi.org/project/prompt-optimizer-tool/)
[![Python 3.12+](https://img.shields.io/badge/python-3.12%2B-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](LICENSE)

![Demo](media/demo.gif)

## What it does

1. **Scores** your prompt from 0 to 100 against 10 prompt-writing principles.
2. **Lists** what is good and what is weak, with a fix for each weakness.
3. **Rewrites** it into a clear, structured prompt you can copy and use.
4. **Saves** the result to a file in `saved/`.

It runs on [Groq](https://console.groq.com), so you need a Groq API key.

## Install

```bash
uv tool install prompt-optimizer-tool
# or: pipx install prompt-optimizer-tool
```

Then save your key (get one at <https://console.groq.com/keys>):

```bash
prompt-optimizer setup
```

## Use

```bash
# Optimize a prompt
prompt-optimizer optimize "write code in python to fetch api data"

# From a file
prompt-optimizer optimize --file prompt.txt

# From stdin
echo "explain quantum computing to a 5 year old" | prompt-optimizer optimize

# Save somewhere else
prompt-optimizer optimize "write a blog post" --out ~/prompts

# Show the 10 principles
prompt-optimizer list
```

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

Python, Groq, LangChain, Pydantic, Click, Rich.

## Run from source

```bash
git clone https://github.com/khadarbashajilan/prompt-optimizer-tool.git
cd prompt-optimizer-tool
cp .env.example .env   # add your GROQ_API_KEY
./run.sh
```

## Develop

```bash
uv run pytest
```

Tests run offline and need no API key. See [CONTRIBUTING.md](CONTRIBUTING.md) for the code layout and PR guidelines.

Benchmark results: [eval/results/20261108-220810.md](eval/results/20261108-220810.md)

## License

[MIT](LICENSE)
