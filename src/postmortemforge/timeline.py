"""The ordered timeline model.

A Timeline is the aligned, merged event stream plus the correlation features and
links found over it. It is the single structure the draft writer and the report
renderer read from, so the incident is described once and consumed many ways.

Time is presented as minutes elapsed from the first event, which is the natural
axis for a postmortem and keeps the diagram and the prose using the same units.
"""

from __future__ import annotations

import datetime as _dt
from dataclasses import dataclass

from .clockalign import AlignedEvent
from .correlate import Burst, Interval, Link, breach_intervals, correlate, error_bursts


@dataclass(frozen=True)
class Timeline:
    """The full incident model on the reference clock."""

    events: tuple[AlignedEvent, ...]
    links: tuple[Link, ...]
    intervals: tuple[Interval, ...]
    bursts: tuple[Burst, ...]

    @property
    def origin_ts(self) -> float:
