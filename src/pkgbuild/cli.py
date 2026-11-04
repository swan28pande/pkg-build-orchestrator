"""Command-line entry point."""

from __future__ import annotations

import argparse
import sys
from pathlib import Path

from . import __version__
from .backends import BACKENDS
from .config import load_config
from .orchestrator import run_build


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(prog="pkgbuild", description=__doc__)
    parser.add_argument("--version", action="version", version=f"%(prog)s {__version__}")
    sub = parser.add_subparsers(dest="command", required=True)

    plan = sub.add_parser("plan", help="show what would be built from pyproject.toml")
    plan.add_argument("project", nargs="?", default=".", type=Path)

    build = sub.add_parser("build", help="build packages in an isolated container")
    build.add_argument("project", nargs="?", default=".", type=Path)
    build.add_argument("-t", "--targets", help="comma-separated: wheel,deb,snap (default: from pyproject)")
    build.add_argument("-b", "--backend", choices=sorted(BACKENDS), default="lxd")
    build.add_argument("-i", "--image", help="container image (default: from pyproject or ubuntu:24.04)")
    build.add_argument("-o", "--out", type=Path, default=Path("dist-pkgbuild"))
    build.add_argument("-n", "--dry-run", action="store_true", help="print commands without running them")

    args = parser.parse_args(argv)
    try:
        cfg = load_config(args.project)
        if args.command == "plan":
            print(f"name:         {cfg.name}")
            print(f"version:      {cfg.version}")
            print(f"image:        {cfg.image}")
            print(f"targets:      {', '.join(cfg.targets)}")
            print(f"dependencies: {', '.join(cfg.dependencies) or '(none)'}")
            print(f"scripts:      {', '.join(cfg.scripts) or '(none)'}")
            return 0

        if args.image:
            cfg.image = args.image
        targets = args.targets.split(",") if args.targets else cfg.targets
        run_build(cfg, args.backend, targets, args.out.resolve(), args.dry_run)
        return 0
    except Exception as exc:  # noqa: BLE001 - surface any failure as a clean CLI error
        print(f"error: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
