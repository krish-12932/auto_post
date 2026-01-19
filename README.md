# Telegram Auto-Poster Bot

A Telegram bot that can **Post Now** or **Schedule** messages to a configured channel.

## Features
- **Interactive Menu**: When you send a post, choose "Post Now" or "Schedule".
- **Scheduling**: Schedule posts for later (e.g., `10m`, `1h`, `300s`).
- **Content Preservation**: Keeps information like captions and formatting intact.
- **Security**: Only the owner can operate the bot.

## Setup Guide

### 1. Configuration
Ensure your `.env` file is set up:
```env
BOT_TOKEN=your_token
CHANNEL_ID=@yourchannel  (or -100xxxx for private)
OWNER_ID=123456789
```

### 2. Running Locally
1. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
2. Run the bot:
   ```bash
   python bot.py
   ```

## How to Use
1. **Send any message** (text, photo, video) to the bot in private chat.
2. The bot will reply with buttons:
   - **🚀 Post Now**: Instantly forwards to the channel.
   - **📅 Schedule**: Asks you for a delay.
   - **❌ Cancel**: Discards the post.
3. If you choose **Schedule**:
   - Reply with the time, e.g., `5m` (5 minutes), `1h` (1 hour).
   - The bot will confirm and post it automatically after the time passes.

## Deployment Notes
- **Render**: Use "Background Worker" service type so the bot doesn't sleep and miss scheduled jobs.
- **Railway**: Works out of the box.
