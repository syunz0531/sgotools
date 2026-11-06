"""Facts about the SGO data that the rest of the package depends on.

Everything here was verified against the published CSV files and the
``SGO-2021-01_Data_Element_Definitions.pdf`` documents for both reporting
regimes (snapshot of 2026-11-06). Each entry carries the reason it exists so
that a user can audit the decision rather than trust it.
"""

from __future__ import annotations

#: The third amendment to SGO 2021-01 took effect on this date. NHTSA splits
#: the published data into a "current" file (this date onward) and an
#: "Archive-2021-2025" file (2021-07 through 2025-06-15). The two regimes
#: differ in schema, in inclusion criteria and in several value sets, so they
#: are never silently concatenated by this package.
REGIME_BREAK = "2025-06-16"

REGIMES = ("archive", "current")
CATEGORIES = ("ADS", "ADAS", "OTHER")

BASE_URL = "https://static.nhtsa.gov/odi/ffdd/sgo-2021-01/"
ARCHIVE_URL = BASE_URL + "Archive-2021-2025/"

#: Published file names, keyed by (regime, category).
FILE_URLS = {
    ("current", "ADS"): BASE_URL + "SGO-2021-01_Incident_Reports_ADS.csv",
    ("current", "ADAS"): BASE_URL + "SGO-2021-01_Incident_Reports_ADAS.csv",
    ("current", "OTHER"): BASE_URL + "SGO-2021-01_Incident_Reports_OTHER.csv",
    ("archive", "ADS"): ARCHIVE_URL + "SGO-2021-01_Incident_Reports_ADS.csv",
    ("archive", "ADAS"): ARCHIVE_URL + "SGO-2021-01_Incident_Reports_ADAS.csv",
    ("archive", "OTHER"): ARCHIVE_URL + "SGO-2021-01_Incident_Reports_OTHER.csv",
}

DEFINITION_URLS = {
    "current": BASE_URL + "SGO-2021-01_Data_Element_Definitions.pdf",
    "archive": ARCHIVE_URL + "SGO-2021-01_Data_Element_Definitions.pdf",
}

#: Encodings to try, in order. The published files are not uniform: as of the
#: 2026-11-06 snapshot the archive ADAS file is cp1252 while the others are
#: UTF-8, so reading without a fallback raises UnicodeDecodeError.
ENCODINGS = ("utf-8", "cp1252", "latin-1")

#: ``Report Type`` values that are administrative filings, not crashes.
#: Under the pre-2025 regime a reporting entity with nothing to report still
#: filed a monthly record; 3,519 such rows sit in the archive files and carry
#: no incident date. They are not crashes and are dropped by default.
NON_INCIDENT_REPORT_TYPES = ("No New or Updated Incident Reports",)

#: Columns that identify a report and its revision. NHTSA assigns one
#: ``Report ID`` per incident report and increments ``Report Version`` each
#: time the filing entity revises it, so the raw files hold several rows per
#: incident.
REPORT_ID = "Report ID"
REPORT_VERSION = "Report Version"

#: Columns this package adds, so provenance travels with the data.
PROVENANCE_COLUMNS = ("sgo_regime", "sgo_category", "sgo_snapshot")

#: Columns that exist under both regimes but do not mean the same thing.
#: Comparing them across the regime break without handling is a silent error.
SEMANTIC_BREAKS = {
    "Automation System Engaged?": (
        "Under the archive regime a non-null value indicated that the system "
        "was engaged. Under the current regime the column records only the "
        "system type; engagement moved to the new 'Engagement Status' column. "
        "44 current ADS reports carry 'ADS' here while Engagement Status is "
        "'Verified Not Engaged'."
    ),
    "Highest Injury Severity Alleged": (
        "Six categories became ten. Minor, Moderate and Serious were each "
        "split by hospitalisation, and 'No Injuries Reported' became both "
        "'No Injured Reported' and 'Property Damage. No Injured Reported'. "
        "Filtering current data with an archive label matches nothing."
    ),
    "Report Type": (
        "'1-Day', '10-Day Update' and 'No New or Updated Incident Reports' "
        "were retired; the current regime uses only '5-Day', 'Monthly' and "
        "'Update'."
    ),
    "Model Year": (
        "Stored as a float in the archive files ('2014.0') and as a string in "
        "the current files ('2014')."
    ),
}

#: Current-regime injury labels mapped onto the coarser archive scale, for
#: series that cross the regime break.
INJURY_CURRENT_TO_LEGACY = {
    "Minor W/ Hospitalization": "Minor",
    "Minor W/O Hospitalization": "Minor",
    "Moderate W/ Hospitalization": "Moderate",
    "Moderate W/O Hospitalization": "Moderate",
    "Serious W/ Hospitalization": "Serious",
    "Serious W/O Hospitalization": "Serious",
    "No Injured Reported": "No Injuries Reported",
    "Property Damage. No Injured Reported": "No Injuries Reported",
    "Fatality": "Fatality",
    "Unknown": "Unknown",
}

INJURY_COLUMN = "Highest Injury Severity Alleged"
ENGAGEMENT_STATUS = "Engagement Status"
AUTOMATION_ENGAGED = "Automation System Engaged?"
INCIDENT_DATE = "Incident Date"

#: ``Engagement Status`` values (current regime only) that mean the automation
#: was running at the time of the crash.
ENGAGED_VALUES = ("Verified Engaged", "Alleged Engaged")
