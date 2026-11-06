---
title: 'sgotools: Reproducible access to NHTSA Standing General Order crash reports'
tags:
  - Python
  - road safety
  - automated driving
  - crash data
  - reproducibility
  - open data
authors:
  - name: Seoyoung Lee
    orcid: 0009-0004-4053-8849
    affiliation: 1
affiliations:
  - name: Department of Computer Science and Engineering, Sungkyunkwan University, Suwon, Republic of Korea
    index: 1
date: 7 November 2026
bibliography: paper.bib
---

# Summary

The United States National Highway Traffic Safety Administration (NHTSA)
requires named manufacturers and operators to report crashes involving
automated driving systems (ADS) and Level 2 driver assistance (ADAS) under
Standing General Order 2021-01, and publishes the resulting incident reports
as CSV files [@nhtsa_sgo]. These files are the main public record of
real-world automated-vehicle crashes in the United States and are used in
safety evaluations by regulators, insurers, developers and academics.

`sgotools` is a Python package for working with those files correctly. It
pins a dated snapshot of the published data together with retrieval
timestamps and SHA-256 digests, reads files whose character encodings are not
uniform, reconciles the schema and value changes introduced when the order
was amended on 16 June 2025, and records every filtering decision applied so
that a published count can be traced back to the choices that produced it.

# Statement of need

The published files are harder to use correctly than their tabular form
suggests, in three ways that are easy to miss and that change results
substantially.

**Published rows are not crashes.** Under the pre-2025 regime a reporting
entity with nothing to report still filed a monthly record. In the snapshot
examined here, 3,519 archive rows carry the report type
`No New or Updated Incident Reports`; they describe no crash and 98.6% of
them have no incident date. Separately, each revision of a report appears as
its own row, keyed by `Report ID` and `Report Version`. Counting published
rows gives 9,920 archive records against 4,201 current ones, which reads as a
halving; counting incidents gives 4,641 against 4,010, over periods of about
47 and 15 months. The Insurance Institute for Highway Safety reports the same
difficulty from the other direction, reducing 1,692 SGO records to 977 unique
incidents in their own analysis [@teoh2026].

**Columns changed meaning across the 2025 amendment.** NHTSA publishes the
two regimes as separate files, and the schemas differ: 48 columns were
removed, 27 added, and of the 89 that appear in both, four no longer mean the
same thing. The clearest case is injury severity, where a six-category scale
became ten. `Minor`, `Moderate` and `Serious` were each split by
hospitalisation, and `No Injuries Reported` became both `No Injured Reported`
and `Property Damage. No Injured Reported`. Filtering current data with the
old label matches nothing; filtering with the closest new label returns 146
records where the comparable figure is 1,461. A second case is
`Automation System Engaged?`, which under the current regime records only the
system type: 44 current ADS reports carry `ADS` there while the new
`Engagement Status` column states the system was verified *not* engaged.
Columns removed in the amendment include posted speed limit, lighting,
roadway surface, mileage and whether the crash was investigated by law
enforcement, and the separate subject-vehicle and crash-partner airbag and
tow fields were collapsed into single columns that no longer identify which
vehicle is described.

**Releases are replaced, not archived.** NHTSA overwrites the published files
each month and retains no earlier release. Its own change log records that
the 15 May 2026 release omitted reports received before the cut-off, which
were restored a month later; that an August 2026 release replaced a narrative
that had been published against the wrong report; and that city and state
fields first appeared in the November 2025 release. An analysis run against
the May 2026 release therefore cannot be reproduced from the current files,
and the archive-regime documentation contains no change log at all.

Existing packages cover other public crash datasets — `fars_cleaner` for the
US Fatality Analysis Reporting System [@abrams2022] and `stats19` for Great
Britain's STATS19 collisions [@lovelace2019] — but no comparable tool exists
for the SGO files, and the most widely used general NHTSA Python client marks
the Standing General Order explicitly out of scope. Work on the
comparability of automated-vehicle crash databases has established that
inconsistent inclusion criteria make crash-rate comparisons difficult
[@goodall2025], and benchmark analyses have had to construct their own
exposure and severity conventions [@scanlon2024]. In practice each study
reimplements the cleaning steps in analysis scripts, and the resulting
choices are reported, if at all, in prose. `sgotools` makes those choices
explicit arguments with documented defaults, and attaches the ones used to
the data.

# Functionality

```python
import sgotools as sgo

snapshot = sgo.download_snapshot("data/2026-11-06")

crashes = sgo.load_incidents(
    snapshot,
    regime="current",           # "current", "archive" or "both"
    categories=["ADS"],
    dedupe="latest",            # one row per Report ID
    drop_non_incidents=True,    # remove administrative filings
    harmonize_injury="legacy",  # collapse onto the pre-2025 scale
    engaged_only=False,
)

print(crashes.attrs["provenance"].methods_sentence())
```

Each argument corresponds to a decision that published analyses have made
differently. Filters run before the frame is narrowed to the columns shared
by both regimes, so a filter never degrades silently because the column it
needs exists under only one regime. Reading data that spans the amendment
emits warnings naming each affected column. The attached `Provenance` object
holds the options used, the rows removed at each step and the file digests,
and renders a sentence suitable for a methods section:

> Crash records were taken from the NHTSA Standing General Order incident
> report files, retrieved 2026-11-06, current reporting regime only (ADS
> files), processed with sgotools using: one row per Report ID (latest
> version); administrative non-incident filings removed; injury severity
> collapsed onto the pre-2025 scale. This yielded 1,551 incident records from
> 1,595 published rows.

# Limitations

`sgotools` does not deduplicate crashes reported by more than one entity.
The archive files flagged these in `Other Reporting Entities?`, a column the
current files do not have, and matching on date, city and state
over-collapses distinct crashes in the same city on the same day; doing this
properly requires the narratives. The package supplies no exposure
denominator, because reporting entities are not required to disclose distance
travelled, so crash rates cannot be computed from these files alone. It does
not judge whether a crash would have been police-reportable, a choice that
belongs to the analysis and accounts for much of the variation between
published counts. It makes no safety claim about any company or system.

All figures quoted here describe the snapshot retrieved on 6 November 2026,
covering reports received through 15 September 2026, and will change as NHTSA
publishes further releases.

# Acknowledgements

This work used only public data published by NHTSA. The author declares no
competing interests and received no specific funding.

# References
