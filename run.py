import asyncio
import os
from src.bot import start_bot, handle_signals

async def run_bot():
    """Run the Discord bot"""
    token = os.getenv("DISCORD_API_TOKEN")
    if not token:
        raise ValueError("DISCORD_API_TOKEN environment variable is not set")
    
    handle_signals()
    await start_bot(token)

if __name__ == "__main__":
    asyncio.run(run_bot())