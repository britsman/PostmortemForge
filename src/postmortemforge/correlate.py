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

