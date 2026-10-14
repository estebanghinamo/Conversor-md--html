# Imagen de MarkForge: solo la CLI, sin dependencias de runtime (dependencies = []).
# Base fijada por digest (indice multi-arquitectura); Dependabot (docker) la actualiza.
FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1 AS builder
WORKDIR /build
COPY pyproject.toml README.md ./
COPY src ./src
RUN python -m venv /opt/venv \
    && /opt/venv/bin/pip install --no-cache-dir .

FROM python:3.12-slim@sha256:a6e34c598f2467ed0e9a8d349809fcd8b5c603269512df273a0bb1784edc11b1
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
