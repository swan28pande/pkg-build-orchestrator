# pkg-build-orchestrator

A Python CLI that builds a Python project into **wheel**, **deb** and **snap** packages inside a fresh, ephemeral LXD container, so every build starts from the same clean base image.

```bash
pip install .
pkgbuild plan examples/hello
pkgbuild build examples/hello --targets wheel,deb,snap
ls dist-pkgbuild/
# hello-pkgbuild_0.1.0_amd64.deb  hello_pkgbuild-0.1.0-py3-none-any.whl
# hello-pkgbuild_0.1.0_amd64.snap  requirements.lock
```

## How it works

1. Read `[project]` and `[tool.pkgbuild]` from `pyproject.toml`.
2. Launch an ephemeral container (`lxc launch ubuntu:24.04 --ephemeral`), with `SOURCE_DATE_EPOCH` set to the last commit time and `PYTHONHASHSEED=0`.
3. Copy the source in, install the toolchain, and resolve all dependencies into a pinned `requirements.lock`.
4. Build each target:
   - **wheel**: `python -m build --wheel`
   - **deb**: a self-contained venv under `/opt/<name>` with the pinned deps, console scripts linked into `/usr/bin`, packed with `dpkg-deb`
   - **snap**: a generated `snapcraft.yaml` (python plugin, `core24`), built with `snapcraft pack --destructive-mode`
5. Copy the artifacts back to `--out` and delete the container.

## Configuration

```toml
[tool.pkgbuild]
image = "ubuntu:24.04"            # LXD/Docker image
targets = ["wheel", "deb", "snap"]
apt-packages = ["libffi-dev"]     # extra build-time packages
```

## CLI

```
pkgbuild plan  [PROJECT]
pkgbuild build [PROJECT] [-t wheel,deb,snap] [-b lxd|docker] [-i IMAGE] [-o OUT] [-n]
```

- `-b docker` uses Docker instead of LXD. It's faster, but it can't build snaps because they need snapd.
- `-n` / `--dry-run` prints every host command without running it.

## Docker

The `Dockerfile` packages the CLI itself. Mount the Docker socket to use it with the docker backend:

```bash
docker build -t pkgbuild .
docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD:/work" -w /work \
  pkgbuild build examples/hello -b docker -t wheel,deb
```

## CI

`.github/workflows/build.yml` sets up LXD on a GitHub runner, builds the example project for all three targets, and uploads the packages as an artifact.

## License

MIT
