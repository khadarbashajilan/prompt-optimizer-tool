"""Analyze and rewrite prompts against ten prompt engineering principles.

Import layering, which the module structure mirrors:

    cli  ->  analyzer, optimizer  ->  llm  ->  config
                  |
                  +-> principles, schemas   (no internal dependencies)

Dependencies point one way only. `principles` and `schemas` sit at the
bottom and import nothing from the rest of the package, so either pipeline
step can be swapped, retried, or tested without touching the other.

This module deliberately has no side effects: it must stay importable
without a configured API key, and importing it must not load .env.
"""

__version__ = "0.1.0"
