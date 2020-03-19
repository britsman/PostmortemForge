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

