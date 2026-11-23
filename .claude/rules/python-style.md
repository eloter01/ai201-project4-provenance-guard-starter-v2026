# Python conventions

- PEP 8 with 79-character lines.
- Small, single-purpose functions.
- Type hints on every function signature.
- Validate arguments explicitly (None, empty, wrong type) before processing.
- Catch specific exceptions only. Never `except Exception:` or bare `except:`.
- Choose LBYL or EAFP to fit the context.
- Comments explain why, never what.
- Docstrings: one-line purpose, then Args, Returns, Raises.
- Use `with` for files and connections, f-strings, and `pathlib` over `os.path`.