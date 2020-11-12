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
    """A single postmortem statement and the source spans that ground it."""

    text: str
    sources: tuple[Provenance, ...]

    def __post_init__(self) -> None:
        if not self.sources:
            raise UngroundedStatement(f"claim has no source span: {self.text!r}")

    def render(self) -> str:
        cites = ", ".join(p.span() for p in self.sources)
        return f"- {self.text} [{cites}]"


@dataclass(frozen=True)
class Draft:
    """A postmortem draft: titled sections, each a list of grounded claims."""

    title: str
    sections: tuple[tuple[str, tuple[Claim, ...]], ...]

    def render(self) -> str:
        lines: list[str] = [f"# {self.title}", ""]
        for name, claims in self.sections:
            lines.append(f"## {name}")
            if not claims:
                lines.append("(no statement could be grounded in a source span)")
            for claim in claims:
                lines.append(claim.render())
            lines.append("")
        return "\n".join(lines).rstrip() + "\n"


def _prov(*aligned_events) -> tuple[Provenance, ...]:
    return tuple(ae.event.prov for ae in aligned_events)


def build_draft(timeline: Timeline) -> Draft:
    """Compose a postmortem draft from a timeline.

    Each claim is derived directly from concrete events or correlation links, and
    is annotated with the provenance of those events. Sections with no grounded
    claims render an explicit note rather than fabricated narrative.
    """
    summary: list[Claim] = []
    timeline_claims: list[Claim] = []
    cause_claims: list[Claim] = []
