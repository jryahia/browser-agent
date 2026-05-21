FROM python:3.11-slim

# Install Playwright dependencies
RUN apt-get update && apt-get install -y \
    curl \
    wget \
    gnupg \
    ca-certificates \
    && rm -rf /var/lib/apt/lists/*

# Install Chrome and dependencies for Playwright
RUN pip install --no-cache-dir playwright && \
    playwright install chromium && \
    playwright install-deps chromium

WORKDIR /app

# Copy project files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Default command (can be overridden)
CMD ["python", "main.py", "--help"]
