# API reference

Everything below is exported from the top-level package:

```python
import sgotools as sgo
```

---

## `download_snapshot(dest, regimes=..., categories=..., include_definitions=True, timeout=300)`

Download one dated copy of the published SGO files into `dest` and write a
`manifest.json` beside them.

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `dest` | `str` or `Path` | — | Directory to create. |
| `regimes` | iterable of `str` | `("archive", "current")` | Which reporting regimes to fetch. |
| `categories` | iterable of `str` | `("ADS", "ADAS", "OTHER")` | Which published files. |
| `include_definitions` | `bool` | `True` | Also fetch the data-element definition PDFs, which carry NHTSA's change log. |
| `timeout` | `int` | `300` | Per-file socket timeout in seconds. |

Returns a [`Snapshot`](#snapshot) opened on the new directory.

A file that fails to download does not raise; its manifest entry records
`status: "error"` and the message, so a partial snapshot is still usable and
still says what is missing.

The manifest records, per file, the URL, the retrieval timestamp in UTC, the
byte count and the SHA-256 digest. NHTSA replaces the published files in
place each month and retains no earlier release, so this is what lets a
result be traced to the release it came from.

```python
snapshot = sgo.download_snapshot("data/2026-11-06")
snapshot.manifest["files"][0]["sha256"]
```

---

## `Snapshot`

A dated directory of published files. Construct it on a directory that
`download_snapshot` wrote, or on any directory holding files named
`{regime}_{category}.csv`.

```python
snapshot = sgo.Snapshot("data/2026-11-06")
```

Raises `FileNotFoundError` if the path is not a directory.

### Attributes

| Name | Type | Meaning |
|---|---|---|
| `path` | `Path` | The directory. |
| `manifest` | `dict` or `None` | Parsed `manifest.json`; `None` if absent. |
| `retrieved` | `str` or `None` | UTC timestamp the snapshot was taken. |

### Methods

**`available()`** — list of `(regime, category)` pairs present on disk.

**`digest(regime, category)`** — SHA-256 of one published file as recorded at
download time, or `None` if there is no manifest entry for it.

**`read_raw(regime, category)`** — read one file into a `DataFrame` with no
cleaning whatsoever. Encoding is detected by trying UTF-8, then cp1252, then
latin-1, because the published files are not uniformly encoded: in the
2026-11-06 release the archive ADAS file is cp1252 and the rest are UTF-8.

---

## `load_incidents(snapshot, ...)`

Return one row per incident report, with every choice recorded.

| Parameter | Type | Default | Meaning |
|---|---|---|---|
| `snapshot` | `Snapshot`, `str` or `Path` | — | Snapshot to read. |
| `regime` | `str` | `"both"` | `"current"`, `"archive"` or `"both"`. |
| `categories` | sequence of `str` | `("ADS", "ADAS")` | Which published files. |
| `dedupe` | `str` or `None` | `"latest"` | `"latest"`, `"first"` or `None`. |
| `drop_non_incidents` | `bool` | `True` | Remove administrative filings. |
| `harmonize_injury` | `str` or `None` | `"legacy"` | `"legacy"` or `None`. |
| `engaged_only` | `bool` | `False` | Keep only reports with the automation engaged. |
| `drop_undated` | `bool` | `False` | Remove rows with no parseable incident date. |
| `columns` | `str` | `"common"` | `"common"` or `"all"`. |

Raises `ValueError` for any unrecognised value.

### What each option does

**`regime`** — the two regimes are published as separate files with different
schemas and different inclusion criteria. `"both"` reads them together and
warns, naming each column whose meaning changed.

**`categories`** — `"OTHER"` holds reports whose automation type was not
given. Under the archive regime it is almost entirely administrative
filings, and 98.6% of its rows have no incident date.

**`dedupe`** — the raw files hold one row per report *version*, keyed by
`Report ID` and `Report Version`. `"latest"` keeps the newest version of each
report, `"first"` keeps version 1, `None` keeps everything and inflates
counts by roughly 20–30%.

**`drop_non_incidents`** — under the pre-2025 regime an entity with nothing to
report still filed a monthly record, with `Report Type` set to
`No New or Updated Incident Reports`. 3,519 such rows sit in the archive
files. They describe no crash.

**`harmonize_injury`** — `"legacy"` adds an `injury_severity_harmonized`
column mapping the current ten-category scale onto the pre-2025
six-category one. See [`INJURY_CURRENT_TO_LEGACY`](#constants).

**`engaged_only`** — under the current regime this uses `Engagement Status`.
Under the archive regime that column does not exist and the older
`Automation System Engaged?` is used instead, which is a weaker criterion;
the substitution is recorded as a warning.

**`columns`** — `"common"` keeps only columns present in every file read;
`"all"` keeps the union, with missing values as NA. Filters run *before*
narrowing, so a filter is never disabled by its column being
regime-specific.

### Return value

A `DataFrame` with three added columns — `sgo_regime`, `sgo_category`,
`sgo_snapshot` — and a [`Provenance`](#provenance) at
`df.attrs["provenance"]`.

Note that `DataFrame.attrs` is not preserved by every pandas operation. If
you need the provenance after heavy reshaping, keep a reference to it:

```python
crashes = sgo.load_incidents(snapshot)
provenance = crashes.attrs["provenance"]
```

---

## `Provenance`

The record of one `load_incidents` call.

| Attribute | Type | Meaning |
|---|---|---|
| `snapshot_path` | `str` | Directory read. |
| `snapshot_retrieved` | `str` | UTC timestamp of the snapshot. |
| `digests` | `dict` | SHA-256 per file read. |
| `options` | `dict` | The arguments used. |
| `steps` | `list[Step]` | One entry per filter, with `rows_before` and `rows_after`. |
| `warnings` | `list[str]` | Everything the call warned about. |
| `rows_in`, `rows_out` | `int` | Published rows read, and records returned. |

**`summary()`** — multi-line report of the options, each step and the
warnings.

**`methods_sentence()`** — a sentence describing how the dataset was
assembled, for a methods section.

Each `Step` has `name`, `description`, `rows_before`, `rows_after` and a
`removed` property.

---

## Constants

| Name | Meaning |
|---|---|
| `REGIME_BREAK` | `"2025-06-16"`, the date the third amendment took effect. |
| `SEMANTIC_BREAKS` | Columns present under both regimes whose meaning changed, with an explanation for each. |
| `NON_INCIDENT_REPORT_TYPES` | `Report Type` values that are administrative filings, not crashes. |
| `INJURY_CURRENT_TO_LEGACY` | Current injury labels mapped onto the pre-2025 scale. |

```python
>>> sgo.REGIME_BREAK
'2025-06-16'
>>> sorted(sgo.SEMANTIC_BREAKS)
['Automation System Engaged?', 'Highest Injury Severity Alleged', 'Model Year', 'Report Type']
```

More of the package's assumptions, each with the reason it exists, are in
`src/sgotools/constants.py`.

---

## Command line

```bash
sgotools download DEST [--regime {archive,current,both}] [--no-definitions]
sgotools summary PATH [--regime {archive,current,both}] [--categories ADS ADAS]
```

`download` exits non-zero if any file failed. `summary` prints the
provenance report for a snapshot already on disk.
