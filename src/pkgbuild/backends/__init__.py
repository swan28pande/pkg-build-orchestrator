from .base import Backend
from .docker import DockerBackend
from .lxd import LXDBackend

BACKENDS: dict[str, type[Backend]] = {"lxd": LXDBackend, "docker": DockerBackend}

__all__ = ["Backend", "BACKENDS", "DockerBackend", "LXDBackend"]
