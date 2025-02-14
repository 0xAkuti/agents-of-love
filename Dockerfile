FROM python:3.11-slim

    # Add metadata labels
LABEL org.opencontainers.image.source="https://github.com/0xAkuti/agents-of-love"
LABEL org.opencontainers.image.description="Agents of Love - WIP - v0.0.1"
LABEL org.opencontainers.image.licenses="MIT"

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    python3-dev \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements first to leverage Docker cache
COPY requirements.txt .

# Install Python dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Copy the rest of the application
COPY . .

# Environment variables will be provided at runtime
ENV OPENAI_API_KEY=""
ENV DISCORD_TOKEN=""
ENV CDP_API_KEY_NAME=""
ENV CDP_API_KEY_PRIVATE_KEY=""
ENV NETWORK_ID=""
# Set PYTHONPATH to include the app directory
ENV PYTHONPATH=/app

# Expose the API port
EXPOSE 8000

# Use a shell script to start both services
COPY start.sh .
RUN chmod +x start.sh

CMD ["./start.sh"]