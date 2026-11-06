"""sgotools: reproducible access to NHTSA Standing General Order crash data.

The Standing General Order (SGO 2021-01) requires manufacturers and operators
to report crashes involving automated driving systems and Level 2 driver
assistance. NHTSA publishes the reports as CSV files, replacing them in place
each month without retaining earlier releases, and amended the order on
16 June 2025 in a way that changed the schema, the inclusion criteria and
several value sets.

This package provides a dated snapshot with checksums, a reader that handles
the files' inconsistent encodings, filters for the decisions every analysis
of this data has to make, and a record of which ones were applied.

    >>> import sgotools as sgo
    >>> snap = sgo.download_snapshot("data/2026-11-06")       # doctest: +SKIP
    >>> df = sgo.load_incidents(snap, regime="current")       # doctest: +SKIP
    >>> print(df.attrs["provenance"].methods_sentence())      # doctest: +SKIP
"""

from .constants import (
    INJURY_CURRENT_TO_LEGACY,
    NON_INCIDENT_REPORT_TYPES,
    REGIME_BREAK,
    SEMANTIC_BREAKS,
)
from .incidents import load_incidents
from .provenance import Provenance
from .snapshot import Snapshot, download_snapshot

__version__ = "0.1.0"

__all__ = [
    "Snapshot",
    "download_snapshot",
    "load_incidents",
    "Provenance",
    "REGIME_BREAK",
    "SEMANTIC_BREAKS",
    "NON_INCIDENT_REPORT_TYPES",
    "INJURY_CURRENT_TO_LEGACY",
    "__version__",
]
