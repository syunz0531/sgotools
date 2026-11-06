"""Small synthetic snapshots that reproduce the quirks of the real files."""

from __future__ import annotations

import json

import pandas as pd
import pytest

ARCHIVE_ONLY = ["Posted Speed Limit (MPH)", "Other Reporting Entities?"]
CURRENT_ONLY = ["Engagement Status", "VIN Decoded"]
SHARED = [
    "Report ID",
    "Report Version",
    "Report Type",
    "Reporting Entity",
    "Incident Date",
    "Highest Injury Severity Alleged",
    "Automation System Engaged?",
]


def _archive_rows():
    return [
        # one incident filed twice; the later version is the one to keep
        ("A1", 1, "5-Day", "Acme", "2024-03-01", "Minor", "ADS", 35, None),
        ("A1", 2, "Update", "Acme", "2024-03-01", "Moderate", "ADS", 35, "Beta Co"),
        ("A2", 1, "5-Day", "Acme", "2024-04-02", "No Injuries Reported", "ADS", 25, None),
        # administrative filing: no crash, no date
        ("A3", 1, "No New or Updated Incident Reports", "Acme", None, None, None, None, None),
        # automation not recorded at all
        ("A4", 1, "Monthly", "Beta Co", "2024-05-05", "Unknown", None, 45, None),
    ]


def _current_rows():
    return [
        ("C1", 1, "5-Day", "Acme", "2025-08-01", "Minor W/ Hospitalization",
         "ADS", "Verified Engaged", "ACME 2025"),
        ("C2", 1, "5-Day", "Acme", "2025-09-10", "Property Damage. No Injured Reported",
         "ADS", "Verified Not Engaged", "ACME 2025"),
        ("C3", 1, "Monthly", "Beta Co", "2025-10-11", "No Injured Reported",
         "ADS", "Verified Engaged", "BETA 2025"),
    ]


def _write(path, regime, category, rows, extra_cols, encoding="utf-8"):
    frame = pd.DataFrame(rows, columns=SHARED + extra_cols)
    frame.to_csv(path / f"{regime}_{category}.csv", index=False, encoding=encoding)


@pytest.fixture
def snapshot_dir(tmp_path):
    """A snapshot with both regimes, a manifest, and a cp1252 file."""
    _write(tmp_path, "archive", "ADS", _archive_rows(), ARCHIVE_ONLY)
    # mirror the real files, where one archive file is not UTF-8
    rows = [r[:3] + ("Café Transit",) + r[4:] for r in _archive_rows()]
    _write(tmp_path, "archive", "ADAS", rows, ARCHIVE_ONLY, encoding="cp1252")
    _write(tmp_path, "current", "ADS", _current_rows(), CURRENT_ONLY)

    manifest = {
        "tool": "sgotools",
        "created_utc": "2026-11-06T00:00:00+00:00",
        "files": [
            {"name": "archive_ADS.csv", "status": "ok", "sha256": "a" * 64},
            {"name": "current_ADS.csv", "status": "ok", "sha256": "c" * 64},
        ],
    }
    (tmp_path / "manifest.json").write_text(json.dumps(manifest), encoding="utf-8")
    return tmp_path
