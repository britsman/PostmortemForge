# Changelog

All notable changes to this project are documented here. The format follows
Keep a Changelog, and this project adheres to semantic versioning.

## [Unreleased]

### Added

- `ingest` and `timeline` now accept an `--out` flag that writes the aligned
  event list or the correlated timeline to a file instead of stdout, so a
  review can keep the evidence snapshot next to the draft.

## [0.6.0] - 2026-09-02

### Added

- Postmortem draft writer (`draft.py`) where every statement cites the exact
  source file and line span it came from; ungrounded statements are omitted.
- `--window` flag on `draft` to bound the correlation window used by the
  draft's timeline section.

### Changed

- Draft output is now deterministic: events are sorted by aligned time, then
  by source order, independent of input file order.
