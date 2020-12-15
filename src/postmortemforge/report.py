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
    return "\n".join(lines) + "\n"


# --- SVG rendering -----------------------------------------------------------

# Palette reason is documented in the SVG comment. Two core colours plus one
# accent, derived from the incident domain: a calm slate for structure, a steady
# teal for healthy signal, and a single amber accent marking the deploy that
# started the incident, the one thing to look at first.
_INK = "#1f2933"
_MUTED = "#52606d"
_LANE_BG = "#eef2f5"
_TEAL = "#0f7d74"
_AMBER = "#b06a00"
_GRID = "#cbd2d9"
_WHITE = "#ffffff"

_LANES = ("deploy", "metric", "log")
_LANE_LABEL = {"deploy": "deploy", "metric": "metric", "log": "logs"}


def _x_for_minute(minute: float, span_m: float, left: float, width: float) -> float:
    if span_m <= 0:
        return left
    return left + (minute / span_m) * width


def render_svg(timeline: Timeline) -> str:
    """Draw the aligned timeline as an information graphic.

    Layout: a horizontal minute axis, three source lanes stacked vertically, one
    marker per event positioned by its minute offset, and connector lines for the
    correlation links. All coordinates land on whole or half pixels.
    """
    left = 96.0
    right_pad = 24.0
    top = 72.0
    lane_h = 64.0
    lane_gap = 8.0
    plot_w = 640.0
    width = left + plot_w + right_pad
    n_lanes = len(_LANES)
    height = top + n_lanes * lane_h + (n_lanes - 1) * lane_gap + 72.0

    span_m = timeline.span_minutes()
    if span_m <= 0:
        span_m = 1.0

    lane_y = {}
    for i, lane in enumerate(_LANES):
        lane_y[lane] = top + i * (lane_h + lane_gap)

