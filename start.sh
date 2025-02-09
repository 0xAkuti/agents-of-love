#!/bin/bash
echo "Starting API ..."
# Start the FastAPI server in the background
python api.py &
echo "Starting Discord bot..."
# Start the Discord bot
python bot.py
echo "Done!"