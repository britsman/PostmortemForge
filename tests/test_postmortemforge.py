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


class TestSources(unittest.TestCase):
    def test_logs_carry_line_provenance(self):
        text = "2026-03-01T08:00:00Z INFO hello\n2026-03-01T08:00:01Z ERROR boom\n"
        events = S.read_logs(text, "logs.txt")
        self.assertEqual(len(events), 2)
        self.assertEqual(events[0].prov, Provenance("logs.txt", 1, 1))
        self.assertEqual(events[1].attrs["level"], "ERROR")
        self.assertEqual(events[1].prov.span(), "logs.txt:2")

    def test_metric_header_and_breach_flag(self):
