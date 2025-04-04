# 📚 Discord Channel Archiver 

A high-performance Discord bot for archiving channel messages with real-time progress tracking and optimized data export capabilities.

## ✨ Features

- 🚀 High-performance message collection
- 📊 Real-time progress tracking
- 💾 JSON file export with timestamps
- 👤 User-specific message filtering
- 📥 Customizable message limits
- ⚡ Batch processing support
- 🔒 Admin-only commands
- 📁 Automatic saves to Downloads folder

## 🛠️ Setup

1. **Clone the repository**
```bash
git clone https://github.com/S-P-H-E/DiscordChannelArchiver.git
cd DiscordChannelArchiver
```

2. **Install dependencies**
```bash
pip install discord.py aiofiles
```

3. **Configure your Discord Token**
Replace the `DISCORD_TOKEN` in `main.py`:
```python
DISCORD_TOKEN = "your-token-here"
```

## 🎮 Commands

### `!save_messages [channel_id] [limit]`
Save all messages from a specific channel
- `channel_id`: The ID of the channel to archive
- `limit`: (Optional) Maximum number of messages to save

### `!save_recent [channel_id] [message_count]`
Save the most recent messages from a channel
- `channel_id`: The ID of the channel to archive
- `message_count`: Number of recent messages to save (default: 1000)

### `!save_user_messages [channel_id] [user_id] [limit]`
Save messages from a specific user in a channel
- `channel_id`: The ID of the channel to analyze
- `user_id`: The ID of the user to focus on
- `limit`: (Optional) Maximum number of messages to scan

### `!help_save`
Display help information about all available commands

## ⚙️ Configuration Options

You can modify these constants in `main.py`:

```python
BATCH_SIZE = 5000  # Adjust batch processing size
PROGRESS_UPDATE_INTERVAL = 3  # Seconds between progress updates
```

## 📄 Output Format

Messages are saved in JSON format with the following structure:
```json
{
  "content": "Message content",
  "author": "Username#0000",
  "author_id": 123456789,
  "timestamp": "2024-04-04T10:00:00.000Z",
  "attachments": ["url1", "url2"],
  "jump_url": "https://discord.com/channels/..."
}
```

## 🔐 Security

- Commands require administrator permissions
- Token should be kept private
- Outputs are saved locally to Downloads folder

## 🚀 Performance

The bot includes several optimizations:
- Asynchronous file operations
- Batch processing
- Rate-limited progress updates
- Memory-efficient message collection

## 📝 License

This project is open source and available under the MIT License.

## 🤝 Contributing

Contributions, issues, and feature requests are welcome! Feel free to check the issues page.

## 💡 Tips

- For large channels, consider using limits to avoid memory issues
- Use `save_recent` for quick exports of active discussions
- Monitor the progress updates for large exports
- Keep your Discord token secure and never share it