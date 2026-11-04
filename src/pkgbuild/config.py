"""Read project metadata and build settings from pyproject.toml."""

from __future__ import annotations

import re
import tomllib
from dataclasses import dataclass, field
from pathlib import Path

DEFAULT_IMAGE = "ubuntu:24.04"
DEFAULT_TARGETS = ["wheel"]


@dataclass
class BuildConfig:
    name: str
    version: str
    description: str
    dependencies: list[str]
    requires_python: str | None
    scripts: dict[str, str]
    project_dir: Path
    image: str = DEFAULT_IMAGE
    targets: list[str] = field(default_factory=lambda: list(DEFAULT_TARGETS))
    apt_packages: list[str] = field(default_factory=list)

    @property
    def deb_name(self) -> str:
        return re.sub(r"[^a-z0-9.+-]", "-", self.name.lower())


def load_config(project_dir: Path) -> BuildConfig:
    """Parse [project] and optional [tool.pkgbuild] tables."""
    path = project_dir / "pyproject.toml"
    if not path.exists():
        raise FileNotFoundError(f"No pyproject.toml in {project_dir}")
    data = tomllib.loads(path.read_text())

    project = data.get("project") or {}
    if "name" not in project or "version" not in project:
        raise ValueError("pyproject.toml must set [project].name and a static [project].version")

    tool = data.get("tool", {}).get("pkgbuild", {})
    return BuildConfig(
        name=project["name"],
        version=str(project["version"]),
        description=project.get("description", ""),
        dependencies=list(project.get("dependencies", [])),
        requires_python=project.get("requires-python"),
        scripts=dict(project.get("scripts", {})),
        project_dir=project_dir.resolve(),
        image=tool.get("image", DEFAULT_IMAGE),
        targets=list(tool.get("targets", DEFAULT_TARGETS)),
        apt_packages=list(tool.get("apt-packages", [])),
    )
