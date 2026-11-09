# Contributing

Thanks for helping! Keep changes small and focused.

## Setup

```bash
git clone https://github.com/<your-username>/prompt-optimizer-tool.git
cd prompt-optimizer-tool
uv sync --all-groups
```

Requires Python 3.12+ and [uv](https://docs.astral.sh/uv/getting-started/installation/).

## Tests

```bash
uv run pytest
uv run pytest --cov=prompt_optimizer_tool --cov-report=term-missing
```

The tests are offline — no API key needed. CI requires **94% coverage**, so add
tests for new behaviour.

For manual testing, run `uv run prompt-optimizer setup` to configure a Groq key.

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

Never commit a real API key or `.env` file. If a key leaks, revoke it at
<https://console.groq.com/keys>.

## License

By contributing, you agree that your work is licensed under the
project's [MIT License](LICENSE).
