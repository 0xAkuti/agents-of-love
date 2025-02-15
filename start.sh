#!/bin/bash

# Function to handle cleanup
cleanup() {
    echo "Shutting down services..."
    jobs -p | xargs -r kill
    exit 0
}

# Set up signal handling
trap cleanup SIGINT SIGTERM

echo "Starting API ..."
# Start the FastAPI server in the background with aggressive memory optimizations
python -m uvicorn src.server.api:app \
    --host 0.0.0.0 \
    --port 8080 \
    --workers 1 &
API_PID=$!

echo "Starting Discord bot..."
# Start the Discord bot in the background
python run.py &
BOT_PID=$!

echo "Services started. Waiting..."

# Print initial memory usage
echo "Initial memory usage:"
free -h || true

# Wait for any process to exit
wait -n

# If we get here, one of the processes exited
echo "A service exited unexpectedly. Showing memory usage..."
free -h || true
echo "Process info:"
ps aux | grep python || true
echo "Shutting down..."
cleanup