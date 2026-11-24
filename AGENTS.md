# Repository Guidelines

## Project: Provenance Guard

Spec: `docs/SPEC_phase_1.md`. Read the section for the current step before planning it.

## Project Structure

Provenance Guard is a local Flask service that labels submitted writing and
records appeals. `app.py` defines the HTTP routes. `detector.py` runs the local
model, `stylometry.py` measures writing style, and `scoring.py` combines the
signals and maps scores to labels. Put settings in `config.py` and use
`audit.py` for JSONL audit records.

See [RUNNING.md](RUNNING.md) for setup and troubleshooting and the
[Phase 1 spec](docs/SPEC_phase_1.md) for milestones. `criteria.md` holds the
acceptance targets, `scenarios.py` defines evaluation inputs, and `README.md`
is the course write-up. `logs/` and `results/` hold submission evidence.

## Setup and Local Development

- Use Python 3.11–3.13. Create `.venv` with `python -m venv .venv`, activate
  it, and run `python -m pip install -r requirements.txt`.
- Run `python test.py` to check dependencies and smoke-test Flask.
- Run `python detector.py` to download the model on first use and score a
  sample. Then run `python app.py` to serve at `http://127.0.0.1:5000`.

## Workflow
- Break work into small, independent steps. At the start of a feature, list the steps first.
- Deliver exactly ONE committable change per turn: the codebase works and tests pass after it.
- End each step with a Conventional Commits message, e.g. `feat(chunker): add input validation`.
- Then stop and wait. Commit only after I say "commit it", then move to the next step.

## Coding Style

Follow PEP 8 with four-space indentation, 79-character lines, `snake_case`
functions and variables, `PascalCase` classes, and `UPPER_CASE` constants.
Keep functions focused, annotate signatures, and use Google-style docstrings
for public functions and classes. Validate inputs before processing and catch
specific exceptions. Prefer `pathlib` for paths and `with` for file access.
Use `python -m ruff check .` for linting and
`python -m ruff format --check .` for formatting checks.

- Type hints on every function signature.
- Validate arguments explicitly (None, empty, wrong type) before processing.
- Catch specific exceptions only. Never `except Exception:` or bare `except:`.
- Choose LBYL or EAFP to fit the context.
- Comments explain why, never what.

## Testing

Keep `/ping` available as a smoke-test control. Add pytest cases under `tests/`
using `test_*.py` files and descriptive `test_*` functions. Run them with
`python -m pytest -q`. Code coverage is unconfigured in the starter. With the
service running, use
`python run_eval.py --label before` to check the five acceptance criteria
across three trials.

## Commits and Pull Requests

Follow the history with short, action-oriented subjects such as `Pin certifi`
or `Fix JSON body handling`. In PRs, summarize the change, list verification
commands and outcomes, and link related issues when available. For course
submissions, make at least four new commits per unit, keep the same repository
URL, and commit the relevant audit logs and result reports. Starter maintainers
should follow [.github/MAINTAINERS.md](.github/MAINTAINERS.md) when pushing.

## Writing
- READMEs and docs: simple, concise, easy to read.