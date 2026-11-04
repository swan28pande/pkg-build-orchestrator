"""Docker backend: faster for wheel/deb builds; cannot build snaps (no snapd)."""

from __future__ import annotations

from pathlib import Path

from .base import Backend


class DockerBackend(Backend):
    name = "docker"
    supports_snap = False

    def start(self) -> None:
        env_flags = [f for k, v in self.env.items() for f in ("-e", f"{k}={v}")]
        self.run_host(
            ["docker", "run", "-d", "--rm", "--name", self.instance, *env_flags, self.image, "sleep", "infinity"]
        )

    def exec(self, argv: list[str]) -> None:
        self.run_host(["docker", "exec", self.instance, *argv])

    def push(self, src: Path, dest: str) -> None:
        self.exec(["mkdir", "-p", dest])
        self.run_host(["docker", "cp", f"{src}/.", f"{self.instance}:{dest}"])

    def pull(self, src: str, dest: Path) -> None:
        dest.mkdir(parents=True, exist_ok=True)
        self.run_host(["docker", "cp", f"{self.instance}:{src}/.", str(dest)])

    def destroy(self) -> None:
        self.run_host(["docker", "rm", "-f", self.instance], check=False)
