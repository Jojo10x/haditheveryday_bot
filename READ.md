# 📿 Hadith Bot

A simple Telegram bot that delivers authentic Islamic hadiths with daily reminders.

## Features

- 📖 Get random hadiths from 6 authentic collections
- ⏰ Schedule daily hadith reminders at your preferred time
- 🔤 Arabic text with English translations

## Setup

1. Clone the repo and install dependencies:
```bash
pip install -r requirements.txt
```

2. Create a `.env` file with your credentials:
```env
DATABASE_URL=your_postgresql_url
TELEGRAM_BOT_TOKEN=your_bot_token
HADITH_API_KEY=your_hadith_api_key
```

3. Run the bot:
```bash
python bot.py
```

## Usage

Start the bot on Telegram with `/start` and use:
- `/hadith` - Get a random hadith
- `/daily` - Set up daily reminders

## Deployment

Deploy to Render as a Background Worker. The `render.yaml` file is already configured.

---
