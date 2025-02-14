#!/bin/bash
echo "Starting API ..."
# Start the FastAPI server in the background
python src/server/api.py &
echo "Starting Discord bot..."
# Start the Discord bot
python src/bot.py
echo "Done!"