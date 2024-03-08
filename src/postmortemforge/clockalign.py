"""Offset and skew correction to a declared reference clock.

Each source records time on its own clock. Before events from different sources
can be compared, they must be projected onto one reference timeline. We model
each source clock with a linear map:

    reference_ts = raw_ts + offset + skew * (raw_ts - anchor)

- offset is a constant shift in seconds (the source clock is ahead or behind).
- skew is a rate error in seconds per second (the source clock runs fast or
  slow). skew multiplies the elapsed time since a per-source anchor, so a small
  rate error accumulates over the window rather than applying uniformly.
- anchor is the raw_ts at which the source was last known to agree with the
  reference. Using an anchor keeps the correction numerically small and makes
  the offset the pure shift at the anchor instant.

The maps are declared, not inferred: this tool aligns against offsets an
operator provides (from NTP records, a known deploy marker, and so on). The
math is a plain affine transform, applied deterministically.
"""

from __future__ import annotations

from dataclasses import dataclass, replace

from .sources import Event


@dataclass(frozen=True)
class ClockModel:
    """Linear clock model for one source, relative to the reference clock."""

    source: str
    offset_s: float = 0.0
    skew_s_per_s: float = 0.0
    anchor_ts: float = 0.0

    def to_reference(self, raw_ts: float) -> float:
        """Project a raw source timestamp onto the reference timeline."""
        return raw_ts + self.offset_s + self.skew_s_per_s * (raw_ts - self.anchor_ts)


@dataclass(frozen=True)
class AlignedEvent:
    """An Event whose timestamp has been projected onto the reference clock.

    ref_ts is the reference-clock timestamp. source is the logical source name
    (logs, metric, deploy). event carries the original record, including its
    provenance and untouched raw_ts, so nothing observed is lost.
    """

    ref_ts: float
    source: str
    event: Event


def align(events: list[Event], model: ClockModel) -> list[AlignedEvent]:
    """Apply a clock model to every event from one source.

    Returns AlignedEvents sorted by reference timestamp, then by original line
    number for a stable, deterministic order when timestamps tie.
    """
    aligned = [
        AlignedEvent(ref_ts=model.to_reference(ev.raw_ts), source=model.source, event=ev)
        for ev in events
    ]
    aligned.sort(key=lambda a: (a.ref_ts, a.event.prov.line_start))
    return aligned


def merge(*groups: list[AlignedEvent]) -> list[AlignedEvent]:
    """Merge aligned events from several sources into one ordered stream.

    Ordering is by reference timestamp, then source name, then line number, so
    the merged stream is fully deterministic regardless of input order.
    """
    merged: list[AlignedEvent] = []
    for group in groups:
        merged.extend(group)
    merged.sort(key=lambda a: (a.ref_ts, a.source, a.event.prov.line_start))
    return merged


def with_anchor(model: ClockModel, anchor_ts: float) -> ClockModel:
    """Return a copy of the model anchored at anchor_ts."""
