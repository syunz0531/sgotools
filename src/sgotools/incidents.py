"""Assembling an analysis-ready table of SGO incident reports."""

from __future__ import annotations

import warnings
from typing import Iterable, Optional, Sequence

import pandas as pd

from .constants import (
    AUTOMATION_ENGAGED,
    CATEGORIES,
    ENGAGED_VALUES,
    ENGAGEMENT_STATUS,
    INCIDENT_DATE,
    INJURY_COLUMN,
    INJURY_CURRENT_TO_LEGACY,
    NON_INCIDENT_REPORT_TYPES,
    REGIME_BREAK,
    REGIMES,
    REPORT_ID,
    REPORT_VERSION,
    SEMANTIC_BREAKS,
)
from .provenance import Provenance
from .snapshot import Snapshot


def load_incidents(
    snapshot: Snapshot | str,
    regime: str = "both",
    categories: Sequence[str] = ("ADS", "ADAS"),
    dedupe: Optional[str] = "latest",
    drop_non_incidents: bool = True,
    harmonize_injury: Optional[str] = "legacy",
    engaged_only: bool = False,
    drop_undated: bool = False,
    columns: str = "common",
) -> pd.DataFrame:
    """Return one row per incident report, with every choice recorded.

    Each argument corresponds to a decision that published analyses of this
    data have made differently. The defaults are the ones documented in the
    README; none of them is applied silently, and the choices actually used
    are attached to the result as ``df.attrs["provenance"]``.

    Parameters
    ----------
    snapshot:
        A :class:`~sgotools.snapshot.Snapshot` or a path to one.
    regime:
        ``"current"`` (16 June 2025 onward), ``"archive"`` (2021-07 to
        2025-06-15), or ``"both"``. The two regimes differ in schema and in
        what has to be reported, so ``"both"`` emits a warning unless
        ``columns="common"``.
    categories:
        Which published files to read: ``"ADS"``, ``"ADAS"``, ``"OTHER"``.
        ``"OTHER"`` holds reports whose automation type was not given; under
        the archive regime it is almost entirely administrative filings.
    dedupe:
        ``"latest"`` keeps the highest ``Report Version`` per ``Report ID``,
        ``"first"`` keeps version 1, ``None`` keeps every row. The raw files
        hold several rows per incident, so ``None`` inflates counts by
        roughly 20-30 per cent.
    drop_non_incidents:
        Remove rows whose ``Report Type`` is an administrative "nothing to
        report" filing. 3,519 such rows sit in the archive files.
    harmonize_injury:
        ``"legacy"`` maps the current ten-category injury scale onto the
        pre-2025 six-category scale, into a new ``injury_severity_harmonized``
        column. ``None`` leaves the raw values alone.
    engaged_only:
        Keep only reports where the automation was engaged. Under the current
        regime this uses ``Engagement Status``; under the archive regime that
        column does not exist and the filter cannot be applied, which is
        recorded as a warning.
    drop_undated:
        Remove rows with no parseable ``Incident Date``.
    columns:
        ``"common"`` keeps only columns present under both regimes,
        ``"all"`` keeps the union (missing ones become NA).

    Returns
    -------
    pandas.DataFrame
        With added ``sgo_regime``, ``sgo_category`` and ``sgo_snapshot``
        columns, and ``.attrs["provenance"]`` holding a
        :class:`~sgotools.provenance.Provenance`.
    """
    if isinstance(snapshot, (str,)) or hasattr(snapshot, "__fspath__"):
        snapshot = Snapshot(snapshot)
    regimes = _resolve_regimes(regime)
    categories = tuple(categories)
    _validate(regimes, categories, dedupe, harmonize_injury, columns)

    prov = Provenance(
        snapshot_path=str(snapshot.path),
        snapshot_retrieved=snapshot.retrieved,
        options={
            "regime": regime,
            "categories": list(categories),
            "dedupe": dedupe,
            "drop_non_incidents": drop_non_incidents,
            "harmonize_injury": harmonize_injury,
            "engaged_only": engaged_only,
            "drop_undated": drop_undated,
            "columns": columns,
        },
    )

    frames = []
    for reg in regimes:
        for cat in categories:
            raw = snapshot.read_raw(reg, cat)
            raw["sgo_regime"] = reg
            raw["sgo_category"] = cat
            raw["sgo_snapshot"] = snapshot.retrieved or str(snapshot.path)
            frames.append(raw)
            digest = snapshot.digest(reg, cat)
            if digest:
                prov.digests[f"{reg}_{cat}"] = digest

    # Filters run on the union of columns, so a filter never silently
    # degrades because the column it needs is regime-specific. Narrowing to
    # the shared columns happens last.
    shared = set(frames[0].columns)
    for frame in frames[1:]:
        shared &= set(frame.columns)
    df = pd.concat(frames, ignore_index=True, sort=False)
    start = len(df)
    prov.record("read", f"{len(frames)} published file(s)", start, start)

    if dedupe:
        df = _dedupe(df, dedupe, prov)
    if drop_non_incidents:
        df = _drop_non_incidents(df, prov)
    if engaged_only:
        df = _engaged_only(df, regimes, prov)
    if drop_undated:
        df = _drop_undated(df, prov)
    if harmonize_injury == "legacy":
        df = _harmonize_injury(df, prov)

    df = _narrow_columns(df, shared, columns, prov)

    if len(regimes) > 1:
        _warn_regime_mix(prov, columns)

    df = df.reset_index(drop=True)
    df.attrs["provenance"] = prov
    for message in prov.warnings:
        warnings.warn(message, UserWarning, stacklevel=2)
    return df


# -- steps ----------------------------------------------------------------


def _resolve_regimes(regime: str) -> tuple[str, ...]:
    if regime == "both":
        return REGIMES
    if regime in REGIMES:
        return (regime,)
    raise ValueError(f"regime must be one of 'current', 'archive', 'both'; got {regime!r}")


def _validate(regimes, categories, dedupe, harmonize_injury, columns) -> None:
    bad = set(categories) - set(CATEGORIES)
    if bad:
        raise ValueError(f"unknown categories: {sorted(bad)}; choose from {CATEGORIES}")
    if not categories:
        raise ValueError("at least one category is required")
    if dedupe not in (None, "latest", "first"):
        raise ValueError("dedupe must be 'latest', 'first' or None")
    if harmonize_injury not in (None, "legacy"):
        raise ValueError("harmonize_injury must be 'legacy' or None")
    if columns not in ("common", "all"):
        raise ValueError("columns must be 'common' or 'all'")


def _narrow_columns(
    df: pd.DataFrame, shared: set[str], columns: str, prov: Provenance
) -> pd.DataFrame:
    """Reduce to the columns present under every regime read, if asked.

    Runs after filtering so that a regime-specific column a filter needs,
    such as ``Engagement Status``, is still available when the filter runs.
    """
    if columns == "all":
        return df
    keep = [c for c in df.columns if c in shared or c.startswith(("sgo_", "injury_severity_"))]
    dropped = [c for c in df.columns if c not in keep]
    if dropped:
        prov.warnings.append(
            f"columns='common' dropped {len(dropped)} column(s) absent from at "
            f"least one file read, including {', '.join(sorted(dropped)[:5])}"
            f"{' ...' if len(dropped) > 5 else ''}. "
            "Pass columns='all' to keep them as NA."
        )
    return df[keep]


def _dedupe(df: pd.DataFrame, how: str, prov: Provenance) -> pd.DataFrame:
    if REPORT_ID not in df.columns or REPORT_VERSION not in df.columns:
        prov.warnings.append(
            f"{REPORT_ID!r}/{REPORT_VERSION!r} not present; deduplication skipped."
        )
        return df
    before = len(df)
    keep = "last" if how == "latest" else "first"
    out = (
        df.sort_values([REPORT_ID, REPORT_VERSION], kind="mergesort")
        .drop_duplicates(subset=[REPORT_ID], keep=keep)
    )
    prov.record("dedupe", f"one row per {REPORT_ID} ({how} version)", before, len(out))
    return out


def _drop_non_incidents(df: pd.DataFrame, prov: Provenance) -> pd.DataFrame:
    if "Report Type" not in df.columns:
        prov.warnings.append("'Report Type' not present; non-incident filter skipped.")
        return df
    before = len(df)
    out = df[~df["Report Type"].isin(NON_INCIDENT_REPORT_TYPES)]
    prov.record(
        "drop_non_incidents",
        "administrative 'nothing to report' filings",
        before,
        len(out),
    )
    return out


def _engaged_only(df: pd.DataFrame, regimes, prov: Provenance) -> pd.DataFrame:
    before = len(df)
    if ENGAGEMENT_STATUS in df.columns:
        mask = df[ENGAGEMENT_STATUS].isin(ENGAGED_VALUES)
        # Archive rows have no Engagement Status; fall back to the older
        # column, whose presence implied engagement under that regime.
        archive_rows = df["sgo_regime"] == "archive"
        if archive_rows.any():
            mask = mask | (archive_rows & df.get(AUTOMATION_ENGAGED, pd.Series(dtype=object)).notna())
            prov.warnings.append(
                "engaged_only: archive rows have no 'Engagement Status'; "
                f"{AUTOMATION_ENGAGED!r} was used for them instead, which is a "
                "weaker criterion."
            )
    elif AUTOMATION_ENGAGED in df.columns:
        mask = df[AUTOMATION_ENGAGED].notna()
        prov.warnings.append(
            "engaged_only: 'Engagement Status' absent, so engagement could "
            f"only be inferred from {AUTOMATION_ENGAGED!r}."
        )
    else:
        prov.warnings.append("engaged_only: no engagement column present; filter skipped.")
        return df
    out = df[mask]
    prov.record("engaged_only", "automation verified or alleged engaged", before, len(out))
    return out


def _drop_undated(df: pd.DataFrame, prov: Provenance) -> pd.DataFrame:
    if INCIDENT_DATE not in df.columns:
        prov.warnings.append(f"{INCIDENT_DATE!r} not present; drop_undated skipped.")
        return df
    before = len(df)
    parsed = pd.to_datetime(df[INCIDENT_DATE], errors="coerce")
    out = df[parsed.notna()]
    prov.record("drop_undated", "no parseable incident date", before, len(out))
    return out


def _harmonize_injury(df: pd.DataFrame, prov: Provenance) -> pd.DataFrame:
    if INJURY_COLUMN not in df.columns:
        prov.warnings.append(f"{INJURY_COLUMN!r} not present; injury harmonisation skipped.")
        return df
    out = df.copy()
    out["injury_severity_harmonized"] = out[INJURY_COLUMN].map(
        lambda v: INJURY_CURRENT_TO_LEGACY.get(v, v)
    )
    prov.record(
        "harmonize_injury",
        "current injury scale collapsed onto the pre-2025 scale",
        len(df),
        len(out),
    )
    return out


def _warn_regime_mix(prov: Provenance, columns: str) -> None:
    prov.warnings.append(
        f"regime='both' spans the {REGIME_BREAK} reporting change. Inclusion "
        "criteria and several value sets differ across it, so a trend through "
        "this date mixes real change with reporting change."
    )
    if columns == "all":
        prov.warnings.append(
            "columns='all' keeps columns that exist under only one regime; "
            "they are NA for the other and must not be read as zero."
        )
    for column, reason in SEMANTIC_BREAKS.items():
        prov.warnings.append(f"semantic break in {column!r}: {reason}")
