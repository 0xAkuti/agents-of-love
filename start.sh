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
# Start the FastAPI server in the background
python -m uvicorn src.server.api:app --host 0.0.0.0 --port 8080 &
API_PID=$!

echo "Starting Discord bot..."
# Start the Discord bot in the background
python run.py &
BOT_PID=$!

echo "Services started. Waiting..."

# Wait for any process to exit
wait -n

# If we get here, one of the processes exited
echo "A service exited unexpectedly. Shutting down..."
cleanup