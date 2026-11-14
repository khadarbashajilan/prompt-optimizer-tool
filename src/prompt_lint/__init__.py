"""Analyze and rewrite prompts against ten prompt engineering principles.

Import layering, which the module structure mirrors:

    cli  ->  analyzer, optimizer  ->  llm  ->  config
                  |
                  +-> prompts  ->  principles
                  |
                  +-> schemas

Dependencies point one way only. `principles` and `schemas` sit at the
bottom and import nothing from the rest of the package. `prompts` depends
only on `principles`, so prompt wording can change without touching either
pipeline step.

This module deliberately has no side effects: it must stay importable
without a configured API key, and importing it must not load .env.
"""

__version__ = "0.1.5"
