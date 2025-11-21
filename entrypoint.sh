#!/bin/bash
set -e

# Start transmission-daemon in the background
echo "Starting transmission-daemon..."
transmission-daemon --foreground --config-dir /var/lib/transmission-daemon &
TRANSMISSION_PID=$!

# Give transmission a moment to start
sleep 2

# Start the Flask API using gunicorn
echo "Starting Flask API..."
exec gunicorn \
    --bind 0.0.0.0:5000 \
    --workers 4 \
    --worker-class sync \
    --timeout 30 \
    --access-logfile - \
    --error-logfile - \
    api:app
