# Sample fixtures

These files are hand authored test vectors, not captured production telemetry.
They describe one coherent incident so the readers, clock alignment, correlation,
and draft writer can be exercised end to end and asserted in tests.

## The incident

On the reference clock:

- T+0.0 min: a deploy of v2.4.1.
- T+1.0 min: the latency_p99_ms metric crosses its 400 ms threshold.
- T+2.6 min: an error burst begins in the application logs.
- T+6.0 min: a rollback to v2.4.0.
- shortly after: the metric returns below threshold and the errors stop.

## The three clocks

Each source is written on its own clock, and the timestamps in the files are the
raw, unaligned values. The alignment config, `align.txt`, declares how each
projects onto the reference clock:

