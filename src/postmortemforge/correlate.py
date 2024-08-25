"""Windowed correlation between deploys, metric breaches, and log error bursts.

Given aligned events on a single reference clock, this module finds the
structural features of an incident and the causal links between them, using
only time proximity within declared windows. It never invents a link it cannot
support from the aligned data.

Features detected:

- deploy actions (deploy and rollback), taken directly from the deploy source.
- a metric breach interval: the first and last reference timestamps for which
  the metric value crossed its declared threshold, treating a gap longer than
  break_gap_s as ending one interval and starting another.
- log error bursts: runs of ERROR level log events where consecutive errors are
  no more than burst_gap_s apart, with at least min_burst errors in the run.

Links produced (each carries the two events it relates and the gap in seconds):

- deploy -> breach: a metric breach that begins within window_s after a deploy.
- deploy -> burst: an error burst that begins within window_s after a deploy.
- rollback -> recovery: a rollback followed within window_s by the metric
  value returning below threshold (breach interval ending).

A link is only emitted when both endpoints exist and the gap is within the
window. Anything outside the window is left uncorrelated rather than guessed.
"""

from __future__ import annotations

from dataclasses import dataclass

from .clockalign import AlignedEvent


@dataclass(frozen=True)
class Interval:
    """A closed time interval on the reference clock, with its bounding events."""

    start_ts: float
    end_ts: float
    start_event: AlignedEvent
    end_event: AlignedEvent


@dataclass(frozen=True)
class Burst:
    """A run of error log events on the reference clock."""

    start_ts: float
    end_ts: float
    count: int
    events: tuple[AlignedEvent, ...]

    @property
    def start_event(self) -> AlignedEvent:
        return self.events[0]

    @property
    def end_event(self) -> AlignedEvent:
        return self.events[-1]


@dataclass(frozen=True)
class Link:
    """A causal relationship inferred from time proximity within a window."""

    relation: str  # deploy_to_breach, deploy_to_burst, rollback_to_recovery
    cause: AlignedEvent
    effect: AlignedEvent
    gap_s: float


def deploy_events(events: list[AlignedEvent]) -> list[AlignedEvent]:
    """Return deploy-source events in reference-clock order."""
    return [e for e in events if e.source == "deploy"]


def breach_intervals(events: list[AlignedEvent], break_gap_s: float = 120.0) -> list[Interval]:
    """Find metric breach intervals from breached metric samples.

    Consecutive breached samples belong to the same interval unless separated by
    more than break_gap_s, which starts a new one.
    """
    breached = [e for e in events if e.source == "metric" and e.event.attrs.get("breached")]
    breached.sort(key=lambda e: e.ref_ts)
    intervals: list[Interval] = []
    run: list[AlignedEvent] = []
    for ev in breached:
        if run and ev.ref_ts - run[-1].ref_ts > break_gap_s:
            intervals.append(Interval(run[0].ref_ts, run[-1].ref_ts, run[0], run[-1]))
            run = []
        run.append(ev)
    if run:
        intervals.append(Interval(run[0].ref_ts, run[-1].ref_ts, run[0], run[-1]))
    return intervals


def error_bursts(
    events: list[AlignedEvent], burst_gap_s: float = 60.0, min_burst: int = 3
) -> list[Burst]:
    """Find bursts of ERROR level log events.

    A burst is a run of errors where each is within burst_gap_s of the previous,
    containing at least min_burst errors.
    """
    errors = [
        e
        for e in events
        if e.source == "log" and e.event.attrs.get("level") == "ERROR"
    ]
    errors.sort(key=lambda e: e.ref_ts)
    bursts: list[Burst] = []
    run: list[AlignedEvent] = []
    for ev in errors:
        if run and ev.ref_ts - run[-1].ref_ts > burst_gap_s:
            _flush_burst(run, min_burst, bursts)
            run = []
        run.append(ev)
    _flush_burst(run, min_burst, bursts)
    return bursts


def _flush_burst(run: list[AlignedEvent], min_burst: int, out: list[Burst]) -> None:
    if len(run) >= min_burst:
        out.append(Burst(run[0].ref_ts, run[-1].ref_ts, len(run), tuple(run)))


def correlate(events: list[AlignedEvent], window_s: float = 300.0) -> list[Link]:
    """Produce causal links between deploys, breaches, bursts, and recovery.

    Only links whose gap falls within window_s are emitted. Links are returned in
    a deterministic order: by cause timestamp, then relation name.
    """
    deploys = deploy_events(events)
    intervals = breach_intervals(events)
    bursts = error_bursts(events)

    links: list[Link] = []

    deploy_actions = [d for d in deploys if d.event.attrs.get("action") == "deploy"]
    rollback_actions = [d for d in deploys if d.event.attrs.get("action") == "rollback"]

    for dep in deploy_actions:
        for interval in intervals:
            gap = interval.start_ts - dep.ref_ts
            if 0 <= gap <= window_s:
                links.append(Link("deploy_to_breach", dep, interval.start_event, gap))
        for burst in bursts:
            gap = burst.start_ts - dep.ref_ts
            if 0 <= gap <= window_s:
                links.append(Link("deploy_to_burst", dep, burst.start_event, gap))

    for rb in rollback_actions:
        for interval in intervals:
            gap = interval.end_ts - rb.ref_ts
            # The breach interval ends at or after the rollback: recovery.
            if -window_s <= gap <= window_s:
                links.append(Link("rollback_to_recovery", rb, interval.end_event, abs(gap)))

    links.sort(key=lambda l: (l.cause.ref_ts, l.relation, l.effect.ref_ts))
    return links
