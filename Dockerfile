# Imagen de MarkForge: solo la CLI, sin dependencias de runtime (dependencies = []).
# Base fijada por digest (indice multi-arquitectura); Dependabot (docker) la actualiza.
FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir .

FROM python:3.12-slim@sha256:5e2bdb1b0d542d5039cffb8181c65930093949194a65c365dfb1b0fe13a4fa5b
ENV PATH="/opt/venv/bin:${PATH}" \
    PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1
RUN useradd --system --uid 10001 --no-create-home --shell /usr/sbin/nologin markforge \
    && mkdir /work \
    && chown markforge /work
COPY --from=builder /opt/venv /opt/venv
USER 10001
WORKDIR /work
ENTRYPOINT ["markforge"]
