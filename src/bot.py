import asyncio
import logging
import logging.handlers
import os
import signal
from typing import Dict, List

import dotenv
import discord

from src.models.model import SimpleUser

dotenv.load_dotenv(override=True)

from autogen_core import TRACE_LOGGER_NAME

logger = logging.getLogger(TRACE_LOGGER_NAME)
logger.setLevel(logging.DEBUG)

logger = logging.getLogger("aol")
logger.setLevel(logging.INFO)
logging.getLogger("discord.http").setLevel(logging.INFO)

handler = logging.handlers.RotatingFileHandler(
    filename="aol.log",
    encoding="utf-8",
    maxBytes=32 * 1024 * 1024,  # 32 MiB
    backupCount=5,  # Rotate through 5 files
)
dt_fmt = "%Y-%m-%d %H:%M:%S"
formatter = logging.Formatter(
    "[{asctime}] [{levelname:<8}] {name}: {message}", dt_fmt, style="{"
)
handler.setFormatter(formatter)
logger.addHandler(handler)
logger.addHandler(logging.StreamHandler())

#import after initializing the logger
from src.agents.date_manager import DateManager

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
client = discord.Client(intents=intents)

# Store date managers for each user
date_managers: Dict[int, DateManager] = {}

def split_message(message: str, max_length: int = 2000) -> List[str]:
    """Split a message into chunks of maximum length while preserving word boundaries."""
    if len(message) <= max_length:
        return [message]
        
    chunks = []
    current_chunk = ""
    
    # Split by lines first to preserve formatting
    lines = message.split('\n')
    
    for line in lines:
        # If the line itself is too long, split by words
        if len(line) > max_length:
            words = line.split(' ')
            for word in words:
                if len(current_chunk) + len(word) + 1 <= max_length:
                    current_chunk += (word + ' ')
                else:
                    chunks.append(current_chunk.strip())
                    current_chunk = word + ' '
            continue
            
        # If adding the line would exceed max_length, start a new chunk
        if len(current_chunk) + len(line) + 1 > max_length:
            chunks.append(current_chunk.strip())
            current_chunk = line + '\n'
        else:
            current_chunk += line + '\n'
            
    # Add the last chunk if it's not empty
    if current_chunk:
        chunks.append(current_chunk.strip())
        
    return chunks

async def save_all_states():
    """Save states for all active date managers."""
    logger.info("Saving states for all date managers...")
    for manager in date_managers.values():
        try:
            await manager.save_state()
        except Exception as e:
            logger.error(f"Error saving state for user {manager.user.id}: {e}")
    logger.info("All states saved.")

async def get_date_manager(user: discord.User) -> DateManager:
    """Get or create a date manager for a user."""
    if user.id not in date_managers:
        # Create new date manager
        date_manager = DateManager(user=SimpleUser(id=user.id, name=user.display_name))
        # Initialize memory and load previous state
        await date_manager.initialize()
        date_managers[user.id] = date_manager
    return date_managers[user.id]

@client.event
async def on_message(message: discord.Message):
    logger.info(
        {"message": message.content, "author": message.author, "id": message.id}
    )
    if message.author.id == client.user.id: # Not talking to myself
        return
    if message.author.bot: # Not talking to other bots
        return
    # Show typing indicator while processing
    async with message.channel.typing():
        # Get or create date manager for this user
        date_manager = await get_date_manager(message.author)
        date_manager.date_started_callback = lambda: asyncio.create_task(message.channel.send(f"Great, I am organizing the date for you. I'll let you know how it went in a bit."))
        
        # Get response from date manager
        response = await date_manager.get_manager_response(f'{message.author.display_name}: {message.content}')
        
        # Split response into chunks and send each chunk
        chunks = split_message(response)
        for chunk in chunks:
            await message.reply(chunk)

@client.event
async def on_reaction_add(reaction, user):
    message = reaction.message
    logger.info(
        {
            "message": message.content,
            "author": message.author,
            "id": message.id,
            "reaction": reaction.emoji,
            "reactor": user,
        }
    )

@client.event
async def on_ready():
    logger.info("Logged in as %s", client.user.name)

@client.event
async def on_member_join(member):
    logger.info(f"User {member.name} joined the server")
    await member.send(f"Hey {member.name}, welcome to Virtura. I'm Nova, your date manager. I'll help you find love in the metaverse.")

async def cleanup():
    """Cleanup function to save states and close connections."""
    logger.info("Starting cleanup...")
    
    # Save all states
    await save_all_states()
    
    # Close the Discord connection
    if not client.is_closed():
        await client.close()
    
    logger.info("Cleanup complete.")

def handle_signals():
    """Set up signal handlers."""
    loop = asyncio.get_event_loop()
    loop.add_signal_handler(signal.SIGINT, lambda: asyncio.create_task(cleanup()))
    loop.add_signal_handler(signal.SIGTERM, lambda: asyncio.create_task(cleanup()))
    logger.info("Signal handlers registered")

async def start_bot(token: str):
    """Start the bot with the given token."""
    try:
        await client.start(token)
    finally:
        await cleanup()

def main():
    logging.info("Starting bot...")
    
    discord_token = os.getenv("DISCORD_API_TOKEN")
    if not discord_token:
        logger.error("DISCORD_API_TOKEN environment variable is not set")
        exit(1)
        
    handle_signals()
    logger.info("Starting Discord client...")
    
    try:
        asyncio.run(start_bot(discord_token))
    except KeyboardInterrupt:
        logger.info("Received keyboard interrupt...")
    except Exception as e:
        logger.error(f"Error starting bot: {e}")
    finally:
        logger.info("Bot shutdown complete.")