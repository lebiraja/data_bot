# Data Bot

**Data Bot** is a Telegram bot designed to help users with two main tasks:
- **Data Cleaning:** Upload CSV files, and the bot will automatically clean, analyze, and return the processed file with an AI-generated summary.
- **AI Chat:** Chat mode leverages a local AI (Ollama) to provide a conversational assistant.

---

## Features

- **Data Cleaning Mode:**
  - Upload CSV files (up to 10 MB).
  - Cleans data: removes duplicates, handles missing values, summarizes the dataset.
  - Provides both a cleaned CSV file and an AI-generated summary of the cleaning steps and data characteristics.
  - Uses AI (Ollama) for advanced cleaning suggestions and explanations.

- **Chat Mode:**
  - Engage in natural language conversations with the AI assistant.
  - Remembers conversation context and history for each user.
  - Simple commands to switch between chat and data cleaning modes.

- **User State and History:**
  - User preferences and chat history are saved in an SQLite database.
  - Users can clear their chat history at any time.

- **Robust Logging and Error Handling:**
  - All actions and errors are logged for troubleshooting.
  - Provides user-friendly error messages and guidance.

## Directory Structure

```
data_bot/
├── bot.py              # Main entry point; Telegram bot logic and message routing
├── chat_handler.py     # AI chat mode logic & user conversation management
├── data_cleaner.py     # Data cleaning and summarization functions
├── db_handler.py       # Handles user data, chat history, and preferences via SQLite
├── ollama_handler.py   # Interfaces with local Ollama AI (API/CLI)
├── utils.py            # Logging, environment checks, file cleanup
├── requirements.txt    # Project dependencies
├── bot_data.db         # SQLite database (created/used at runtime)
├── data_bot.log        # Log file (created at runtime)
├── uploads/            # Folder for uploaded files
├── outputs/            # Folder for processed/cleaned files
├── downloads/          # (Potentially for additional file operations)
├── __pycache__/        # Python bytecode cache
└── README.md           # This documentation file
```

## Key Components and Functionality

### 1. `bot.py`
- Initializes the Telegram bot and handles the primary message loop.
- Loads configuration from environment (.env) and sets up directories.
- Handles commands:
  - `/start`: Welcome message and mode selection (Data Cleaning or Chat).
  - `/chatmode`, `/datamode`: Switch modes.
  - `/clear`: Clear user's chat history.
  - `/help`: Display context-specific instructions.
- Manages file uploads (CSV only):
  - Validates file type and size.
  - Saves uploaded files, triggers cleaning/analysis, and returns results.
  - Handles errors gracefully, cleans up files after processing.
- On shutdown, stops polling and logs shutdown events.

### 2. `chat_handler.py`
- Manages chat mode and context for each user.
- Interfaces with Ollama for generating AI responses.
- Stores and retrieves chat history from the database.
- Provides mode switching and help messages.

### 3. `data_cleaner.py`
- Loads and validates CSV files using pandas.
- Computes dataset statistics (numeric/non-numeric summaries, missing values, duplicates).
- Interacts with Ollama AI to get cleaning suggestions (if available).
- Performs cleaning: removes duplicates, handles missing values (drops/fills), saves cleaned CSV.
- Returns both the cleaned file path and a detailed summary.

### 4. `db_handler.py`
- Manages users and their preferences in SQLite.
- Stores chat history with roles (user/assistant) for context.
- Efficiently retrieves context for chat and manages history length.
- Allows clearing user history and updating preferences.

### 5. `ollama_handler.py`
- Checks if Ollama (local LLM) is running via API or CLI.
- Sends prompts to Ollama and retrieves responses (supports retries and backoff).
- Handles errors and falls back to CLI if the API is unavailable.

### 6. `utils.py`
- Logging setup (file + console, level configurable via env).
- Functions for cleaning up old files/directories.
- Validates environment (required variables, dependencies, directories).
- Utility for creating `.env` files if needed.

### 7. `requirements.txt`
- Lists Python dependencies:
    - Core: `pandas`, `telebot`, `python-dotenv`, `requests`
    - Optional: `numpy`, `matplotlib`, `seaborn`
    - Dev: `pytest`, `flake8`, `black`

---

## Getting Started

### 1. Prerequisites

- Python 3.8+
- [Ollama](https://ollama.com/) (local AI language model runner) installed and running.
- Telegram bot token (get from BotFather).

### 2. Installation

```bash
git clone https://github.com/lebiraja/data_bot.git
cd data_bot
pip install -r requirements.txt
```

### 3. Configuration

- Create a `.env` file or set environment variables:
  ```
  TELEGRAM_BOT_TOKEN=your_telegram_bot_token_here
  ```
- (Optional) Configure logging level by setting `LOG_LEVEL`.

### 4. Running the Bot

```bash
python bot.py
```

The bot will start polling for messages on Telegram. Use `/start` to interact.

---

## Usage

- **Switch Modes:** Use `/chatmode` for AI chat, `/datamode` for data cleaning.
- **Data Cleaning:** Send a CSV file in data cleaning mode. Receive a cleaned CSV and summary.
- **Chat:** Ask questions in chat mode. The bot will use AI to reply with context.
- **Help:** Use `/help` in either mode for detailed instructions.
- **Clear History:** Use `/clear` to reset your chat history.

---

## Advanced

- **Extending Data Cleaning:** Modify `data_cleaner.py` to add new cleaning steps or analysis.
- **Custom Models:** Change the model name in `chat_handler.py` or `ollama_handler.py` for different LLMs.
- **File Retention:** Configure how many days files are kept by editing `FILE_RETENTION_DAYS` in `bot.py`.

---

## Troubleshooting

- **Ollama Not Running:** Some features (AI chat, advanced cleaning) require Ollama. Ensure it is installed and running.
- **Logging:** Check `data_bot.log` for detailed logs and errors.
- **Database:** The bot creates and manages `bot_data.db` automatically.

---

## License

MIT License

---

## Links

- [View Source on GitHub](https://github.com/lebiraja/data_bot)
- [Ollama Documentation](https://ollama.com/)
- [Telegram Bot API](https://core.telegram.org/bots/api)

---

> **Note:** This README was generated from the current codebase. For the latest directory listing, see the [repository files](https://github.com/lebiraja/data_bot/tree/main/).
