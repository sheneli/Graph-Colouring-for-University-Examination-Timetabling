"""Shared helpers for experiment scripts."""

from __future__ import annotations

import csv
import gzip
import json
import platform
import subprocess
import sys
import tomllib
from importlib import metadata
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
RESULTS = ROOT / "results"
FIGURES = ROOT / "figures"


def cli_config() -> dict:
    """Parse ``--config`` (default configs/experiment.toml) and return the loaded config."""
    import argparse
    ap = argparse.ArgumentParser()
    ap.add_argument("--config", default=str(ROOT / "configs" / "experiment.toml"))
    args = ap.parse_args()
    return load_config(args.config)


def out_dir(cfg: dict) -> Path:
    d = ROOT / cfg.get("output", {}).get("dir", "results")
    d.mkdir(parents=True, exist_ok=True)
    return d


def load_config(path: str | Path = ROOT / "configs" / "experiment.toml") -> dict:
    with open(path, "rb") as fh:
        cfg = tomllib.load(fh)
    cfg["data"]["toronto_dir"] = str((ROOT / cfg["data"]["toronto_dir"]).resolve())
    return cfg


def write_csv(path: Path, rows: list[dict]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    if not rows:
        path.write_text("")
        return
    opener = gzip.open if path.suffix == ".gz" else open
    with opener(path, "wt", newline="") as fh:
        w = csv.DictWriter(fh, fieldnames=list(rows[0].keys()))
        w.writeheader()
        w.writerows(rows)


def environment() -> dict:
    def ver(pkg):
        try:
            return metadata.version(pkg)
        except metadata.PackageNotFoundError:
            return None

    cpu = ""
    try:
        cpu = subprocess.run(["lscpu"], capture_output=True, text=True).stdout
        cpu = next((l.split(":", 1)[1].strip() for l in cpu.splitlines() if l.startswith("Model name")), "")
    except Exception:  # pragma: no cover
        pass
    try:
        import os
        ncpu = os.cpu_count()
        mem = int(open("/proc/meminfo").read().split()[1]) // 1024
    except Exception:  # pragma: no cover
        ncpu, mem = None, None
    return {
        "python": sys.version.split()[0], "implementation": platform.python_implementation(),
        "platform": platform.platform(), "cpu_model": cpu, "logical_cpus": ncpu, "mem_mib": mem,
        "packages": {p: ver(p) for p in ["numpy", "scipy", "ortools", "networkx", "matplotlib",
                                         "pandas", "pytest", "python-docx"]},
    }


def save_json(path: Path, obj) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(obj, indent=2, default=str))
