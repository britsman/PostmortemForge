# Security Policy

## Supported versions

| Version | Supported |
|---------|-----------|
| 0.6.x   | yes       |
| < 0.6   | no        |

## Reporting a vulnerability

PostmortemForge runs offline on log files you already have, so attack surface
is small but real:

- path traversal via log filenames in timeline generation,
- crash / OOM on adversarial log formats (quadratic regexes, unbounded reads),
- markdown injection: incident text rendered into the report must be escaped
  so a crafted log line cannot smuggle HTML into the rendered page.

Please do **not** open a public issue for the above. Contact the repository
owner through the profile with:

1. The affected version (`postmortemforge --version` or the commit SHA).
2. The smallest synthetic sample that triggers the behaviour.
3. Expected vs. actual behaviour.

You will get an acknowledgement within a week. Fixes land in the next minor
release and the reporter is credited in the changelog unless they prefer
otherwise.

## Scope

- `parsers/` - untrusted input, primary focus.
- `timeline/` - alignment and merge logic.
- `render/` - escaping of log-derived strings in output documents.
