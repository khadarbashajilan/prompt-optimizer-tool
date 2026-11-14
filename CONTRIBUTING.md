# Contributing

Thanks for helping! Keep changes small and focused.

## Setup

```bash
git clone https://github.com/<your-username>/prompt-optimizer-tool.git
cd prompt-optimizer-tool
uv sync --all-groups
```

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).

## Code layout

```
src/prompt_lint/
  cli/          Click commands, terminal rendering, error messages
  analyzer.py   prompt -> PromptAnalysis (score, strengths, weaknesses)
  optimizer.py  prompt + analysis -> OptimizedPrompt
  llm.py        the only module that calls the provider (via LiteLLM)
  config.py     settings, credential checks, saved config
  prompts.py    prompt templates; principles.py: the 10 principles
  schemas.py    Pydantic models the LLM reply must match
  storage.py    timestamped output files
eval/           benchmark harness (needs a real API key)
tests/          offline tests; the LLM is always faked
media/          demo.gif and make_demo.py, which records the real CLI into it
```

## Tests

```bash
uv run pytest
uv run pytest --cov=prompt_lint --cov-report=term-missing
```

The tests are offline — no API key needed. CI requires **94% coverage**, so add
tests for new behaviour.

For manual testing, run `uv run plint setup` (or export `PLINT_MODEL` and the key) to pick a model and configure its key.

## Pull requests

1. Fork the repo and create a branch.
2. Make your change.
3. Run the tests.
4. Open a PR against `main`.

In the PR description, include what changed, why, and how you tested it.

## Reporting bugs

Include the command you ran, what you expected, what happened, the error, and
your OS/Python/version. Redact API keys and private prompt content.

## Secrets

Never commit a real API key or `.env` file. If a key leaks, revoke it with your provider.

## License

By contributing, you agree that your work is licensed under the
project's [MIT License](LICENSE).
