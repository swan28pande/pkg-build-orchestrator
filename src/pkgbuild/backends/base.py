"""Common interface for isolated build environments."""

from __future__ import annotations

import shlex
import subprocess
import uuid
from abc import ABC, abstractmethod
from pathlib import Path


class Backend(ABC):
    """An ephemeral build environment: start, run commands, copy files, destroy."""

    name: str = "base"
    supports_snap: bool = False

    def __init__(self, image: str, dry_run: bool = False, env: dict[str, str] | None = None):
        self.image = image
        self.dry_run = dry_run
        self.env = env or {}
        self.instance = f"pkgbuild-{uuid.uuid4().hex[:8]}"

    def run_host(self, argv: list[str], check: bool = True) -> subprocess.CompletedProcess:
        print("+", shlex.join(argv), flush=True)
        if self.dry_run:
            return subprocess.CompletedProcess(argv, 0, "", "")
        return subprocess.run(argv, check=check, text=True)

    def pipe(self, producer: list[str], consumer: list[str]) -> None:
        """Run `producer | consumer` on the host (used to stream tarballs)."""
        print("+", shlex.join(producer), "|", shlex.join(consumer), flush=True)
        if self.dry_run:
            return
        src = subprocess.Popen(producer, stdout=subprocess.PIPE)
        dst = subprocess.run(consumer, stdin=src.stdout)
        src.stdout.close()  # type: ignore[union-attr]
        if src.wait() or dst.returncode:
            raise subprocess.CalledProcessError(src.returncode or dst.returncode, producer + ["|"] + consumer)

    def sh(self, script: str, cwd: str = "/src") -> None:
        """Run a shell snippet inside the environment."""
        self.exec(["bash", "-euo", "pipefail", "-c", f"cd {shlex.quote(cwd)} && {script}"])

    @abstractmethod
    def start(self) -> None: ...

    @abstractmethod
    def exec(self, argv: list[str]) -> None: ...

    @abstractmethod
    def push(self, src: Path, dest: str) -> None:
        """Copy a host directory into the environment."""

    @abstractmethod
    def pull(self, src: str, dest: Path) -> None:
        """Copy a directory out of the environment."""

    @abstractmethod
    def destroy(self) -> None: ...

    def __enter__(self) -> "Backend":
        self.start()
        return self

    def __exit__(self, *exc) -> None:
        self.destroy()
