# ==============================================================================
# TOKI Backend — Production & Demo Container
# Target runtime: Python 3.12 on Debian slim
# ==============================================================================

FROM python:3.12-slim AS runtime

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PYTHONPATH=/workspace

WORKDIR /workspace

# Install system utilities needed for healthcheck and database connectivity
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install python dependencies
COPY requirements.txt /workspace/
RUN pip install --no-cache-dir -r requirements.txt

# Copy application source code
COPY app/ /workspace/app/
COPY README.md /workspace/
COPY pyproject.toml /workspace/

# Create a non-root user for security
RUN useradd -m -u 1000 toki && chown -R toki:toki /workspace
USER toki

EXPOSE 8000

# Default entry point
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "8000"]
