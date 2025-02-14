#!/bin/bash

# Function to handle cleanup
cleanup() {
    echo "Shutting down services..."
    if [ -n "$API_PID" ] && ps -p $API_PID > /dev/null; then
        kill $API_PID
    fi
    if [ -n "$BOT_PID" ] && ps -p $BOT_PID > /dev/null; then
        kill $BOT_PID
    fi
    exit 0
}

# Set up signal handling
trap cleanup SIGINT SIGTERM

echo "Starting API ..."
# Start the FastAPI server in the background
python -m uvicorn src.server.api:app --host 0.0.0.0 --port 8000 --no-access-log &
API_PID=$!

echo "Starting Discord bot..."
# Start the Discord bot in the background
python run.py > bot.log 2>&1 &
BOT_PID=$!

echo "Services started. Waiting..."

# Wait for any process to exit
wait -n

# If we get here, one of the processes exited
echo "A service exited unexpectedly. Showing bot logs..."
if [ -f bot.log ]; then
    echo "=== Bot Logs ==="
    tail -n 50 bot.log
    echo "================"
fi

cleanup