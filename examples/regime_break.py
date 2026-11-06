"""What the 2025 reporting change does to a naive count of SGO crashes.

Run:
    python examples/regime_break.py [snapshot_dir]

Downloads a snapshot if the directory is missing, then prints three
comparisons and writes ``examples/regime_break.png``.
"""

from __future__ import annotations

import sys
import warnings
from pathlib import Path

import matplotlib
import pandas as pd

matplotlib.use("Agg")
import matplotlib.pyplot as plt  # noqa: E402

import sgotools as sgo  # noqa: E402

HERE = Path(__file__).resolve().parent
DEFAULT_SNAPSHOT = HERE.parent / "data" / "snapshot_2026-11-06"

# Validated categorical slots 1 and 2 (light surface).
ARCHIVE_COLOR, CURRENT_COLOR = "#2a78d6", "#eb6834"
INK, INK_MUTED, SURFACE = "#0b0b0b", "#52514e", "#fcfcfb"

CATEGORIES = ["ADS", "ADAS", "OTHER"]


def get_snapshot(path: Path) -> sgo.Snapshot:
    if path.exists():
        return sgo.Snapshot(path)
    print(f"snapshot not found, downloading into {path}")
    return sgo.download_snapshot(path)


def quiet(fn, *args, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return fn(*args, **kwargs)


def rule(title: str) -> None:
    print()
    print(title)
    print("-" * len(title))


def counting(snapshot: sgo.Snapshot) -> None:
    rule("1. Rows are not crashes")
    raw = {r: sum(len(snapshot.read_raw(r, c)) for c in CATEGORIES)
           for r in ("archive", "current")}
    deduped = {
        r: len(quiet(sgo.load_incidents, snapshot, regime=r, categories=CATEGORIES,
                     drop_non_incidents=False, harmonize_injury=None))
        for r in ("archive", "current")
    }
    incidents = {
        r: len(quiet(sgo.load_incidents, snapshot, regime=r, categories=CATEGORIES,
                     harmonize_injury=None))
        for r in ("archive", "current")
    }
    print(f"  {'':34s} {'archive':>9s} {'current':>9s}")
    for label, counts in [
        ("published rows", raw),
        ("one row per Report ID", deduped),
        ("minus administrative filings", incidents),
    ]:
        print(f"  {label:34s} {counts['archive']:9,d} {counts['current']:9,d}")
    naive = raw["current"] / raw["archive"] - 1
    real = incidents["current"] / incidents["archive"] - 1
    print()
    print(f"  Counting rows suggests a {naive:+.0%} change between the two files.")
    print(f"  Counting incidents gives {real:+.0%} - over 47 and 15 months, so")
    print("  neither figure is a crash-rate trend.")


def injury(snapshot: sgo.Snapshot) -> None:
    rule("2. An archive injury label matches nothing in current data")
    current = quiet(sgo.load_incidents, snapshot, regime="current",
                    categories=CATEGORIES)
    archive = quiet(sgo.load_incidents, snapshot, regime="archive",
                    categories=CATEGORIES)
    col = "Highest Injury Severity Alleged"
    print(f"  archive, label 'No Injuries Reported'       "
          f"{(archive[col] == 'No Injuries Reported').sum():6,d}")
    print(f"  current, same label                         "
          f"{(current[col] == 'No Injuries Reported').sum():6,d}   <- matches nothing")
    print(f"  current, closest new label                  "
          f"{(current[col] == 'No Injured Reported').sum():6,d}")
    print(f"  current, harmonised onto the archive scale  "
          f"{(current['injury_severity_harmonized'] == 'No Injuries Reported').sum():6,d}")


def monthly(snapshot: sgo.Snapshot) -> pd.DataFrame:
    frames = []
    for regime in ("archive", "current"):
        frame = quiet(sgo.load_incidents, snapshot, regime=regime,
                      categories=["ADS", "ADAS"], drop_undated=True,
                      harmonize_injury=None)
        counts = (pd.to_datetime(frame["Incident Date"], errors="coerce")
                  .dt.to_period("M").value_counts().sort_index())
        frames.append(counts.rename(regime))
    return pd.concat(frames, axis=1).sort_index()


def plot(series: pd.DataFrame, out: Path) -> None:
    series = series[series.index >= pd.Period("2022-01", "M")]
    # June 2025 is split between the two regimes and the published data stops
    # mid-September 2026, so both partial months are left out.
    break_month = pd.Period(sgo.REGIME_BREAK, "M")
    series = series[series.index < series.index.max()]
    archive = series["archive"][series.index < break_month]
    current = series["current"][series.index > break_month]

    fig, ax = plt.subplots(figsize=(9, 4.2), facecolor=SURFACE)
    ax.set_facecolor(SURFACE)

    ax.plot(archive.index.to_timestamp(), archive.values,
            color=ARCHIVE_COLOR, linewidth=2, label="2021–2025 regime")
    ax.plot(current.index.to_timestamp(), current.values,
            color=CURRENT_COLOR, linewidth=2, label="Regime since 16 June 2025")

    ax.axvline(pd.Timestamp(sgo.REGIME_BREAK), color=INK_MUTED,
               linewidth=1, linestyle=(0, (4, 3)), zorder=0)
    ax.annotate("reporting rules change", xy=(pd.Timestamp(sgo.REGIME_BREAK), 0),
                xytext=(6, 6), textcoords="offset points",
                color=INK_MUTED, fontsize=9, va="bottom")

    ax.set_title("Reported ADS and ADAS incidents per month",
                 color=INK, fontsize=13, pad=12, loc="left")
    ax.set_ylabel("incidents", color=INK_MUTED, fontsize=10)
    ax.set_ylim(bottom=0)
    ax.grid(axis="y", color="#e6e5e1", linewidth=0.8)
    ax.set_axisbelow(True)
    for side in ("top", "right"):
        ax.spines[side].set_visible(False)
    for side in ("left", "bottom"):
        ax.spines[side].set_color("#d8d7d2")
    ax.tick_params(colors=INK_MUTED, labelsize=9)

    legend = ax.legend(frameon=False, loc="upper left", fontsize=9)
    for text in legend.get_texts():
        text.set_color(INK)

    fig.text(0.01, -0.02,
             "The two lines are different reporting regimes, not one series: "
             "joining them would mix a rule change with a trend.\n"
             "June 2025 is split between the regimes and is omitted; the most "
             "recent months under-count, because reports arrive with a lag.",
             color=INK_MUTED, fontsize=8.5, ha="left")
    fig.tight_layout()
    fig.savefig(out, dpi=200, bbox_inches="tight", facecolor=SURFACE)
    print(f"\n  figure written to {out}")


def main() -> int:
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT_SNAPSHOT
    snapshot = get_snapshot(path)
    print(f"snapshot: {snapshot.path}")
    print(f"retrieved: {snapshot.retrieved}")

    counting(snapshot)
    injury(snapshot)

    rule("3. Monthly counts, split by regime")
    plot(monthly(snapshot), HERE / "regime_break.png")

    rule("4. What was actually done to the data")
    frame = quiet(sgo.load_incidents, snapshot, regime="current", categories=["ADS"])
    print(frame.attrs["provenance"].methods_sentence())
    return 0


if __name__ == "__main__":
    sys.exit(main())
