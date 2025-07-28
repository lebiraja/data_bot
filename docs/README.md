# Data Bot

A Telegram bot for automated data analysis and AI-powered chat.

## Features

- **Data Cleaning Mode**: Upload CSV files for automated cleaning and analysis
- **Chat Mode**: Have conversations with an AI assistant
- Automatic file cleanup (configurable retention period)
- Support for large CSV files
- Intelligent data analysis and summarization
- SQLite database for storing conversations and user data

## Project Structure

```
data_bot/
├── src/                    # Source code
│   ├── core/              # Core functionality
│   │   ├── bot.py         # Main bot logic
│   │   ├── schemas.py     # Data schemas
│   │   └── utils.py       # Utility functions
│   ├── handlers/          # Various handlers
│   │   ├── chat_handler.py
│   │   ├── db_handler.py
│   │   └── ollama_handler.py
│   └── processors/        # Data processing modules
│       ├── data_cleaner.py
│       └── enhanced_data_processor.py
├── data/                  # Data files
│   ├── downloads/         # Downloaded files
│   ├── uploads/          # User uploads
│   ├── datasets/         # Processed datasets
│   └── outputs/          # Generated outputs
├── logs/                  # Log files
├── db/                    # Database files
├── config/                # Configuration files
│   └── .env              # Environment variables
├── docs/                  # Documentation
│   └── README.md         # This file
├── main.py               # Entry point
├── requirements.txt      # Python dependencies
└── .gitignore           # Git ignore file
```

## Prerequisites

- Python 3.8+
- Telegram Bot Token (from @BotFather)
- Ollama (optional, for enhanced AI features)

## Installation

1. Clone this repository
2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```
3. Create a `.env` file in the `config` directory with your Telegram bot token:
   ```
   TELEGRAM_BOT_TOKEN=your_bot_token_here
   ```
4. (Optional) Install and start Ollama for AI features

## Usage

1. Start the bot:
   ```bash
   python main.py
   ```
2. In Telegram, start a conversation with your bot
3. Use `/start` to see available options
4. Switch between modes using `/chatmode` or `/datamode`

## Commands

- `/start` - Show welcome message and mode selection
- `/chatmode` - Switch to chat mode
- `/datamode` - Switch to data cleaning mode
- `/clear` - Clear chat history (in chat mode)
- `/help` - Show help for current mode

## Configuration

You can customize the following in `src/core/bot.py`:
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
- User data is stored securely in SQLite database

## Troubleshooting

If you encounter issues:
1. Make sure Ollama is running (if using AI features)
2. Check the logs in `logs/data_bot.log`
3. Verify your Telegram bot token is correct
4. Ensure all dependencies are installed
5. Check that you have write permissions for data directories
