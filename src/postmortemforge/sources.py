"""Readers for the three offline export kinds.

Each reader yields Event records carrying provenance: the source file path and
the 1-based line span the event was parsed from. Provenance is what lets the
draft writer cite an exact source location for every statement it emits.

Export kinds:

- logs: application log lines in the form
      ISO8601 LEVEL message
  Example:
      2026-03-01T08:00:04Z INFO request served status=200
- metric: a metric series in the form
      ISO8601 value
  with a header line declaring the metric name, unit, and breach threshold:
      # metric latency_p99_ms unit=ms threshold=400 direction=above
- deploy: a deploy record, one action per line in the form
      ISO8601 action ref=<ref>
  where action is one of deploy or rollback.

Timestamps are parsed as naive UTC seconds since the Unix epoch. Clock
alignment (offset and skew) is applied later by clockalign, not here. Reading
is deliberately dumb: it records what the file says, verbatim, with location.
"""
