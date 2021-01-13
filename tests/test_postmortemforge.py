"""Tests for postmortemforge.

These assert the clock alignment math against known offsets and skew, the
provenance carried through every layer, the correlation links, and the grounding
guarantee that a draft claim cannot exist without a source span.
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.join(os.path.dirname(__file__), os.pardir, "src"))

from postmortemforge import sources as S
from postmortemforge.clockalign import ClockModel, align, merge, with_anchor
from postmortemforge.correlate import breach_intervals, correlate, error_bursts
from postmortemforge.draft import Claim, UngroundedStatement, build_draft
from postmortemforge.sources import Provenance
from postmortemforge.timeline import build, iso_utc

SAMPLES = os.path.join(os.path.dirname(__file__), os.pardir, "samples")


def _sample(name):
    return os.path.join(SAMPLES, name)


