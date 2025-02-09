#!/bin/bash

# Start the FastAPI server in the background
python api.py &

# Start the Discord bot
python bot.py