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
    """Render the timeline as minute-stamped lines plus the correlation links."""
    lines: list[str] = ["EVENTS"]
    for ae in timeline.events:
        mins = timeline.minutes(ae.ref_ts)
        lines.append(
            f"  T+{mins:6.1f}m  {ae.source:<7}  {ae.event.prov.span():<20}  {ae.event.text}"
        )
    lines.append("LINKS")
    if not timeline.links:
        lines.append("  (none)")
    for link in timeline.links:
        cm = timeline.minutes(link.cause.ref_ts)
        em = timeline.minutes(link.effect.ref_ts)
        lines.append(
            f"  {link.relation:<22}  T+{cm:0.1f}m -> T+{em:0.1f}m  gap={link.gap_s:0.0f}s"
            f"  [{link.cause.event.prov.span()} -> {link.effect.event.prov.span()}]"
        )
