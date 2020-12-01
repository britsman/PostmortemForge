"""Line oriented renderers for ingest listings, the timeline, and the SVG.

Text renderers produce deterministic, diff friendly output. The SVG renderer
draws the aligned timeline the CLI computed, with a minute axis, real event
labels, and the three sources on separate lanes. Every number in the SVG comes
from the timeline that was actually built from the sample inputs.
"""

from __future__ import annotations

from xml.sax.saxutils import escape

from .clockalign import AlignedEvent
from .timeline import Timeline, iso_utc


def render_ingest(events: list[AlignedEvent]) -> str:
    """List every aligned event with its reference time and source span.

    Columns: reference ISO time, source, provenance span, label. This is the
    proof that reading and alignment happened, one event per line.
    """
    lines: list[str] = []
    for ae in events:
        lines.append(
            f"{iso_utc(ae.ref_ts)}  {ae.source:<7}  {ae.event.prov.span():<20}  {ae.event.text}"
        )
    return "\n".join(lines) + "\n"


def render_timeline(timeline: Timeline) -> str:
