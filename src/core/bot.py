# bot.py
import os
import signal
import subprocess
import sys
import time
import traceback
from pathlib import Path

import telebot
from dotenv import load_dotenv
from telebot import types

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.processors.data_cleaner import clean_and_summarize
from src.handlers.chat_handler import chat_handler
from src.core.utils import cleanup_old_files, logger

# Load environment variables from .env file
config_path = Path(__file__).parent.parent.parent / 'config' / '.env'
load_dotenv(config_path)

# Get API token from environment variable
API_TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

bot = telebot.TeleBot(API_TOKEN)

# Configuration
base_dir = Path(__file__).parent.parent.parent
DOWNLOAD_DIR = str(base_dir / "data" / "uploads")
OUTPUT_DIR = str(base_dir / "data" / "outputs")
MAX_FILE_SIZE_MB = 10  # Maximum file size in MB
ALLOWED_EXTENSIONS = [".csv"]
FILE_RETENTION_DAYS = 7  # Number of days to keep files before cleanup

# Create necessary directories
os.makedirs(DOWNLOAD_DIR, exist_ok=True)
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Clean up old files on startup
cleanup_old_files(DOWNLOAD_DIR, FILE_RETENTION_DAYS)
cleanup_old_files(OUTPUT_DIR, FILE_RETENTION_DAYS)


# Check if Ollama is installed and running
def check_ollama():
    try:
        subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=5, check=True
        )
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False


@bot.message_handler(commands=["start"])
def send_welcome(message):
    # Create inline keyboard with two options
    markup = types.InlineKeyboardMarkup(row_width=2)
    data_cleaning_btn = types.InlineKeyboardButton(
        "📊 Data Cleaning", callback_data="mode_data"
    )
    chat_btn = types.InlineKeyboardButton("🤖 Chat Mode", callback_data="mode_chat")
    markup.add(data_cleaning_btn, chat_btn)

    # Check if Ollama is running
    ollama_status = (
        "✅ Ollama is running"
        if check_ollama()
        else "⚠️ Ollama is not running (limited functionality)"
    )

    welcome_text = (
        "👋 Welcome to Data Bot!\n\n"
        "Please select a mode:\n\n"
        "📊 *Data Cleaning* - Send CSV files for automated cleaning and analysis, /datamode. \n"
        "🤖 *Chat Mode* - Have a conversation with the AI assistant, /chatmode.\n\n"
        f"Status: {ollama_status}"
    )

    bot.send_message(
        message.chat.id, welcome_text, parse_mode="Markdown", reply_markup=markup
    )


@bot.callback_query_handler(func=lambda call: call.data.startswith("mode_"))
def handle_mode_selection(call):
    """Handle mode selection from inline keyboard"""
    try:
        user_id = call.from_user.id

        if call.data == "mode_data":
            # Switch to data cleaning mode
            response = chat_handler.switch_to_data_mode(user_id)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=response,
                parse_mode="Markdown",
            )
        elif call.data == "mode_chat":
            # Switch to chat mode
            response = chat_handler.switch_to_chat_mode(user_id)
            bot.edit_message_text(
                chat_id=call.message.chat.id,
                message_id=call.message.message_id,
                text=response,
                parse_mode="Markdown",
            )
    except Exception as e:
        logger.error(f"Error handling mode selection: {str(e)}")
        bot.answer_callback_query(call.id, "⚠️ An error occurred. Please try again.")


@bot.message_handler(commands=["chatmode"])
def switch_to_chat_mode(message):
    """Switch to chat mode"""
    user_id = message.from_user.id
    response = chat_handler.switch_to_chat_mode(user_id)
    bot.reply_to(message, response, parse_mode="Markdown")


@bot.message_handler(commands=["datamode"])
def switch_to_data_mode(message):
    """Switch to data cleaning mode"""
    user_id = message.from_user.id
    response = chat_handler.switch_to_data_mode(user_id)
    bot.reply_to(message, response, parse_mode="Markdown")


@bot.message_handler(commands=["clear"])
def clear_chat_history(message):
    """Clear user's chat history"""
    user_id = message.from_user.id
    response = chat_handler.clear_history(user_id)
    bot.reply_to(message, response)


@bot.message_handler(commands=["help"])
def send_help(message):
    """Send help message based on current mode"""
    user_id = message.from_user.id

    if chat_handler.is_chat_mode(user_id):
        # Send chat mode help
        help_text = chat_handler.get_help_message()
        bot.reply_to(message, help_text, parse_mode="Markdown")
    else:
        # Send data cleaning mode help
        help_text = (
            "📊 *Data Cleaning Mode Help*\n\n"
            "Send me a CSV file and I'll clean it for you using AI.\n\n"
            "Supported formats: CSV\n"
            "Maximum file size: 10 MB\n\n"
            "Commands:\n"
            "/chatmode - Switch to chat mode\n"
            "/datamode - Switch to data cleaning mode\n"
            "/help - Show this help message"
        )
        bot.reply_to(message, help_text, parse_mode="Markdown")


def send_long_message(chat_id: int, text: str, parse_mode: str = None):
    """
    Split and send long messages that exceed Telegram's limit
    """
    max_message_length = 4000  # Telegram's limit is 4096, using 4000 to be safe

    # Split message into chunks
    chunks = [
        text[i: i + max_message_length]
        for i in range(0, len(text), max_message_length)
    ]

    for chunk in chunks:
        try:
            bot.send_message(chat_id, chunk, parse_mode=parse_mode)
        except Exception as e:
            logger.error(f"Error sending message chunk: {str(e)}")
            # Try sending without parse mode if it fails
            try:
                bot.send_message(chat_id, chunk)
            except Exception as e2:
                logger.error(
                    f"Error sending message chunk without parse mode: {str(e2)}"
                )
                raise


@bot.message_handler(content_types=["document"])
def handle_document(message):
    # Check if user is in chat mode
    user_id = message.from_user.id
    if chat_handler.is_chat_mode(user_id):
        bot.reply_to(
            message,
            "⚠️ You're currently in Chat Mode which doesn't support file processing.\n"
            "Use /datamode command to switch to Data Cleaning Mode first.",
        )
        return

    original_file_path = None
    try:
        # Check if file is a CSV
        file_name = message.document.file_name
        file_extension = os.path.splitext(file_name)[1].lower()

        if file_extension not in ALLOWED_EXTENSIONS:
            bot.reply_to(
                message,
                f"""❌ Only CSV files are supported. \n"
                "                Please upload a file with one of these extensions: \n"
                "                {', '.join(ALLOWED_EXTENSIONS)}""",
            )
            return

        # Check file size
        file_size_mb = message.document.file_size / (1024 * 1024)  # Convert to MB
        if file_size_mb > MAX_FILE_SIZE_MB:
            bot.reply_to(
                message,
                f"""❌ File is too large ({file_size_mb:.1f} MB). \n"
                "                Maximum allowed size is {MAX_FILE_SIZE_MB} MB.""",
            )
            return

        # Get file info and download
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)

        # Add timestamp to filename to prevent collisions
        timestamp = int(time.time())
        safe_filename = f"{timestamp}_{file_name}"
        file_path = os.path.join(DOWNLOAD_DIR, safe_filename)
        original_file_path = file_path

        with open(file_path, "wb") as new_file:
            new_file.write(downloaded_file)

        bot.reply_to(message, "Processing your file... please wait ⏳")

        cleaned_path, summary = clean_and_summarize(file_path, OUTPUT_DIR)

        # Processing complete - notify user

        # Send cleaned file
        with open(cleaned_path, "rb") as result:
            bot.send_document(
                message.chat.id, result, caption="✅ Here's your cleaned file"
            )

        # Send summary using the new function
        summary_message = f"✅ Summary of cleaning:\n{summary}"
        send_long_message(message.chat.id, summary_message)

        # Clean up the original file after successful processing
        if original_file_path and os.path.exists(original_file_path):
            try:
                os.remove(original_file_path)
                logger.info(
                    "Cleaned up temporary file after successful processing: "
                    f"{original_file_path}"
                )
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to clean up temporary file: {str(cleanup_error)}"
                )

    except Exception as e:
        # Handle specific error types with user-friendly messages
        error_text = None
        if "Ollama Error" in str(e) or "Ollama is not running" in str(e):
            error_text = (
                "AI processing unavailable. The AI service (Ollama) is not responding."
            )
        elif "File not found" in str(e):
            error_text = "The uploaded file could not be processed. Please try again."
        elif "File is too large" in str(e):
            error_text = (
                "The file is too large to process. Please upload a smaller file."
            )
        elif "CSV file is empty" in str(e) or "Empty" in str(e):
            error_text = (
                "The CSV file appears to be empty. Please check your file and try again."
            )
        elif "parse" in str(e).lower() or "encoding" in str(e).lower():
            error_text = (
                "Could not parse the CSV file. Please ensure it's properly formatted."
            )
        elif "missing values" in str(e).lower():
            error_text = (
                "The file contains too many missing values to process effectively."
            )
        else:
            # Generic error message
            error_text = "An error occurred while processing your file."

        # Send user-friendly error message
        bot.send_message(message.chat.id, f"❌ Error: {error_text}")

        # Log the detailed error for debugging
        logger.error(f"Error processing document: {str(e)}")
        logger.error(traceback.format_exc())

        # Clean up the original file if it exists
        if original_file_path and os.path.exists(original_file_path):
            try:
                os.remove(original_file_path)
                logger.info(
                    f"Cleaned up temporary file after error: {original_file_path}"
                )
            except Exception as cleanup_error:
                logger.warning(
                    f"Failed to clean up temporary file: {str(cleanup_error)}"
                )


@bot.message_handler(func=lambda message: True)
def handle_all_messages(message):
    """
    Handle all text messages. This will process chat messages when in chat mode
    or give instructions when in data mode.
    """
    user_id = message.from_user.id

    # Check user's mode
    if chat_handler.is_chat_mode(user_id):
        # User is in chat mode, process the message
        try:
            # Show typing status
            bot.send_chat_action(message.chat.id, "typing")

            # Process message and get response
            response = chat_handler.process_message(user_id, message.text)

            # Send response using the new function
            send_long_message(message.chat.id, response)
        except Exception as e:
            logger.error(f"Error in chat processing: {str(e)}")
            logger.error(traceback.format_exc())
            bot.reply_to(
                message,
                """⚠️ I encountered an error while processing your message. \n"
                "                Please try again later.""",
            )
    else:
        # User is in data mode, give instructions
        bot.reply_to(
            message,
            """📊 You're in Data Cleaning Mode. \n"
            "            Please upload a CSV file for processing.\n\n"
            "            To chat with me instead, use /chatmode command to switch to Chat Mode.""",
        )


# Handle graceful shutdown
def signal_handler(sig, frame):
    logger.info("Shutdown signal received, closing bot...")
    bot.stop_polling()
    logger.info("Bot stopped polling")
    sys.exit(0)


signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

def main():
    """Main function to start the bot"""
    logger.info("Starting Telegram Data Bot")
    try:
        # Validate environment
        from src.core.utils import validate_environment

        env_valid = validate_environment()
        if not env_valid:
            logger.warning(
                "Environment validation failed - some features may not work"
            )

        # Log configurations
        logger.info(f"Using directories: uploads={DOWNLOAD_DIR}, outputs={OUTPUT_DIR}")
        logger.info(f"File retention days: {FILE_RETENTION_DAYS}")
        logger.info(f"Maximum file size: {MAX_FILE_SIZE_MB} MB")
        logger.info(f"Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}")

        # Check Ollama status
        ollama_status = check_ollama()
        logger.info(f"Ollama status: {'Running' if ollama_status else 'Not running'}")

        # Initialize chat handler
        try:
            chat_handler._check_model_availability()
            logger.info("Chat handler initialized successfully")
        except Exception as e:
            logger.warning(f"Chat handler initialization warning: {str(e)}")

        # Start bot with exception handling
        logger.info("Bot is polling for messages...")
        bot.infinity_polling(
            timeout=10, long_polling_timeout=5, allowed_updates=["message"]
        )
    except Exception as e:
        logger.critical(f"Fatal error in main loop: {str(e)}")
        sys.exit(1)


if __name__ == "__main__":
    main()
