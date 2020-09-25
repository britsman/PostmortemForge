"""Offset and skew correction to a declared reference clock.

Each source records time on its own clock. Before events from different sources
can be compared, they must be projected onto one reference timeline. We model
each source clock with a linear map:

    reference_ts = raw_ts + offset + skew * (raw_ts - anchor)

- offset is a constant shift in seconds (the source clock is ahead or behind).
- skew is a rate error in seconds per second (the source clock runs fast or
  slow). skew multiplies the elapsed time since a per-source anchor, so a small
  rate error accumulates over the window rather than applying uniformly.
- anchor is the raw_ts at which the source was last known to agree with the
  reference. Using an anchor keeps the correction numerically small and makes
  the offset the pure shift at the anchor instant.

The maps are declared, not inferred: this tool aligns against offsets an
operator provides (from NTP records, a known deploy marker, and so on). The
