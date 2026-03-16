FROM python:3.12-slim

WORKDIR /app

# System dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    gcc \
    libpq-dev \
    curl \
    && rm -rf /var/lib/apt/lists/*

# Install Python dependencies
# stub app/ package so editable install resolves before source copy (layer cache)
COPY pyproject.toml .
RUN pip install --no-cache-dir --upgrade pip && \
    mkdir -p app && touch app/__init__.py && \
    pip install --no-cache-dir -e .[dev]

COPY . .

EXPOSE 8000
