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
        text = (
            "# metric latency_p99_ms unit=ms threshold=400 direction=above\n"
            "2026-03-01T08:00:00Z 100\n"
            "2026-03-01T08:00:30Z 500\n"
        )
        meta, events = S.read_metric(text, "metric.txt")
        self.assertEqual(meta.name, "latency_p99_ms")
        self.assertEqual(meta.threshold, 400.0)
        self.assertFalse(events[0].attrs["breached"])
        self.assertTrue(events[1].attrs["breached"])
        self.assertEqual(events[1].prov.line_start, 3)

    def test_deploy_actions(self):
        text = "2026-03-01T08:00:00Z deploy ref=v1\n2026-03-01T08:05:00Z rollback ref=v0\n"
        events = S.read_deploy(text, "deploy.txt")
        self.assertEqual(events[0].attrs["action"], "deploy")
        self.assertEqual(events[0].attrs["ref"], "v1")
        self.assertEqual(events[1].attrs["action"], "rollback")

    def test_bad_timestamp_raises(self):
        with self.assertRaises(S.SourceError):
            S.read_logs("not-a-time INFO x\n", "logs.txt")

    def test_bad_direction_raises(self):
        with self.assertRaises(S.SourceError):
            S.read_metric("# metric m unit=ms threshold=1 direction=sideways\n", "m.txt")


class TestClockAlign(unittest.TestCase):
    def test_offset_only(self):
        raw = S._parse_ts("2026-03-01T08:00:00Z", "x", 1)
        model = ClockModel("log", offset_s=45.0, skew_s_per_s=0.0, anchor_ts=raw)
        self.assertAlmostEqual(model.to_reference(raw), raw + 45.0)

    def test_skew_accumulates_from_anchor(self):
        anchor = S._parse_ts("2026-03-01T08:00:00Z", "x", 1)
        later = anchor + 600.0  # ten minutes past the anchor
        model = ClockModel("metric", offset_s=-90.0, skew_s_per_s=0.02, anchor_ts=anchor)
        # At the anchor, only the offset applies.
        self.assertAlmostEqual(model.to_reference(anchor), anchor - 90.0)
        # Ten minutes later, skew has added 0.02 * 600 = 12 seconds.
