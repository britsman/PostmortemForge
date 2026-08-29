# Contributing to PostmortemForge

Thanks for helping make incident write-ups less painful. A few ground rules
keep the tool honest.

## Ground rules

- **Timeline first.** Every feature must ultimately serve the timeline:
  parsing, aligning, or rendering it. If a change does not make the timeline
  more trustworthy, it probably belongs in a different tool.
- **Samples stay synthetic.** Never commit real incident logs, hostnames, or
  customer identifiers. `samples/` uses synthetic data only.
- **Deterministic rendering.** The same inputs must produce byte-identical
  markdown output. No wall-clock in templates, no dict iteration order.

## Workflow

1. Branch from `main` (`feat/<topic>` or `fix/<topic>`).
2. One behaviour per PR - small and reviewable.
3. Check locally:
   ```bash
   pip install -e .
   pytest
   ruff check src tests
   ```
4. Open the PR with a short description of *why*, not just *what*.

## Adding a log-format parser

Parsers live in `src/postmortemforge/parsers/`. Each one needs:

- a `parse()` yielding `Event(timestamp, source, kind, summary)` objects,
- unit tests with a synthetic fixture in `tests/fixtures/`,
- an entry in the parser registry and `docs/formats.md`.

## Reporting issues

Use the bug template. Attach the anonymised log sample that mis-parses (or a
few synthetic lines in the same format) - timestamps and one event each is
enough to reproduce most alignment bugs.

## Code style

- `ruff` defaults; `pytest -q` must stay green.
- CLI output is part of the API: golden tests in `tests/golden/` guard the
  rendered markdown of every subcommand.
