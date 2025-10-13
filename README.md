# Shree Krishna Slack Bot

A minimalist Slack bot that shares wisdom from the Bhagavad Gita.

## Setup

1. Clone the repository
2. python/python3 -m venv venv
3. source venv/bin/activate(linux/macos) or windows: venv\Scripts\activate(cmd) or \venv\Scripts\Activate.ps1(PowerShell)
4. Install dependencies: `pip install -r requirements.txt`
5. Create `.env` file with your Slack tokens:

   ```
   SLACK_BOT_TOKEN=your_bot_token
   CHANNEL_ID=your_channel_id

   ```

6. Run: `python/python3 slack_bot.py`

## Usage

- `@Shree Krishna quote` - Get a random Gita quote
- Daily wisdom sharing in configured channels

## Files

- `slack_bot.py` - Main bot logic
- gita_quotes.py - Functions to fetch random or daily Gita quotes
- `gita_quotes_data.py` - Quote database
- `.env` - Configuration (not tracked)

## Deploy

- Deployed on `Render`

## Future Enhancement

- Use APi to fetch Gita quotes for unlimited Gita quotes

## Author

Copyright © 2025 Deephang Thegim. All rights reserved.
