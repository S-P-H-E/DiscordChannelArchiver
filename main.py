import discord
import asyncio
import os
import json
import aiofiles
import time
from discord.ext import commands
from datetime import datetime
from pathlib import Path
import concurrent.futures
from typing import List, Dict, Any, Optional, Union

# Configure your Discord Token
DISCORD_TOKEN = "YOUR_TOKEN_HERE"  # Replace with your Discord bot token

# Configure Discord bot
intents = discord.Intents.default()
intents.message_content = True
bot = commands.Bot(command_prefix='!', intents=intents)

# Batch size for processing messages
BATCH_SIZE = 5000
# Progress update interval (in seconds)
PROGRESS_UPDATE_INTERVAL = 3


# Get the downloads folder path based on the operating system
def get_downloads_folder():
    home = Path.home()
    if os.name == 'nt':  # Windows
        return home / 'Downloads'
    elif os.name == 'posix':  # macOS/Linux
        return home / 'Downloads'
    else:
        # Fallback to current directory if OS not detected
        return Path.cwd()


class AsyncJsonWriter:
    """A class for asynchronously writing JSON data to a file"""

    def __init__(self, file_path: Union[str, Path]):
        self.file_path = Path(file_path)
        self.first_batch = True
        self.any_data_written = False

    async def __aenter__(self):
        self.file = await aiofiles.open(self.file_path, 'w', encoding='utf-8')
        await self.file.write('[')
        return self

    async def __aexit__(self, exc_type, exc_val, exc_tb):
        await self.file.write(']')
        await self.file.flush()
        await self.file.close()

    async def write_batch(self, batch: List[Dict[str, Any]]):
        """Write a batch of message data to the file"""
        if not batch:
            return

        # Convert batch to JSON string
        json_string = json.dumps(batch, ensure_ascii=False)

        # For batches after the first one, add a comma separator
        if not self.first_batch and self.any_data_written:
            await self.file.write(',')

        # Remove the outer brackets from the JSON array
        content_to_write = json_string[1:-1]

        # If this is the first batch with data, don't add a comma
        if self.first_batch:
            self.first_batch = False

        if content_to_write:  # Only write if there's actual content
            await self.file.write(content_to_write)
            self.any_data_written = True
            await self.file.flush()  # Ensure data is written to disk


class ProgressReporter:
    """Helper class to manage progress reporting with rate limiting"""

    def __init__(self, ctx, initial_message: str):
        self.ctx = ctx
        self.message = None
        self.last_update_time = 0
        self.initial_message = initial_message

    async def initialize(self):
        """Send the initial progress message"""
        self.message = await self.ctx.send(self.initial_message)
        self.last_update_time = time.time()
        return self.message

    async def update(self, content: str, force: bool = False):
        """Update the progress message, respecting the rate limit"""
        current_time = time.time()

        # Only update if forced or if enough time has passed since the last update
        if force or (current_time - self.last_update_time) >= PROGRESS_UPDATE_INTERVAL:
            await self.message.edit(content=content)
            self.last_update_time = current_time
            return True
        return False


@bot.event
async def on_ready():
    print(f'Bot is ready! Logged in as {bot.user}')


@bot.command()
@commands.has_permissions(administrator=True)
async def save_messages(ctx, channel_id: int, limit: int = None):
    """
    Save messages from a channel to a JSON file in the Downloads folder.

    :param ctx: Command context
    :param channel_id: The ID of the channel to save messages from
    :param limit: Optional limit on number of messages to save (None = all messages)
    """
    try:
        start_time = time.time()

        # Get the channel
        channel = bot.get_channel(channel_id)
        if not channel:
            await ctx.send(f"❌ Channel with ID {channel_id} not found.")
            return

        # Initialize progress reporter
        progress = ProgressReporter(ctx, f"🔍 Starting to collect messages from #{channel.name}...")
        await progress.initialize()

        # Prepare output file path
        downloads_folder = get_downloads_folder()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"discord_messages_{channel.name}_{timestamp}.json"
        filepath = downloads_folder / filename

        # Create all_messages list to store message data
        all_messages = []
        total_collected = 0

        # Collect messages first for simplicity
        await progress.update(f"📥 Collecting messages from #{channel.name}...")

        async for message in channel.history(limit=limit, oldest_first=True):
            # Add message to all_messages - optimized format
            all_messages.append({
                "content": message.content,
                "author": str(message.author),
                "author_id": message.author.id,
                "timestamp": message.created_at.isoformat(),
                "attachments": [a.url for a in message.attachments],
                "jump_url": message.jump_url
            })

            total_collected += 1

            # Update progress periodically
            await progress.update(
                f"📥 Collecting messages from #{channel.name}: {total_collected} messages so far..."
            )

        # If no messages were found
        if not all_messages:
            await ctx.send("❌ No messages found in the channel.")
            return

        # Write messages to file
        await progress.update(
            f"💾 Writing {total_collected} messages to file...",
            force=True
        )

        try:
            # Simple synchronous write - more reliable for smaller datasets
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(all_messages, f, ensure_ascii=False, indent=2)

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            # Send completion message
            await progress.update(
                f"✅ Successfully exported {total_collected} messages from #{channel.name} to:\n"
                f"`{filepath}`\n"
                f"Time taken: {elapsed_time:.2f} seconds ({total_collected / elapsed_time:.2f} messages/sec)",
                force=True
            )
        except Exception as file_error:
            await ctx.send(f"❌ Error saving file: {str(file_error)}")

    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()


@bot.command()
@commands.has_permissions(administrator=True)
async def save_recent(ctx, channel_id: int, message_count: int = 1000):
    """
    Save the most recent messages from a channel.

    :param ctx: Command context
    :param channel_id: The ID of the channel to save messages from
    :param message_count: Number of recent messages to save (default: 1000)
    """
    await save_messages(ctx, channel_id, message_count)


@bot.command()
@commands.has_permissions(administrator=True)
async def save_user_messages(ctx, channel_id: int, user_id: int, limit: int = None):
    """
    Save messages from a specific user in a channel.

    :param ctx: Command context
    :param channel_id: The ID of the channel to analyze
    :param user_id: The ID of the user to focus on
    :param limit: Optional message limit (None = all messages)
    """
    try:
        start_time = time.time()

        # Get the channel
        channel = bot.get_channel(channel_id)
        if not channel:
            await ctx.send(f"❌ Channel with ID {channel_id} not found.")
            return

        # Initialize progress reporter
        progress = ProgressReporter(
            ctx, f"🔍 Starting to collect messages from user ID {user_id} in #{channel.name}..."
        )
        await progress.initialize()

        # Prepare output file path
        downloads_folder = get_downloads_folder()
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filename = f"discord_user_{user_id}_messages_{timestamp}.json"
        filepath = downloads_folder / filename

        # Collect messages
        user_messages = []
        total_scanned = 0
        user_collected = 0

        # Process messages
        async for message in channel.history(limit=limit):
            total_scanned += 1

            # Check if message is from target user
            if message.author.id == user_id:
                # Convert message to dictionary
                user_messages.append({
                    "content": message.content,
                    "author": str(message.author),
                    "author_id": message.author.id,
                    "timestamp": message.created_at.isoformat(),
                    "attachments": [a.url for a in message.attachments],
                    "jump_url": message.jump_url
                })

                user_collected += 1

            # Update progress periodically
            await progress.update(
                f"📥 Scanned {total_scanned} messages, found {user_collected} from user ID {user_id} in #{channel.name}..."
            )

        # If no messages were found
        if not user_messages:
            await progress.update(
                f"❌ No messages found for user ID {user_id} in #{channel.name} after scanning {total_scanned} messages.",
                force=True
            )
            return

        # Write messages to file
        await progress.update(
            f"💾 Writing {user_collected} messages to file...",
            force=True
        )

        try:
            # Simple synchronous write
            with open(filepath, 'w', encoding='utf-8') as f:
                json.dump(user_messages, f, ensure_ascii=False, indent=2)

            # Calculate elapsed time
            elapsed_time = time.time() - start_time

            # Send completion message
            await progress.update(
                f"✅ Successfully exported {user_collected} messages from user ID {user_id} in #{channel.name} to:\n"
                f"`{filepath}`\n"
                f"Time taken: {elapsed_time:.2f} seconds ({total_scanned / elapsed_time:.2f} messages scanned/sec)",
                force=True
            )
        except Exception as file_error:
            await ctx.send(f"❌ Error saving file: {str(file_error)}")

    except Exception as e:
        await ctx.send(f"❌ An error occurred: {str(e)}")
        import traceback
        traceback.print_exc()


@bot.command()
@commands.has_permissions(administrator=True)
async def help_save(ctx):
    """Shows help for the message saving commands"""
    embed = discord.Embed(
        title="Message Saving Commands",
        description="High-performance commands for saving Discord messages to JSON files",
        color=discord.Color.green()
    )

    embed.add_field(
        name="!save_messages [channel_id] [limit]",
        value="Save messages from a channel (limit is optional)",
        inline=False
    )

    embed.add_field(
        name="!save_recent [channel_id] [message_count]",
        value="Save the most recent messages from a channel (default: 1000)",
        inline=False
    )

    embed.add_field(
        name="!save_user_messages [channel_id] [user_id] [limit]",
        value="Save messages from a specific user in a channel",
        inline=False
    )

    embed.add_field(
        name="Performance Features",
        value="• Optimized for speed and reliability\n• Progress tracking\n• Performance metrics",
        inline=False
    )

    embed.add_field(
        name="Note",
        value="All files are saved to your Downloads folder as simplified JSON (AI-friendly)",
        inline=False
    )

    await ctx.send(embed=embed)


# Run the bot
if __name__ == "__main__":
    bot.run(DISCORD_TOKEN)