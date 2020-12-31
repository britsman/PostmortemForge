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

    parts: list[str] = []
    parts.append(f'<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {width:g} {height:g}" role="img" aria-labelledby="ttl dsc">')
    parts.append(
        "<!-- Palette reason: incident timeline. Slate ink for structure, teal for "
        "healthy metric signal, one amber accent on the deploy that began the "
        "incident, the first thing to read. Flat fills, no gradients. -->"
    )
    parts.append(f'<title id="ttl">Aligned incident timeline, {span_m:0.1f} minutes across three sources</title>')
    parts.append(
        '<desc id="dsc">Three horizontal lanes, deploy, metric, and logs, share a '
        'minute axis measured from the first event. Markers show each event, and '
        'connectors show correlated deploy, breach, and rollback relationships.</desc>'
    )
    parts.append(f'<rect x="0" y="0" width="{width:g}" height="{height:g}" fill="{_WHITE}"/>')

    # Title text.
    parts.append(
        f'<text x="{left:g}" y="36" font-family="-apple-system, &quot;Segoe UI&quot;, Roboto, Helvetica, Arial, sans-serif" '
        f'font-size="17" font-weight="600" fill="{_INK}">Aligned incident timeline</text>'
    )
    parts.append(
        f'<text x="{left:g}" y="56" font-family="-apple-system, &quot;Segoe UI&quot;, Roboto, Helvetica, Arial, sans-serif" '
        f'font-size="12" fill="{_MUTED}">minutes from first event, reference clock</text>'
    )

    # Lane backgrounds and labels.
    for lane in _LANES:
        y = lane_y[lane]
        parts.append(
            f'<rect x="{left:g}" y="{y:g}" width="{plot_w:g}" height="{lane_h:g}" '
            f'rx="3" fill="{_LANE_BG}"/>'
        )
        parts.append(
            f'<text x="{left - 12:g}" y="{y + lane_h / 2 + 4:g}" text-anchor="end" '
            f'font-family="&quot;Cascadia Mono&quot;, &quot;JetBrains Mono&quot;, Consolas, &quot;DejaVu Sans Mono&quot;, monospace" '
            f'font-size="12" fill="{_INK}">{escape(_LANE_LABEL[lane])}</text>'
        )

    # Minute axis: ticks at whole minutes across the span.
    axis_y = top + n_lanes * lane_h + (n_lanes - 1) * lane_gap + 20.0
    tick_step = _tick_step(span_m)
    parts.append(
        f'<line x1="{left:g}" y1="{axis_y:g}" x2="{left + plot_w:g}" y2="{axis_y:g}" '
        f'stroke="{_MUTED}" stroke-width="1"/>'
    )
    m = 0.0
    while m <= span_m + 1e-9:
        x = _x_for_minute(m, span_m, left, plot_w)
        x = round(x * 2) / 2
        parts.append(
            f'<line x1="{x:g}" y1="{top:g}" x2="{x:g}" y2="{axis_y:g}" '
            f'stroke="{_GRID}" stroke-width="1"/>'
