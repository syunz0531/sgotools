# sgotools

Reproducible access to the NHTSA Standing General Order crash reports for
automated driving systems (ADS) and Level 2 driver assistance (ADAS).

NHTSA's Standing General Order 2021-01 requires named manufacturers and
operators to report crashes involving these systems, and publishes the
reports as CSV files. The files are widely used, and they are harder to use
correctly than they look.

## Three things that go wrong

**Rows are not crashes.** Under the pre-2025 reporting regime an entity with
nothing to report still filed a monthly record. 3,519 rows in the archive
files are such filings; they carry no incident date and no crash. They are
35% of the published archive rows. Separately, each revision of a report
appears as its own row. Counting rows gives 9,920 archive records against
4,201 current ones, which reads as a halving. Counting incidents gives 4,641
against 4,010, over periods of about 47 and 15 months.

**Columns changed meaning on 16 June 2025.** The third amendment to the order
replaced 48 columns with 27 new ones and altered four that kept their names.
The clearest trap is injury severity: the six-category scale became ten, with
Minor, Moderate and Serious each split by hospitalisation, and
`No Injuries Reported` becoming both `No Injured Reported` and
`Property Damage. No Injured Reported`. Filtering current data with the old
label matches nothing at all; filtering with the closest new label returns
146 records where the comparable figure is 1,461. `Automation System
Engaged?` is a second trap: under the current regime it records only the
system type, and 44 ADS reports carry `ADS` there while the new
`Engagement Status` column says the system was verified *not* engaged.

**Published releases are not archived.** NHTSA replaces the files in place
each month and keeps no earlier release. Its own change log records that the
15 May 2026 release omitted reports received before the cut-off, which were
added a month later, and that an August 2026 release replaced a narrative
published against the wrong report. An analysis run in May 2026 therefore
cannot be reproduced today. The archive-regime definitions document contains
no change log at all, so nothing is known about what moved between 2021 and
2025.

## Install

```bash
pip install sgotools
```

## Use

```python
import sgotools as sgo

# Fetch a dated copy with a manifest of URLs, timestamps and SHA-256 digests.
snapshot = sgo.download_snapshot("data/2026-11-06")

# Assemble incidents. Every default is a documented choice, not a silent one.
crashes = sgo.load_incidents(
    snapshot,
    regime="current",          # "current", "archive" or "both"
    categories=["ADS"],
    dedupe="latest",           # one row per Report ID
    drop_non_incidents=True,   # remove administrative filings
    harmonize_injury="legacy", # collapse the current scale onto the old one
    engaged_only=False,
)

print(crashes.attrs["provenance"].summary())
print(crashes.attrs["provenance"].methods_sentence())
```

`methods_sentence()` prints a description you can put in a paper:

> Crash records were taken from the NHTSA Standing General Order incident
> report files, retrieved 2026-11-06, current reporting regime only (ADS
> files), processed with sgotools using: one row per Report ID (latest
> version); administrative non-incident filings removed; injury severity
> collapsed onto the pre-2025 scale. This yielded 1,551 incident records from
> 1,595 published rows.

From the command line:

```bash
sgotools download data/2026-11-06
sgotools summary data/2026-11-06 --regime both --categories ADS ADAS
```

## Worked example

[`examples/`](examples/) walks through the three problems above on real data,
with the output and a figure included, and ships the script that produced
them.

## The decisions, and the defaults

| Option | Default | What it does |
|---|---|---|
| `regime` | `"both"` | Which reporting regime to read. `"both"` warns, because inclusion criteria differ across the break. |
| `categories` | `("ADS", "ADAS")` | Which published files. `"OTHER"` is almost entirely administrative filings under the archive regime. |
| `dedupe` | `"latest"` | One row per `Report ID`. `None` inflates counts by roughly 20–30%. |
| `drop_non_incidents` | `True` | Removes "nothing to report" filings. |
| `harmonize_injury` | `"legacy"` | Adds `injury_severity_harmonized` on the pre-2025 scale. |
| `engaged_only` | `False` | Keeps reports with the automation engaged, using `Engagement Status` where it exists. |
| `drop_undated` | `False` | Removes records with no parseable incident date. |
| `columns` | `"common"` | Keep only columns shared by every file read. Filters run before narrowing, so a regime-specific column a filter needs is still available. |

Nothing is applied behind your back: the options used and the rows each step
removed are attached to the result as `df.attrs["provenance"]`.

## What this package does not do

- It does not deduplicate crashes reported by more than one entity. The
  archive files flagged these in `Other Reporting Entities?`; the current
  files do not, and matching on date, city and state over-collapses distinct
  crashes in the same city on the same day. Doing this properly needs the
  narratives.
- It supplies no exposure denominator. Reporting entities are not required to
  disclose miles driven, so crash rates cannot be computed from these files
  alone.
- It does not judge whether a crash would have been police-reportable. That
  choice belongs to the analysis, and it is a large part of why published
  counts differ.
- It makes no safety claim about any company or system.

## Data source

Files are fetched from NHTSA's
[Standing General Order on Crash Reporting](https://www.nhtsa.gov/laws-regulations/standing-general-order-crash-reporting)
page. The data are public. Accuracy, completeness and interpretation remain
NHTSA's and the reporting entities'; this package only reads what is
published. The figures quoted above come from the snapshot of 2026-11-06,
covering reports received through 15 September 2026.

## License

MIT
