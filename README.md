# Data Bot

A Telegram bot for cleaning and analyzing CSV data files using AI.

## Features

- CSV file processing and cleaning
- AI-powered data analysis using Ollama
- Automated report generation
- User-friendly Telegram interface

## Requirements

- Python 3.8+
- Ollama installed and running locally
- Telegram bot token

## Installation

1. Clone the repository
2. Install dependencies:
   ```
   pip install -r requirements.txt
   ```
3. Create a `.env` file with your Telegram bot token:
   ```
   TELEGRAM_BOT_TOKEN='your_token_here'
   ```
4. Make sure Ollama is installed and running

## Usage

Run the bot:
```
python bot.py
```

Then, open Telegram and send CSV files to your bot.

## Configuration

You can customize the following in `bot.py`:
- `MAX_FILE_SIZE_MB`: Maximum file size in MB (default: 10)
- `FILE_RETENTION_DAYS`: Number of days to keep files (default: 7)
- `ALLOWED_EXTENSIONS`: File types allowed (default: ['.csv'])

## Environment Variables

- `TELEGRAM_BOT_TOKEN`: Your Telegram bot token
- `LOG_LEVEL`: Set the logging level (DEBUG, INFO, WARNING, ERROR, CRITICAL)

## Security

- Bot token is stored in .env file (not committed to git)
- File validation prevents oversized uploads
- Automatic cleanup of old files

## Troubleshooting

If you encounter issues:
1. Make sure Ollama is running
2. Check the logs in data_bot.log
3. Verify your Telegram bot token is correct

