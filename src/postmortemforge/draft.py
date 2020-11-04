"""The postmortem draft writer.

Every statement this module emits is a Claim that carries the exact source
span(s) it was derived from. A statement that cannot be grounded in at least one
source span is not written at all: the writer omits it rather than guessing. The
guarantee is enforced structurally, because a Claim cannot be constructed
without at least one Provenance, and the renderer only ever prints Claims.

The draft is line oriented so it diffs cleanly, and deterministic so identical
input produces byte-identical output.
"""

from __future__ import annotations

from dataclasses import dataclass

from .sources import Provenance
from .timeline import Timeline, iso_utc


class UngroundedStatement(ValueError):
    """Raised if code attempts to build a Claim with no source span."""


@dataclass(frozen=True)
class Claim:
