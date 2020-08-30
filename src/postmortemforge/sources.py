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
    """Declared metadata for a metric series, parsed from its header line."""

    name: str
    unit: str
    threshold: float
    direction: str  # above or below

    def breached(self, value: float) -> bool:
        if self.direction == "above":
            return value > self.threshold
        return value < self.threshold


def _parse_ts(token: str, path: str, line_no: int) -> float:
    """Parse an ISO8601 UTC timestamp to epoch seconds.

    Accepts a trailing Z or an explicit +00:00 offset. Rejects anything else so
    a malformed export fails loudly rather than silently misaligning.
    """
    t = token
    if t.endswith("Z"):
        t = t[:-1] + "+00:00"
    try:
        dt = _dt.datetime.fromisoformat(t)
    except ValueError as exc:
        raise SourceError(f"{path}:{line_no}: bad timestamp {token!r}") from exc
    if dt.tzinfo is None:
        dt = dt.replace(tzinfo=_dt.timezone.utc)
    return dt.timestamp()


def _iter_lines(text: str) -> Iterator[tuple[int, str]]:
    for i, line in enumerate(text.splitlines(), start=1):
        yield i, line


def read_logs(text: str, path: str) -> list[Event]:
    """Parse application log lines into Event records.

    Format per line: `<iso8601> <LEVEL> <message>`. Blank lines and lines
    starting with # are skipped. The message is kept verbatim as the label.
    """
    events: list[Event] = []
    for line_no, line in _iter_lines(text):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split(None, 2)
        if len(parts) < 2:
            raise SourceError(f"{path}:{line_no}: log line needs a timestamp and level")
        ts = _parse_ts(parts[0], path, line_no)
        level = parts[1].upper()
        message = parts[2] if len(parts) == 3 else ""
        events.append(
            Event(
                raw_ts=ts,
                kind="log",
                text=message or level,
                attrs={"level": level, "message": message},
                prov=Provenance(path, line_no, line_no),
            )
        )
    return events


def read_metric(text: str, path: str) -> tuple[MetricMeta, list[Event]]:
    """Parse a metric series and its declared header.

    The header line, starting with `# metric`, declares name, unit, threshold,
    and direction. Each subsequent data line is `<iso8601> <value>`. Every data
    point becomes an Event; the attrs record the value and whether it breached
    the declared threshold, so correlation can find the breach window.
    """
    meta: MetricMeta | None = None
    events: list[Event] = []
    for line_no, line in _iter_lines(text):
        s = line.strip()
        if not s:
            continue
        if s.startswith("#"):
            if s.startswith("# metric"):
                meta = _parse_metric_header(s, path, line_no)
            continue
        if meta is None:
            raise SourceError(f"{path}:{line_no}: metric data before header")
        parts = s.split()
        if len(parts) != 2:
            raise SourceError(f"{path}:{line_no}: metric line needs a timestamp and value")
        ts = _parse_ts(parts[0], path, line_no)
        try:
