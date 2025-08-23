FROM python:3.11-slim

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    g++ \
    curl \
    wget \
    gnupg \
    ca-certificates \
    git \
    && rm -rf /var/lib/apt/lists/*

# Install Go 1.24.0 (required for latest Katana)
RUN wget https://go.dev/dl/go1.24.0.linux-amd64.tar.gz && \
    tar -C /usr/local -xzf go1.24.0.linux-amd64.tar.gz && \
    rm go1.24.0.linux-amd64.tar.gz

# Add Go to PATH
ENV PATH="/usr/local/go/bin:${PATH}"

# Install Katana directly using Go
RUN go install -v github.com/projectdiscovery/katana/cmd/katana@latest

# Fix permissions for Katana binary
RUN chmod +x /root/go/bin/katana

# Create appuser and install Katana for them
RUN groupadd -r appuser && useradd -r -g appuser -m -s /bin/bash appuser

# Install Katana for appuser
USER appuser
RUN go install -v github.com/projectdiscovery/katana/cmd/katana@latest

# Switch back to root for remaining operations
USER root

# Add both Go bin directories to PATH
ENV PATH="/root/go/bin:/home/appuser/go/bin:${PATH}"

# Copy requirements first for better caching
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .
RUN chown -R appuser:appuser /app

USER appuser

# Default command for exposure analysis
CMD ["python", "run_complete_exposure_analysis.py"] 