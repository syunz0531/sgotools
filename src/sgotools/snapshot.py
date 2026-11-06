"""Downloading and opening a dated copy of the published SGO files.

NHTSA replaces the published CSV files in place each month and keeps no
archive of earlier releases, so the same analysis run two months apart can
produce different numbers with nothing to show for it. The agency's own
change log records releases that omitted reports received before the cut-off
and a narrative that was published against the wrong report and later
replaced.

A :class:`Snapshot` is therefore a directory holding one dated copy of the
files plus a manifest recording, for each file, the URL it came from, the
time it was retrieved and its SHA-256 digest. Analyses cite the snapshot;
the manifest makes the claim checkable.
"""

from __future__ import annotations

import hashlib
import json
import urllib.request
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Iterable, Optional

import pandas as pd

from .constants import (
    CATEGORIES,
    DEFINITION_URLS,
    ENCODINGS,
    FILE_URLS,
    REGIMES,
)

MANIFEST_NAME = "manifest.json"
_USER_AGENT = "sgotools (https://github.com/syunz0531/sgotools)"


def _digest_and_write(response, dest: Path) -> tuple[int, str]:
    sha = hashlib.sha256()
    size = 0
    tmp = dest.with_suffix(dest.suffix + ".part")
    with open(tmp, "wb") as fh:
        while True:
            chunk = response.read(1 << 16)
            if not chunk:
                break
            fh.write(chunk)
            sha.update(chunk)
            size += len(chunk)
    tmp.replace(dest)
    return size, sha.hexdigest()


def download_snapshot(
    dest: str | Path,
    regimes: Iterable[str] = REGIMES,
    categories: Iterable[str] = CATEGORIES,
    include_definitions: bool = True,
    timeout: int = 300,
) -> "Snapshot":
    """Download one dated copy of the published files into ``dest``.

    Parameters
    ----------
    dest:
        Directory to create. A ``manifest.json`` is written alongside the
        downloaded files.
    regimes, categories:
        Which published files to fetch. Defaults to all six.
    include_definitions:
        Also fetch the data-element definition PDFs, which carry NHTSA's
        change log.

    Returns
    -------
    Snapshot
        Opened on the directory just written.
    """
    dest = Path(dest)
    dest.mkdir(parents=True, exist_ok=True)
    entries = []

    wanted = [(r, c) for r in regimes for c in categories]
    for regime, category in wanted:
        url = FILE_URLS[(regime, category)]
        name = f"{regime}_{category}.csv"
        entries.append(_fetch_one(url, dest / name, name, timeout))

    if include_definitions:
        for regime in regimes:
            url = DEFINITION_URLS[regime]
            name = f"{regime}_definitions.pdf"
            entries.append(_fetch_one(url, dest / name, name, timeout))

    manifest = {
        "tool": "sgotools",
        "created_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        "source": "https://www.nhtsa.gov/laws-regulations/standing-general-order-crash-reporting",
        "note": (
            "NHTSA replaces the published files in place each month and does "
            "not retain earlier releases. This manifest pins the release this "
            "snapshot was taken from."
        ),
        "files": entries,
    }
    (dest / MANIFEST_NAME).write_text(
        json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
    )
    return Snapshot(dest)


def _fetch_one(url: str, path: Path, name: str, timeout: int) -> dict:
    entry = {"name": name, "url": url}
    request = urllib.request.Request(url, headers={"User-Agent": _USER_AGENT})
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            size, digest = _digest_and_write(response, path)
    except Exception as exc:  # noqa: BLE001 - reported, not raised
        entry.update({"status": "error", "message": str(exc)})
        return entry
    entry.update(
        {
            "status": "ok",
            "bytes": size,
            "sha256": digest,
            "retrieved_utc": datetime.now(timezone.utc).isoformat(timespec="seconds"),
        }
    )
    return entry


@dataclass
class Snapshot:
    """A dated directory of published SGO files.

    Attributes
    ----------
    path:
        Directory holding the files and ``manifest.json``.
    """

    path: Path

    def __init__(self, path: str | Path):
        self.path = Path(path)
        if not self.path.is_dir():
            raise FileNotFoundError(f"not a directory: {self.path}")

    # -- manifest ---------------------------------------------------------

    @property
    def manifest(self) -> Optional[dict]:
        """Manifest contents, or ``None`` for a directory not written by
        :func:`download_snapshot`."""
        manifest_path = self.path / MANIFEST_NAME
        if not manifest_path.exists():
            return None
        return json.loads(manifest_path.read_text(encoding="utf-8"))

    @property
    def retrieved(self) -> Optional[str]:
        """UTC timestamp the snapshot was taken, if a manifest is present."""
        manifest = self.manifest
        return manifest["created_utc"] if manifest else None

    def digest(self, regime: str, category: str) -> Optional[str]:
        """SHA-256 of one published file as recorded at download time."""
        manifest = self.manifest
        if not manifest:
            return None
        name = f"{regime}_{category}.csv"
        for entry in manifest["files"]:
            if entry["name"] == name:
                return entry.get("sha256")
        return None

    # -- reading ----------------------------------------------------------

    def available(self) -> list[tuple[str, str]]:
        """``(regime, category)`` pairs present on disk."""
        found = []
        for regime in REGIMES:
            for category in CATEGORIES:
                if (self.path / f"{regime}_{category}.csv").exists():
                    found.append((regime, category))
        return found

    def read_raw(self, regime: str, category: str) -> pd.DataFrame:
        """Read one published file with no cleaning at all.

        Encoding is detected by trying :data:`~sgotools.constants.ENCODINGS`
        in order, because the published files are not uniformly encoded.
        """
        path = self.path / f"{regime}_{category}.csv"
        if not path.exists():
            raise FileNotFoundError(path)
        last: Optional[UnicodeDecodeError] = None
        for encoding in ENCODINGS:
            try:
                return pd.read_csv(path, low_memory=False, encoding=encoding)
            except UnicodeDecodeError as exc:
                last = exc
        raise UnicodeDecodeError(  # pragma: no cover - all encodings failed
            "sgotools", b"", 0, 1, f"could not decode {path}: {last}"
        )

    def __repr__(self) -> str:  # pragma: no cover - display only
        return f"Snapshot({str(self.path)!r}, retrieved={self.retrieved!r})"
