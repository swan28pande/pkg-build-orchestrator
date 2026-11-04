"""Build steps for each output format, executed inside a backend."""

from __future__ import annotations

import shlex
import textwrap

from .backends import Backend
from .config import BuildConfig

OUT = "/out"
VENV = "/opt/pkgbuild-venv"


def prepare(backend: Backend, cfg: BuildConfig) -> None:
    """Install the toolchain and resolve dependencies into a lock file."""
    apt = " ".join(["python3", "python3-venv", "python3-pip", "git", *cfg.apt_packages])
    backend.sh(
        "export DEBIAN_FRONTEND=noninteractive && apt-get update -qq && "
        f"apt-get install -y -qq --no-install-recommends {apt}",
        cwd="/",
    )
    backend.sh(f"python3 -m venv {VENV} && {VENV}/bin/pip install -q --upgrade pip build", cwd="/")
    backend.sh(f"mkdir -p {OUT}")
    # Resolve the full dependency tree in a throwaway venv and pin it.
    backend.sh(
        "python3 -m venv /tmp/resolve && /tmp/resolve/bin/pip install -q . && "
        f"/tmp/resolve/bin/pip freeze --exclude {shlex.quote(cfg.name)} > {OUT}/requirements.lock && "
        f"cp {OUT}/requirements.lock requirements.lock"
    )


def build_wheel(backend: Backend, cfg: BuildConfig) -> None:
    backend.sh(f"{VENV}/bin/python -m build --wheel --outdir {OUT} .")


def build_deb(backend: Backend, cfg: BuildConfig) -> None:
    """Package the project plus its pinned deps as a self-contained venv under /opt."""
    pkg, prefix = cfg.deb_name, f"/opt/{cfg.deb_name}"
    root = "/tmp/debroot"
    control = textwrap.dedent(
        f"""\
        Package: {pkg}
        Version: {cfg.version}
        Architecture: $(dpkg --print-architecture)
        Maintainer: pkgbuild <noreply@localhost>
        Depends: python3
        Description: {cfg.description or cfg.name}
        """
    )
    links = " && ".join(
        f"ln -sf {prefix}/bin/{name} {root}/usr/bin/{name}" for name in cfg.scripts
    ) or "true"
    backend.sh(
        f"python3 -m venv {root}{prefix} && "
        f"{root}{prefix}/bin/pip install -q --no-deps -r {OUT}/requirements.lock && "
        f"{root}{prefix}/bin/pip install -q --no-deps . && "
        # Rewrite shebangs/venv paths so the venv works from its final location.
        f"grep -rlI '{root}{prefix}' {root}{prefix} | xargs -r sed -i 's#{root}{prefix}#{prefix}#g' && "
        f"mkdir -p {root}/DEBIAN {root}/usr/bin && {links} && "
        f'cat > {root}/DEBIAN/control <<EOF\n{control}EOF\n'
        f"dpkg-deb --root-owner-group --build {root} {OUT}/{pkg}_{cfg.version}_$(dpkg --print-architecture).deb"
    )


def build_snap(backend: Backend, cfg: BuildConfig) -> None:
    if not backend.supports_snap:
        raise RuntimeError(f"snap builds need the lxd backend (got '{backend.name}')")
    apps = "\n".join(
        f"  {name}:\n    command: bin/{name}" for name in cfg.scripts
    ) or "  noop:\n    command: bin/python3"
    snapcraft = textwrap.dedent(
        f"""\
        name: {cfg.deb_name}
        version: '{cfg.version}'
        summary: {(cfg.description or cfg.name)[:78]}
        description: {cfg.description or cfg.name}
        base: core24
        confinement: strict
        grade: stable
        parts:
          {cfg.deb_name}:
            plugin: python
            source: .
            python-requirements: [requirements.lock]
        apps:
        """
    ) + apps + "\n"
    backend.sh(
        "snap wait system seed.loaded && snap install snapcraft --classic && "
        f"mkdir -p snap && cat > snap/snapcraft.yaml <<'EOF'\n{snapcraft}EOF\n"
        f"snapcraft pack --destructive-mode --output {OUT}/"
    )


TARGETS = {"wheel": build_wheel, "deb": build_deb, "snap": build_snap}
