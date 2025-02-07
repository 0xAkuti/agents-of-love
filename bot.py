import logging
import logging.handlers
import os
from date_manager import DateManager
from typing import Dict

import dotenv
import discord
from discord.ext import commands

dotenv.load_dotenv(override=True)

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

intents = discord.Intents.default()
intents.message_content = True
intents.reactions = True
client = discord.Client(intents=intents)

# Store date managers for each user
date_managers: Dict[int, DateManager] = {}

def get_date_manager(user_id: int) -> DateManager:
    if user_id not in date_managers:
        date_managers[user_id] = DateManager()
    return date_managers[user_id]

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
        date_manager = get_date_manager(message.author.id)
        
        # Get response from date manager
        response = await date_manager.get_manager_response(f'{message.author.display_name}: {message.content}')
        
        # Send response back to Discord
        await message.reply(response)

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

client.run(os.getenv("DISCORD_API_TOKEN"), log_handler=None)