# Shree Krishna Slack Bot

A minimalist Slack bot that shares wisdom from the Bhagavad Gita.

---

## Getting Started

Clone the repository and set up your environment:

```bash
git clone https://github.com/mrdeephang/Slack-Bot.git
cd Slack-Bot
```

Create and activate a virtual environment:

```bash
# Linux/macOS
python3 -m venv venv
source venv/bin/activate

# Windows (Command Prompt)
python -m venv venv
venv\Scripts\activate

# Windows (PowerShell)
python -m venv venv
venv\Scripts\Activate.ps1
```

Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Configuration

Create a `.env` file in the root directory with your Slack credentials:

```env
SLACK_BOT_TOKEN=your_bot_token
CHANNEL_ID=your_channel_id
```

## Running the Bot

Start the bot with:

```bash
python3 slack_bot.py
```

## Commands

The bot responds to the following:

**@Shree Krishna quote** — Receive a random quote from the Bhagavad Gita

The bot also shares daily wisdom automatically in your configured channels.

## Project Structure

```
├── slack_bot.py           # Core bot implementation
├── gita_quotes.py         # Quote retrieval logic
├── gita_quotes_data.py    # Quote collection
├── requirements.txt       # Python dependencies
└── .env                   # Environment variables (not tracked)
```

## Deployment

Currently deployed on Render.

## Roadmap

Integration with external APIs is planned to expand the quote database and provide unlimited wisdom from the Gita.

---

**Copyright © 2026 Deephang Thegim. All rights reserved.**
