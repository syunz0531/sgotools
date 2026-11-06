"""A record of every choice made while assembling a dataset.

Published analyses of the SGO data differ in how many crashes they count,
largely because each author applies a different set of defensible filters and
describes them in prose, if at all. :class:`Provenance` records the options
actually used and the rows each step removed, and renders them as a sentence
that can be pasted into a methods section.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Optional


@dataclass
class Step:
    """One filtering or transformation step."""

    name: str
    description: str
    rows_before: int
    rows_after: int

    @property
    def removed(self) -> int:
        return self.rows_before - self.rows_after


@dataclass
class Provenance:
    """Options and row counts for one :func:`~sgotools.load_incidents` call."""

    snapshot_path: Optional[str] = None
    snapshot_retrieved: Optional[str] = None
    digests: dict[str, str] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)
    steps: list[Step] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def record(self, name: str, description: str, before: int, after: int) -> None:
        self.steps.append(Step(name, description, before, after))

    @property
    def rows_in(self) -> int:
        return self.steps[0].rows_before if self.steps else 0

    @property
    def rows_out(self) -> int:
        return self.steps[-1].rows_after if self.steps else 0

    def summary(self) -> str:
        """Multi-line report of the options, each step and any warnings."""
        lines = ["sgotools provenance", "=" * 19]
        if self.snapshot_path:
            lines.append(f"snapshot: {self.snapshot_path}")
        if self.snapshot_retrieved:
            lines.append(f"retrieved: {self.snapshot_retrieved}")
        for name, digest in sorted(self.digests.items()):
            lines.append(f"  sha256[{name}] = {digest}")
        lines.append("")
        lines.append("options:")
        for key, value in self.options.items():
            lines.append(f"  {key} = {value!r}")
        lines.append("")
        lines.append("steps:")
        for step in self.steps:
            lines.append(
                f"  {step.name:22s} {step.rows_before:7,d} -> {step.rows_after:7,d}"
                f"  (-{step.removed:,d})  {step.description}"
            )
        if self.warnings:
            lines.append("")
            lines.append("warnings:")
            lines.extend(f"  - {w}" for w in self.warnings)
        return "\n".join(lines)

    def methods_sentence(self) -> str:
        """A citable description of how the dataset was assembled."""
        opts = self.options
        parts = [
            "Crash records were taken from the NHTSA Standing General Order "
            "incident report files"
        ]
        if self.snapshot_retrieved:
            parts.append(f", retrieved {self.snapshot_retrieved[:10]}")
        regime = opts.get("regime")
        if regime == "both":
            parts.append(
                ", covering both the 2021-2025 reporting regime and the regime "
                "in force since 16 June 2025"
            )
        elif regime:
            parts.append(f", {regime} reporting regime only")
        categories = opts.get("categories")
        if categories:
            parts.append(f" ({', '.join(categories)} files)")
        parts.append(
            f", processed with sgotools using: {self._option_phrase()}"
        )
        parts.append(
            f". This yielded {self.rows_out:,} incident records "
            f"from {self.rows_in:,} published rows."
        )
        return "".join(parts)

    def _option_phrase(self) -> str:
        opts = self.options
        bits = []
        if opts.get("dedupe") == "latest":
            bits.append("one row per Report ID (latest version)")
        elif opts.get("dedupe") == "first":
            bits.append("one row per Report ID (first version)")
        else:
            bits.append("all report versions retained")
        bits.append(
            "administrative non-incident filings removed"
            if opts.get("drop_non_incidents")
            else "administrative non-incident filings retained"
        )
        if opts.get("harmonize_injury") == "legacy":
            bits.append("injury severity collapsed onto the pre-2025 scale")
        if opts.get("engaged_only"):
            bits.append("restricted to reports with the automation verified or alleged engaged")
        if opts.get("drop_undated"):
            bits.append("records without an incident date removed")
        return "; ".join(bits)

    def __str__(self) -> str:  # pragma: no cover - display only
        return self.summary()
