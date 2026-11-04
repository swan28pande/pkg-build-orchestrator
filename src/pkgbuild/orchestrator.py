"""Drive a full build: start environment, push source, build targets, pull artifacts."""

from __future__ import annotations

import subprocess
import time
from pathlib import Path

from .backends import BACKENDS
from .config import BuildConfig
from .targets import OUT, TARGETS, prepare


def source_date_epoch(project_dir: Path) -> str:
    """Use the last commit time so rebuilds of the same commit produce identical output."""
    try:
        out = subprocess.run(
            ["git", "-C", str(project_dir), "log", "-1", "--format=%ct"],
            capture_output=True, text=True, check=True,
        )
        return out.stdout.strip() or str(int(time.time()))
    except (subprocess.CalledProcessError, FileNotFoundError):
        return str(int(time.time()))


def run_build(cfg: BuildConfig, backend_name: str, targets: list[str], out_dir: Path, dry_run: bool) -> None:
    unknown = [t for t in targets if t not in TARGETS]
    if unknown:
        raise ValueError(f"Unknown target(s): {', '.join(unknown)}. Choose from {', '.join(TARGETS)}")

    if "snap" in targets and not BACKENDS[backend_name].supports_snap:
        raise ValueError(f"snap builds need the lxd backend (got '{backend_name}')")

    env = {
        "SOURCE_DATE_EPOCH": source_date_epoch(cfg.project_dir),
        "PYTHONHASHSEED": "0",
        "PIP_NO_CACHE_DIR": "1",
        "PIP_DISABLE_PIP_VERSION_CHECK": "1",
    }
    backend = BACKENDS[backend_name](cfg.image, dry_run=dry_run, env=env)
    print(f"==> {cfg.name} {cfg.version}: {', '.join(targets)} on {backend.name} ({cfg.image})")

    with backend:
        backend.push(cfg.project_dir, "/src")
        prepare(backend, cfg)
        for target in targets:
            print(f"==> building {target}")
            TARGETS[target](backend, cfg)
        backend.pull(OUT, out_dir)

    print(f"==> artifacts in {out_dir}")
