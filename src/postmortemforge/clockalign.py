"""Offset and skew correction to a declared reference clock.

Each source records time on its own clock. Before events from different sources
can be compared, they must be projected onto one reference timeline. We model
each source clock with a linear map:

    reference_ts = raw_ts + offset + skew * (raw_ts - anchor)

