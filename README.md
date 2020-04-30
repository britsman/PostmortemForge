<div align="center">

<img src="docs/assets/logo.svg" width="150"
     alt="PostmortemForge logo: a three lane timeline mark with one amber deploy dot above the wordmark PostmortemForge" />

# PostmortemForge

</div>

![Aligned incident timeline spanning 8.4 minutes across three horizontal lanes on a
shared minute axis. The top deploy lane marks the v2.4.1 deploy at minute 0 in amber
and the v2.4.0 rollback near minute 6. The middle metric lane plots fourteen
latency_p99_ms samples as a line from 210ms rising to a peak of 705ms and falling back
to 205ms, with the samples at or above the 470ms breach onset drawn in amber. The
bottom logs lane shows twelve events sized and coloured by severity, including a burst
of five amber ERROR entries. Three dashed connectors join the deploy to the first
breach sample, the deploy to the start of the error burst, and the rollback to the
recovery sample. A legend at the foot names INFO, WARN or rollback, and ERROR with
latency at or above the 470ms breach onset.](docs/assets/incident-timeline.svg)

<div align="center">

*The `timeline --svg` render of the bundled sample incident, drawn from the same
aligned data the CLI prints.*

</div>

PostmortemForge reconstructs an incident timeline from exported evidence and drafts a
postmortem in which every statement carries its source. It reads three offline exports
(application logs, a metric series, and a deploy record), aligns their clocks against a
declared reference using a per source offset and skew, correlates the events into a
timeline, and writes a draft where each line cites the exact source file and line span
it came from. A statement it cannot ground in a source span is left out rather than
guessed.

## Why timelines get argued about

The room agrees on almost nothing during an incident review. One engineer says the
deploy caused it; another points at a log line that arrived, on their screen, before
the deploy went out. Both are reading real timestamps. The disagreement is not about
honesty, it is about clocks. The log host was a little behind, the metric exporter was
a little ahead, and nobody wrote down by how much. So the same fifteen minutes look
different depending on which export you are staring at, and the postmortem inherits the
confusion.

The bundled sample is exactly this situation, made concrete. The log host runs 45
seconds behind the reference clock, and the metric exporter runs 90 seconds ahead and
drifts fast. On the raw exports, the first metric sample is stamped `08:01:30` and the
service start log is stamped `07:59:20`, so a naive merge orders them almost two minutes
apart from where they truly sit. Once aligned, the service start lands at `08:00:05`
and the first metric sample at `08:00:00`, and the story reads in the order it happened.

PostmortemForge takes the position that a postmortem is only as trustworthy as its
evidence, and makes that trust structural rather than aspirational. Every sentence in a
draft ends with a citation like `[samples/metric.txt:7]`, and any assertion that lacks a
grounding event never reaches the page. You can click through from any claim to the
line of the export it came from.

## Install

No third party dependencies. Python 3.11 or newer.

```
pip install -e .
```

You can also run it straight from the source tree without installing:

```
set PYTHONPATH=src
python -m postmortemforge version
```

That prints:

```
$ python -m postmortemforge version
postmortemforge 0.1.0
```

## Commands

Four subcommands, all reading the same three sources plus an alignment config.

| Command    | What it does                                                        | Exit on findings |
| ---------- | ------------------------------------------------------------------- | ---------------- |
| `ingest`   | List every event on the reference clock with its source span        | 1 if any events  |
| `timeline` | Build the correlated timeline: events plus the causal links found   | 1 if any links   |
| `timeline --svg <path>` | Write the same aligned timeline as an SVG instead of text | 1 if any links |
| `draft`    | Write the cited postmortem draft, one grounded claim per line       | 1 if any links   |
| `version`  | Print the version                                                   | always 0         |

`ingest`, `timeline`, and `draft` all take four required paths: `--logs`, `--metric`,
`--deploy`, and `--align`. `timeline` and `draft` also accept `--window <seconds>` for
the correlation window (default 300). Only `timeline` accepts `--svg <path>`.

## The three source kinds and their formats

Each source keeps time on its own clock and is read verbatim, with location. The reader
records what the file says; it does not correct or infer anything at read time.

| Kind     | Line format                                        | Header                                                              |
| -------- | -------------------------------------------------- | ------------------------------------------------------------------- |
| `logs`   | `<iso8601> <LEVEL> <message>`                      | none                                                                |
| `metric` | `<iso8601> <value>`                                | `# metric <name> unit=<u> threshold=<t> direction=<above\|below>`   |
| `deploy` | `<iso8601> <deploy\|rollback> ref=<ref>`           | none                                                                |

Rules that hold across all three:

- Timestamps must be ISO8601 UTC, with a trailing `Z` or an explicit `+00:00`. Anything
  else is rejected with a `SourceError` rather than guessed.
- Blank lines and lines starting with `#` are skipped (the metric header is the one `#`
  line that carries meaning).
- Every event records its provenance: the source path and a 1-based inclusive line span,
  rendered as `path:line` or `path:start-end`.

The metric reader models a single scalar series with one threshold and one direction. On
each data point it records the value and whether it breached, so correlation can later
find the breach window without re-reading the file.

## Clock alignment

Before events from different sources can be compared, they must be projected onto one
reference clock. Each source clock is modelled as a linear map:

```
reference_ts = raw_ts + offset + skew * (raw_ts - anchor)
```

- `offset` is a constant shift in seconds: the source clock is ahead or behind.
- `skew` is a rate error in seconds per second: the source clock runs fast or slow. It
  multiplies the elapsed time since a per source `anchor`, so a small rate error
  accumulates over the window instead of applying uniformly.
- `anchor` is the raw timestamp at which the source was last known to agree with the
  reference. Anchoring keeps the correction numerically small and makes the offset the
  pure shift at the anchor instant. `anchor=first` anchors at the source's own earliest
  raw sample.

The maps are declared, not inferred. PostmortemForge applies the offsets an operator
provides (from NTP records, a known deploy marker, and so on); it does not estimate them
from the data. The sample `align.txt` declares:

```
deploy offset=0 skew=0 anchor=first
log offset=45 skew=0 anchor=first
metric offset=-90 skew=0.02 anchor=first
```

So in the sample the deploy record is the reference, the log host runs 45 seconds behind
(add 45), and the metric exporter runs 90 seconds ahead (subtract 90) while drifting fast
at 0.02 seconds per second, anchored at its first sample.

The skew is not decorative. The test `TestSampleAlignment` projects a real metric sample
to prove the accumulated drift. The metric anchor is its first sample at raw `08:01:30`.
Line 15 of `metric.txt` is stamped raw `08:05:00`, which is 300 seconds after the anchor,
so the skew adds `0.02 * 300 = 6` seconds:

```
ref = raw - 90 + 6 = 08:05:00 - 90 + 6 = 08:05:06Z
```

That projected time, `2026-03-01T08:05:06Z`, is asserted exactly in the test and appears
verbatim in the `ingest` output below for `samples/metric.txt:15`. At the anchor itself
only the offset applies, so the first metric sample projects to `08:00:00Z`, and the log
host's first line (raw `07:59:20`) projects to `08:00:05Z`.

`ingest` reads all three sources and lists every event on the reference clock with its
source span. This is the captured output from the sample fixtures:

```
$ python -m postmortemforge ingest --logs samples/logs.txt --metric samples/metric.txt --deploy samples/deploy.txt --align samples/align.txt
2026-03-01T08:00:00Z  deploy   samples/deploy.txt:3  deploy v2.4.1
2026-03-01T08:00:00Z  metric   samples/metric.txt:5  latency_p99_ms=210ms
2026-03-01T08:00:05Z  log      samples/logs.txt:4    service started build=v2.4.1
2026-03-01T08:00:30Z  metric   samples/metric.txt:6  latency_p99_ms=235ms
2026-03-01T08:01:01Z  metric   samples/metric.txt:7  latency_p99_ms=470ms
2026-03-01T08:01:20Z  log      samples/logs.txt:5    config reloaded
2026-03-01T08:01:31Z  metric   samples/metric.txt:8  latency_p99_ms=610ms
2026-03-01T08:02:02Z  metric   samples/metric.txt:9  latency_p99_ms=655ms
2026-03-01T08:02:05Z  log      samples/logs.txt:6    upstream latency rising pool=checkout
2026-03-01T08:02:33Z  metric   samples/metric.txt:10  latency_p99_ms=640ms
2026-03-01T08:02:35Z  log      samples/logs.txt:7    upstream timeout pool=checkout after=2000ms
2026-03-01T08:02:50Z  log      samples/logs.txt:8    upstream timeout pool=checkout after=2000ms
2026-03-01T08:03:03Z  metric   samples/metric.txt:11  latency_p99_ms=690ms
2026-03-01T08:03:20Z  log      samples/logs.txt:9    circuit open pool=checkout
2026-03-01T08:03:34Z  metric   samples/metric.txt:12  latency_p99_ms=705ms
2026-03-01T08:03:50Z  log      samples/logs.txt:10   upstream timeout pool=checkout after=2000ms
2026-03-01T08:04:04Z  metric   samples/metric.txt:13  latency_p99_ms=660ms
2026-03-01T08:04:25Z  log      samples/logs.txt:11   circuit open pool=checkout
2026-03-01T08:04:35Z  metric   samples/metric.txt:14  latency_p99_ms=620ms
2026-03-01T08:05:06Z  metric   samples/metric.txt:15  latency_p99_ms=540ms
2026-03-01T08:05:36Z  metric   samples/metric.txt:16  latency_p99_ms=470ms
2026-03-01T08:06:00Z  deploy   samples/deploy.txt:4  rollback v2.4.0
2026-03-01T08:06:00Z  log      samples/logs.txt:12   retries elevated pool=checkout
2026-03-01T08:06:07Z  metric   samples/metric.txt:17  latency_p99_ms=250ms
2026-03-01T08:06:37Z  metric   samples/metric.txt:18  latency_p99_ms=205ms
2026-03-01T08:07:05Z  log      samples/logs.txt:13   rollback signal received target=v2.4.0
2026-03-01T08:07:55Z  log      samples/logs.txt:14   circuit closed pool=checkout
2026-03-01T08:08:25Z  log      samples/logs.txt:15   request served status=200
```

Note `samples/metric.txt:15` projecting to `08:05:06Z`, matching the skew calculation
above.

## Correlation windows and the links found in the sample

With every event on one clock, correlation looks for the structural features of an
incident and the links between them, using only time proximity within declared windows.
It detects three kinds of feature:

- deploy actions, taken directly from the deploy source.
- a metric breach interval: the first and last reference timestamps for which the metric
  crossed its threshold, treating a gap longer than 120 seconds as ending one interval.
- log error bursts: runs of ERROR level events no more than 60 seconds apart, with at
  least three errors in the run.

From those it produces links, each carrying the two events it relates and the gap in
seconds. A link is only emitted when both endpoints exist and the gap falls within the
window (default 300 seconds). Anything outside the window is left uncorrelated rather
than guessed.

`timeline` builds the correlated timeline and prints events plus the links it found.
Captured output, links section shown in full:

```
$ python -m postmortemforge timeline --logs samples/logs.txt --metric samples/metric.txt --deploy samples/deploy.txt --align samples/align.txt
EVENTS
  T+   0.0m  deploy   samples/deploy.txt:3  deploy v2.4.1
  T+   0.0m  metric   samples/metric.txt:5  latency_p99_ms=210ms
  T+   0.1m  log      samples/logs.txt:4    service started build=v2.4.1
  ... (28 events in full; middle elided here only for length)
  T+   8.4m  log      samples/logs.txt:15   request served status=200
LINKS
  deploy_to_breach        T+0.0m -> T+1.0m  gap=61s  [samples/deploy.txt:3 -> samples/metric.txt:7]
  deploy_to_burst         T+0.0m -> T+2.6m  gap=155s  [samples/deploy.txt:3 -> samples/logs.txt:7]
  rollback_to_recovery    T+6.0m -> T+5.6m  gap=23s  [samples/deploy.txt:4 -> samples/metric.txt:16]
```

The three links, with the real gaps the tool measured:

| Relation               | From                | To                   | Gap   | What it means                                                     |
| ---------------------- | ------------------- | -------------------- | ----- | ----------------------------------------------------------------- |
| `deploy_to_breach`     | deploy v2.4.1       | first breach sample  | 61s   | The metric crossed 400ms 61s after the deploy.                    |
| `deploy_to_burst`      | deploy v2.4.1       | first ERROR log      | 155s  | The error burst began 155s after the deploy.                      |
| `rollback_to_recovery` | rollback v2.4.0     | last breach sample   | 23s   | The metric dropped below threshold within 23s of the rollback.    |

The `rollback_to_recovery` arrow points backward in minutes (`T+6.0m -> T+5.6m`) because
the last breached sample is at T+5.6, just before the rollback at T+6.0; the gap is the
absolute distance, 23 seconds. The correlator allows the recovery endpoint to fall
either side of the rollback within the window, which is why a breach ending slightly
before the rollback still counts as the recovery it enabled.

## Grounded claims

The draft writer emits only `Claim` objects, and a `Claim` cannot be constructed without
at least one `Provenance`. The guarantee is enforced in the type's `__post_init__`:

```python
def __post_init__(self) -> None:
    if not self.sources:
        raise UngroundedStatement(f"claim has no source span: {self.text!r}")
```

Because the renderer only ever prints `Claim`s, and a `Claim` cannot exist without a
source span, no ungrounded sentence can reach the page. There is no code path that
formats a bare string into the draft body. This is verified two ways in the tests:
`test_claim_requires_a_source` asserts that building `Claim("...", tuple())` raises
`UngroundedStatement`, and `test_every_rendered_claim_line_has_a_citation` asserts every
`- ` line in a real rendered draft contains a `[path:line]` citation.

What this guarantees about the draft: if a claim would require a fact the evidence does
not contain, the writer omits it rather than hedging it. A section with no grounded
claims renders the explicit note `(no statement could be grounded in a source span)`
instead of narrative. You never read a sentence you cannot trace.

## A worked run producing the draft

`draft` writes the cited postmortem. This is the full captured output from the sample
fixtures, verbatim:

```
$ python -m postmortemforge draft --logs samples/logs.txt --metric samples/metric.txt --deploy samples/deploy.txt --align samples/align.txt
# Incident postmortem draft

## Summary
- A deploy of v2.4.1 occurred at T+0.0 min. [samples/deploy.txt:3]
- A rollback to v2.4.0 occurred at T+6.0 min. [samples/deploy.txt:4]
- latency_p99_ms stayed past its threshold of 400ms from T+1.0 to T+5.6 min. [samples/metric.txt:7, samples/metric.txt:16]
- A burst of 5 error log lines ran from T+2.6 to T+4.4 min. [samples/logs.txt:7, samples/logs.txt:11]

## Timeline
- T+0.0 min (2026-03-01T08:00:00Z) deploy: deploy v2.4.1 [samples/deploy.txt:3]
- T+0.0 min (2026-03-01T08:00:00Z) metric: latency_p99_ms=210ms [samples/metric.txt:5]
- T+0.1 min (2026-03-01T08:00:05Z) log: service started build=v2.4.1 [samples/logs.txt:4]
- ... (one cited line per event, 28 in all; elided here for length)
- T+8.4 min (2026-03-01T08:08:25Z) log: request served status=200 [samples/logs.txt:15]

## Contributing cause
- The deploy of v2.4.1 was followed 61 s later by latency_p99_ms crossing its threshold. [samples/deploy.txt:3, samples/metric.txt:7]
- The deploy of v2.4.1 was followed 155 s later by the start of an error burst. [samples/deploy.txt:3, samples/logs.txt:7]

## Resolution
- The rollback to v2.4.0 was associated with the metric returning below threshold within 23 s. [samples/deploy.txt:4, samples/metric.txt:16]
```

The Timeline section prints one cited line for every one of the 28 events; the middle is
elided above only to keep the README short. The full output is what the command prints.

Follow one fact from input to draft. The Summary line `A burst of 5 error log lines ran
from T+2.6 to T+4.4 min. [samples/logs.txt:7, samples/logs.txt:11]` traces back like
this: `read_logs` parsed five lines with level `ERROR` (lines 7 to 11 of `logs.txt`),
each carrying its own provenance. `clockalign` projected them 45 seconds forward onto
the reference clock. `error_bursts` grouped them into one run of five because each was
within 60 seconds of the last. `build_draft` bounded the burst by its first and last
error and cited exactly those two spans. Nothing in that chain was invented; every step
either read a file or applied the declared offset.

## Reading the timeline asset

The hero image at the top of this page is the `timeline --svg` render of the sample
incident. It is worth reading closely, because colour and size carry meaning rather than
decoration. It shows:

- Three lanes on a shared minute axis measured from the first event: deploy on top,
  metric in the middle, logs at the foot.
- The metric lane plots fourteen latency samples as a line from 210ms up to a labelled
  peak of 705ms and back down to 205ms.
- Amber marks the incident itself: the v2.4.1 deploy dot, every latency sample at or
  above the 470ms breach onset, and the five ERROR log events.
- Teal marks healthy signal, with hollow teal rings for the WARN log lines and the
  rollback.
- Three dashed connectors trace the recorded correlations: deploy to first breach,
  deploy to error burst start, and rollback to recovery.
- A legend at the foot names each mark: INFO, WARN or rollback, and ERROR with latency
  at or above the 470ms breach onset.

Regenerate it at any time with:

```
python -m postmortemforge timeline --logs samples/logs.txt --metric samples/metric.txt --deploy samples/deploy.txt --align samples/align.txt --svg docs/assets/incident-timeline.svg
```

## Output format

The `draft` output is a contract. Each section is a Markdown `##` heading followed by
grounded claim lines, and each claim line has this shape:

```
- <statement text> [<span>, <span>, ...]
```

| Section              | One line per                                  | Grounded in                                      |
