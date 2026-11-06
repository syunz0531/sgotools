"""Behaviour of :func:`sgotools.load_incidents`."""

from __future__ import annotations

import warnings

import pytest

import sgotools as sgo


def load(snapshot_dir, **kwargs):
    with warnings.catch_warnings():
        warnings.simplefilter("ignore")
        return sgo.load_incidents(snapshot_dir, **kwargs)


# -- snapshot -------------------------------------------------------------


def test_snapshot_reads_manifest(snapshot_dir):
    snap = sgo.Snapshot(snapshot_dir)
    assert snap.retrieved == "2026-11-06T00:00:00+00:00"
    assert snap.digest("archive", "ADS") == "a" * 64
    assert snap.digest("archive", "ADAS") is None


def test_snapshot_lists_only_files_present(snapshot_dir):
    assert sgo.Snapshot(snapshot_dir).available() == [
        ("archive", "ADS"),
        ("archive", "ADAS"),
        ("current", "ADS"),
    ]


def test_non_utf8_file_is_read(snapshot_dir):
    """The published archive ADAS file is cp1252, not UTF-8."""
    frame = sgo.Snapshot(snapshot_dir).read_raw("archive", "ADAS")
    assert "Café Transit" in set(frame["Reporting Entity"])


def test_missing_directory_raises(tmp_path):
    with pytest.raises(FileNotFoundError):
        sgo.Snapshot(tmp_path / "nope")


# -- deduplication --------------------------------------------------------


def test_dedupe_latest_keeps_the_newest_version(snapshot_dir):
    frame = load(snapshot_dir, regime="archive", categories=["ADS"],
                 drop_non_incidents=False)
    a1 = frame[frame["Report ID"] == "A1"]
    assert len(a1) == 1
    assert a1.iloc[0]["Report Version"] == 2
    assert a1.iloc[0]["Highest Injury Severity Alleged"] == "Moderate"


def test_dedupe_first_keeps_version_one(snapshot_dir):
    frame = load(snapshot_dir, regime="archive", categories=["ADS"],
                 dedupe="first", drop_non_incidents=False)
    assert frame[frame["Report ID"] == "A1"].iloc[0]["Report Version"] == 1


def test_dedupe_none_keeps_every_row(snapshot_dir):
    frame = load(snapshot_dir, regime="archive", categories=["ADS"],
                 dedupe=None, drop_non_incidents=False)
    assert len(frame) == 5


# -- administrative filings ----------------------------------------------


def test_non_incident_filings_are_dropped_by_default(snapshot_dir):
    frame = load(snapshot_dir, regime="archive", categories=["ADS"])
    assert "A3" not in set(frame["Report ID"])


def test_non_incident_filings_can_be_kept(snapshot_dir):
    frame = load(snapshot_dir, regime="archive", categories=["ADS"],
                 drop_non_incidents=False)
    assert "A3" in set(frame["Report ID"])


# -- injury harmonisation -------------------------------------------------


def test_current_injury_labels_collapse_onto_the_legacy_scale(snapshot_dir):
    frame = load(snapshot_dir, regime="current", categories=["ADS"])
    harmonized = dict(zip(frame["Report ID"], frame["injury_severity_harmonized"]))
    assert harmonized["C1"] == "Minor"
    # both current "no injury" labels map to the single archive label
    assert harmonized["C2"] == "No Injuries Reported"
    assert harmonized["C3"] == "No Injuries Reported"


def test_harmonisation_can_be_switched_off(snapshot_dir):
    frame = load(snapshot_dir, regime="current", categories=["ADS"],
                 harmonize_injury=None)
    assert "injury_severity_harmonized" not in frame.columns


def test_harmonised_counts_match_across_regimes(snapshot_dir):
    """The point of the mapping: one label, not three."""
    frame = load(snapshot_dir, regime="both", categories=["ADS"])
    counts = frame["injury_severity_harmonized"].value_counts()
    assert counts["No Injuries Reported"] == 3  # A2, C2, C3


# -- engagement -----------------------------------------------------------


def test_engaged_only_uses_engagement_status_for_current_rows(snapshot_dir):
    """C2 is reported as ADS but verified NOT engaged, so it must go."""
    frame = load(snapshot_dir, regime="current", categories=["ADS"],
                 engaged_only=True)
    assert set(frame["Report ID"]) == {"C1", "C3"}


def test_engaged_only_survives_common_column_narrowing(snapshot_dir):
    """Engagement Status is current-only; narrowing must not disable the filter."""
    frame = load(snapshot_dir, regime="both", categories=["ADS"],
                 engaged_only=True, columns="common")
    assert "C2" not in set(frame["Report ID"])


def test_engaged_only_falls_back_for_archive_rows(snapshot_dir):
    frame = sgo.load_incidents(snapshot_dir, regime="archive", categories=["ADS"],
                               engaged_only=True)
    # A4 has no automation value recorded at all
    assert "A4" not in set(frame["Report ID"])
    assert any("Engagement Status" in w for w in frame.attrs["provenance"].warnings)


# -- dates ----------------------------------------------------------------


def test_drop_undated_removes_rows_without_a_parseable_date(snapshot_dir):
    frame = load(snapshot_dir, regime="archive", categories=["ADS"],
                 drop_non_incidents=False, drop_undated=True)
    assert "A3" not in set(frame["Report ID"])


# -- columns --------------------------------------------------------------


def test_common_columns_excludes_regime_specific_fields(snapshot_dir):
    frame = load(snapshot_dir, regime="both", categories=["ADS"], columns="common")
    assert "Posted Speed Limit (MPH)" not in frame.columns
    assert "Engagement Status" not in frame.columns


def test_all_columns_keeps_regime_specific_fields_as_na(snapshot_dir):
    frame = load(snapshot_dir, regime="both", categories=["ADS"], columns="all")
    assert "Posted Speed Limit (MPH)" in frame.columns
    current = frame[frame["sgo_regime"] == "current"]
    assert current["Posted Speed Limit (MPH)"].isna().all()


def test_provenance_columns_are_always_added(snapshot_dir):
    frame = load(snapshot_dir, regime="both", categories=["ADS"])
    for column in ("sgo_regime", "sgo_category", "sgo_snapshot"):
        assert column in frame.columns


# -- warnings and provenance ---------------------------------------------


def test_crossing_the_regime_break_warns(snapshot_dir):
    with pytest.warns(UserWarning, match="2025-06-16"):
        sgo.load_incidents(snapshot_dir, regime="both", categories=["ADS"])


def test_single_regime_does_not_warn_about_the_break(snapshot_dir):
    with warnings.catch_warnings(record=True) as caught:
        warnings.simplefilter("always")
        sgo.load_incidents(snapshot_dir, regime="current", categories=["ADS"])
    assert not any("2025-06-16" in str(w.message) for w in caught)


def test_provenance_records_every_step(snapshot_dir):
    frame = load(snapshot_dir, regime="archive", categories=["ADS"])
    names = [step.name for step in frame.attrs["provenance"].steps]
    assert names == ["read", "dedupe", "drop_non_incidents", "harmonize_injury"]


def test_provenance_counts_are_consistent(snapshot_dir):
    prov = load(snapshot_dir, regime="archive", categories=["ADS"]).attrs["provenance"]
    for earlier, later in zip(prov.steps, prov.steps[1:]):
        assert earlier.rows_after == later.rows_before
    assert prov.rows_out <= prov.rows_in


def test_methods_sentence_names_the_choices(snapshot_dir):
    prov = load(snapshot_dir, regime="current", categories=["ADS"]).attrs["provenance"]
    sentence = prov.methods_sentence()
    assert "latest version" in sentence
    assert "2026-11-06" in sentence
    assert "pre-2025 scale" in sentence


# -- argument validation --------------------------------------------------


@pytest.mark.parametrize(
    "kwargs",
    [
        {"regime": "futur"},
        {"categories": ["NOPE"]},
        {"categories": []},
        {"dedupe": "newest"},
        {"harmonize_injury": "modern"},
        {"columns": "some"},
    ],
)
def test_bad_arguments_raise(snapshot_dir, kwargs):
    with pytest.raises(ValueError):
        sgo.load_incidents(snapshot_dir, **kwargs)
