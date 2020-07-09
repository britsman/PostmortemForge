"""Command line interface for postmortemforge.

Subcommands:

  ingest    Read the three sources, align clocks, list every event with its
            reference time and source span.
  timeline  Build the correlated timeline and print events plus causal links.
  draft     Write the postmortem draft, every statement cited to a source span.
  version   Print the version.

Clock models are declared in a small alignment config (see samples/align.txt):
one line per source, `<source> offset=<s> skew=<s_per_s> anchor=<iso8601|first>`.
The reference clock is whatever these offsets project onto; a source with
offset 0 and skew 0 already agrees with the reference.

Exit codes: 0 clean, 1 findings present (a draft with correlated links or an
ingest that produced events), 2 usage error.
"""

from __future__ import annotations

import argparse
import sys

from . import __version__
from . import sources as S
from .clockalign import ClockModel, align, merge, with_anchor
from .draft import build_draft
from .report import render_ingest, render_svg, render_timeline
from .timeline import build

USAGE_ERROR = 2
FINDINGS = 1
CLEAN = 0


def _parse_align_config(text: str, path: str) -> dict[str, ClockModel]:
    """Parse the alignment config into per-source clock models.

    Lines: `<source> offset=<s> skew=<s_per_s> anchor=<iso8601|first>`.
    anchor=first means anchor at the source's own earliest raw timestamp, filled
    in later once events are read.
    """
    models: dict[str, ClockModel] = {}
    for line_no, line in enumerate(text.splitlines(), start=1):
        s = line.strip()
        if not s or s.startswith("#"):
            continue
        parts = s.split()
        source = parts[0]
        offset = 0.0
        skew = 0.0
        anchor_raw = "first"
        for tok in parts[1:]:
            if "=" not in tok:
                raise S.SourceError(f"{path}:{line_no}: field {tok!r} needs key=value")
            key, val = tok.split("=", 1)
            if key == "offset":
                offset = float(val)
            elif key == "skew":
                skew = float(val)
            elif key == "anchor":
                anchor_raw = val
            else:
                raise S.SourceError(f"{path}:{line_no}: unknown field {key!r}")
        anchor_ts = 0.0
        if anchor_raw != "first":
            anchor_ts = S._parse_ts(anchor_raw, path, line_no)
        models[source] = ClockModel(
            source=source, offset_s=offset, skew_s_per_s=skew, anchor_ts=anchor_ts
        )
        # Stash whether anchor was "first" so we can fill it after reading.
        if anchor_raw == "first":
            _ANCHOR_FIRST.add((path, source))
    return models


_ANCHOR_FIRST: set[tuple[str, str]] = set()


def _load(args) -> list:
    """Read all three sources and project them onto the reference clock."""
    align_text = S.read_file(args.align)
    _ANCHOR_FIRST.clear()
    models = _parse_align_config(align_text, args.align)

    log_events = S.read_logs(S.read_file(args.logs), args.logs)
    _, metric_events = S.read_metric(S.read_file(args.metric), args.metric)
    deploy_events = S.read_deploy(S.read_file(args.deploy), args.deploy)

    groups = []
    for source, events in (
        ("log", log_events),
        ("metric", metric_events),
        ("deploy", deploy_events),
    ):
        model = models.get(source, ClockModel(source=source))
        if (args.align, source) in _ANCHOR_FIRST and events:
            earliest = min(e.raw_ts for e in events)
            model = with_anchor(model, earliest)
        groups.append(align(events, model))
    return merge(*groups)


def _add_source_args(p: argparse.ArgumentParser) -> None:
    p.add_argument("--logs", required=True, help="path to the application log export")
    p.add_argument("--metric", required=True, help="path to the metric series export")
    p.add_argument("--deploy", required=True, help="path to the deploy record export")
    p.add_argument("--align", required=True, help="path to the clock alignment config")


def _cmd_ingest(args) -> int:
    aligned = _load(args)
    sys.stdout.write(render_ingest(aligned))
    return FINDINGS if aligned else CLEAN


def _cmd_timeline(args) -> int:
    aligned = _load(args)
    tl = build(aligned, window_s=args.window)
    if args.svg:
        with open(args.svg, "w", encoding="utf-8", newline="\n") as fh:
            fh.write(render_svg(tl))
        sys.stdout.write(f"wrote {args.svg}\n")
    else:
        sys.stdout.write(render_timeline(tl))
    return FINDINGS if tl.links else CLEAN


def _cmd_draft(args) -> int:
    aligned = _load(args)
    tl = build(aligned, window_s=args.window)
    draft = build_draft(tl)
    sys.stdout.write(draft.render())
    return FINDINGS if tl.links else CLEAN


def _cmd_version(args) -> int:
    sys.stdout.write(f"postmortemforge {__version__}\n")
    return CLEAN


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="postmortemforge",
        description="Reconstruct an incident timeline from exported evidence and draft a cited postmortem.",
    )
    sub = parser.add_subparsers(dest="command", required=True)

    p_ingest = sub.add_parser("ingest", help="list aligned events with source spans")
    _add_source_args(p_ingest)
    p_ingest.set_defaults(func=_cmd_ingest)

    p_timeline = sub.add_parser("timeline", help="build the correlated timeline")
    _add_source_args(p_timeline)
    p_timeline.add_argument("--window", type=float, default=300.0, help="correlation window in seconds")
    p_timeline.add_argument("--svg", help="write the timeline SVG to this path instead of text")
    p_timeline.set_defaults(func=_cmd_timeline)

    p_draft = sub.add_parser("draft", help="write the cited postmortem draft")
