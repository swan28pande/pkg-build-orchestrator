# Runs the orchestrator itself in a container. Use with the docker backend by
# mounting the host Docker socket:
#   docker run --rm -v /var/run/docker.sock:/var/run/docker.sock -v "$PWD:/work" -w /work \
#     pkgbuild build -b docker -t wheel,deb
FROM python:3.12-slim
RUN apt-get update && apt-get install -y --no-install-recommends docker.io git && rm -rf /var/lib/apt/lists/*
COPY . /app
RUN pip install --no-cache-dir /app
ENTRYPOINT ["pkgbuild"]
