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

