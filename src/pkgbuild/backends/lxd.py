"""LXD backend: each build runs in a fresh, ephemeral system container."""

from __future__ import annotations

import time
from pathlib import Path

from .base import Backend


class LXDBackend(Backend):
    name = "lxd"
    supports_snap = True  # system containers can run snapd

    def start(self) -> None:
        self.run_host(["lxc", "launch", self.image, self.instance, "--ephemeral"])
        for key, value in self.env.items():
            self.run_host(["lxc", "config", "set", self.instance, f"environment.{key}", value])
        self._wait_for_network()

    def _wait_for_network(self, timeout: int = 60) -> None:
        if self.dry_run:
            return
        deadline = time.time() + timeout
        while time.time() < deadline:
            probe = self.run_host(
                ["lxc", "exec", self.instance, "--", "getent", "hosts", "archive.ubuntu.com"], check=False
            )
            if probe.returncode == 0:
                return
            time.sleep(2)
        raise TimeoutError(f"{self.instance} has no network after {timeout}s")

    def exec(self, argv: list[str]) -> None:
        self.run_host(["lxc", "exec", self.instance, "--", *argv])

    def push(self, src: Path, dest: str) -> None:
        self.exec(["mkdir", "-p", dest])
        self.pipe(
            ["tar", "-C", str(src), "--exclude=.git", "-cf", "-", "."],
            ["lxc", "exec", self.instance, "--", "tar", "-C", dest, "-xf", "-"],
        )

    def pull(self, src: str, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        self.pipe(
            ["lxc", "exec", self.instance, "--", "tar", "-C", src, "-cf", "-", "."],
            ["tar", "-C", str(dest), "-xf", "-"],
        )

    def destroy(self) -> None:
        self.run_host(["lxc", "delete", "--force", self.instance], check=False)
