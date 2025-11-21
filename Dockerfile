# Multi-stage build for the Transmission + Flask API
FROM debian:bookworm-slim

# Install dependencies: transmission, python3, gunicorn, and Flask
RUN apt-get update && apt-get install -y --no-install-recommends \
    transmission-daemon \
    transmission-cli \
    python3 \
    python3-pip \
    && rm -rf /var/lib/apt/lists/*

# Set working directory
WORKDIR /app

# Copy project files
COPY rtorrent.py /app/rtorrent.py
COPY api.py /app/api.py

# Install Python dependencies
RUN pip install --no-cache-dir flask gunicorn --break-system-packages

# Create Transmission data and config directories
# Transmission (Debian package) stores runtime config in the 'info' subdir.
RUN mkdir -p /var/lib/transmission-daemon/downloads/{tv,film} && \
    mkdir -p /var/lib/transmission-daemon/info
COPY post-torrent.sh /var/lib/transmission-daemon/move-completed.sh
RUN chmod +x /var/lib/transmission-daemon/move-completed.sh
# Copy transmission settings into the daemon's info directory
COPY transmission-settings.json /var/lib/transmission-daemon/info/settings.json

# Copy and make executable the entrypoint script
COPY entrypoint.sh /app/entrypoint.sh
RUN chmod +x /app/entrypoint.sh

# Expose port 5000 for the Flask API and 9091 for Transmission RPC
EXPOSE 5000 9091

# Health check
HEALTHCHECK --interval=30s --timeout=3s --start-period=5s --retries=3 \
    CMD python3 -c "import requests; requests.get('http://127.0.0.1:5000/ping')" || exit 1

# Run the entrypoint script
CMD ["/app/entrypoint.sh"]
