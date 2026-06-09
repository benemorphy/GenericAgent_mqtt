# syntax=docker/dockerfile:1
# Dockerfile for GenericAgent (GA) - Multi-stage build

# ── Stage 1: Build ──
FROM python:3.11-slim AS builder

WORKDIR /build

# Install build deps
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy project metadata first (layer caching)
COPY pyproject.toml ./
COPY requirements.txt ./

# Install dependencies
RUN pip install --no-cache-dir --user -r requirements.txt

# Copy source code
COPY GA/ GA/
COPY Mqtt_bbs_client/ Mqtt_bbs_client/
COPY Mqtt_bbs_server/ Mqtt_bbs_server/

# Install project as editable
RUN pip install --no-cache-dir --user -e .


# ── Stage 2: Runtime ──
FROM python:3.11-slim AS runtime

# Create non-root user
RUN groupadd -r ga && useradd -r -g ga -d /app -s /bin/false ga

WORKDIR /app

# Copy installed packages from builder
COPY --from=builder /root/.local /root/.local

# Make sure scripts are in PATH
ENV PATH=/root/.local/bin:$PATH

# Expose default ports
EXPOSE 8000 8001

# Healthcheck
HEALTHCHECK --interval=30s --timeout=5s --retries=3 \
    CMD python -c "import ga; print('ok')" || exit 1

USER ga

ENTRYPOINT ["python", "-m", "ga_cli.cli"]
