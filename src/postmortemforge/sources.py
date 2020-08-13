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

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass, field
from typing import Iterator


class SourceError(ValueError):
    """Raised when a source file cannot be parsed."""


@dataclass(frozen=True)
class Provenance:
    """Where an event came from: a file and a 1-based inclusive line span."""

    path: str
    line_start: int
    line_end: int

    def span(self) -> str:
        if self.line_start == self.line_end:
            return f"{self.path}:{self.line_start}"
        return f"{self.path}:{self.line_start}-{self.line_end}"


@dataclass(frozen=True)
class Event:
    """A single observed event on one source's own clock.

    raw_ts is seconds since the Unix epoch as written in the file, before any
    clock alignment. kind is one of log, metric, deploy. attrs holds parsed
    fields specific to the kind. text is a short human label. prov records the
    exact source location.
    """

    raw_ts: float
    kind: str
    text: str
    attrs: dict = field(default_factory=dict)
    prov: Provenance = None  # type: ignore[assignment]


@dataclass(frozen=True)
class MetricMeta:
