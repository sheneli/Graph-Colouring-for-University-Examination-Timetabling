"""Download the Toronto (Carter) benchmark, version I, and verify SHA-256 checksums.

The files are fetched from a public GitHub mirror because the original University of
Nottingham host was not reachable from the build environment. Checksums in
data/SHA256SUMS were computed from the copies used for every reported experiment, so a
mismatch means a different file version and results may not reproduce.

Usage: python scripts/get_data.py [--source URL_PREFIX]
"""

from __future__ import annotations

import argparse
import hashlib
import sys
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
DEST = ROOT / "data" / "raw" / "toronto"
SUMS = ROOT / "data" / "SHA256SUMS"
MIRROR = ("https://raw.githubusercontent.com/Sajib-006/"
          "Eaxam-Scheduler-Using-Graph-Coloring-and-Kempe-Chain/master/Toronto/")


def sha256(path: Path) -> str:
    return hashlib.sha256(path.read_bytes()).hexdigest()


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--source", default=MIRROR, help="URL prefix ending in '/'")
    args = ap.parse_args()
    DEST.mkdir(parents=True, exist_ok=True)
    expected = {}
    for line in SUMS.read_text().splitlines():
        if line.strip():
            digest, name = line.split()
            expected[name] = digest
    bad = 0
    for name, digest in sorted(expected.items()):
        target = DEST / name
        if not target.exists():
            print(f"downloading {name}")
            urllib.request.urlretrieve(args.source + name, target)
        ok = sha256(target) == digest
        bad += not ok
        print(f"{'OK ' if ok else 'BAD'} {name}")
    print("all files verified" if bad == 0 else f"{bad} file(s) failed verification")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
