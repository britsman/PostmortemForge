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

- `deploy.txt` is the reference clock: offset 0, skew 0.
- `logs.txt` runs 45 seconds behind the reference: offset +45.
- `metric.txt` runs 90 seconds ahead of the reference and drifts fast at
  0.02 seconds per second, anchored at its first sample: offset -90, skew 0.02.

The offsets are deliberate so the alignment code is genuinely required. The test
`TestSampleAlignment` asserts the projected reference times, including the
accumulated skew on a metric sample 300 seconds past the anchor.

## Formats

- logs: `<iso8601> <LEVEL> <message>`
- metric: a `# metric <name> unit=<u> threshold=<t> direction=<above|below>`
  header, then `<iso8601> <value>` per line
- deploy: `<iso8601> <deploy|rollback> ref=<ref>`

# draft note 114
