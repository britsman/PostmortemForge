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

## [0.5.0] - 2025-11-18

### Added

- Windowed correlation between deploys, metric breach intervals, and log
  error bursts (`correlate.py`), plus rollback-to-recovery detection that
  names the deploy that a metric recovery or log quiet period is attributed
  to.
- `timeline` subcommand that prints the correlated timeline in minutes from
  the first event.

### Changed

- Breach intervals are now computed from the declared threshold at ingest
  time, so the same metric file can be re-run with different thresholds
  without re-reading the source.

## [0.4.0] - 2024-06-21

### Added

- Clock alignment against a declared reference clock (`clockalign.py`): per
  source offset plus linear skew anchored at a chosen instant.
- `ingest` subcommand that lists every aligned event with its source span.

### Fixed

- Events on the exact boundary of an alignment window are no longer dropped
  when the skew model anchors at the window end.

## [0.3.0] - 2023-08-09

### Added

- Reader for application logs (`sources.py`) with one event per line, a
  required timestamp field, and source file/line span tracking.
- Reader for a metric series with a declared threshold, and a reader for a
  deploy record, both with the same span tracking as the log reader.

### Changed

- All readers now share a single event model, so alignment and correlation
