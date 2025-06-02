# bot.py
import telebot
import os
import subprocess
import time
import datetime
import traceback
from dotenv import load_dotenv
import signal
import sys
from data_cleaner import clean_and_summarize
from utils import cleanup_old_files, logger

# Load environment variables from .env file
load_dotenv()

# Get API token from environment variable
API_TOKEN = os.getenv('TELEGRAM_BOT_TOKEN')
if not API_TOKEN:
    raise ValueError("TELEGRAM_BOT_TOKEN environment variable not set. Please create a .env file with your token.")
bot = telebot.TeleBot(API_TOKEN)

# Configuration
DOWNLOAD_DIR = 'uploads'
OUTPUT_DIR = 'outputs'
MAX_FILE_SIZE_MB = 10  # Maximum file size in MB
ALLOWED_EXTENSIONS = ['.csv']
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
        result = subprocess.run(['ollama', 'list'], 
                               capture_output=True, 
                               text=True, 
                               timeout=5)
        return True
    except (subprocess.SubprocessError, FileNotFoundError):
        return False

@bot.message_handler(commands=['start'])
def send_welcome(message):
    if check_ollama():
        bot.reply_to(message, "Hi! Send me a CSV file and I'll clean it for you using AI.")
    else:
        bot.reply_to(message, "⚠️ Warning: Ollama is not running or not installed. Some features may not work.")

@bot.message_handler(content_types=['document'])
def handle_document(message):
    original_file_path = None
    try:
        # Check if file is a CSV
        file_name = message.document.file_name
        file_extension = os.path.splitext(file_name)[1].lower()
        
        if file_extension not in ALLOWED_EXTENSIONS:
            bot.reply_to(message, f"❌ Only CSV files are supported. Please upload a file with one of these extensions: {', '.join(ALLOWED_EXTENSIONS)}")
            return
            
        # Check file size
        file_size_mb = message.document.file_size / (1024 * 1024)  # Convert to MB
        if file_size_mb > MAX_FILE_SIZE_MB:
            bot.reply_to(message, f"❌ File is too large ({file_size_mb:.1f} MB). Maximum allowed size is {MAX_FILE_SIZE_MB} MB.")
            return
            
        # Get file info and download
        file_info = bot.get_file(message.document.file_id)
        downloaded_file = bot.download_file(file_info.file_path)
        
        # Add timestamp to filename to prevent collisions
        timestamp = int(time.time())
        safe_filename = f"{timestamp}_{file_name}"
        file_path = os.path.join(DOWNLOAD_DIR, safe_filename)
        original_file_path = file_path
        
        with open(file_path, 'wb') as new_file:
            new_file.write(downloaded_file)
        
        bot.reply_to(message, "Processing your file... please wait ⏳")
        
        cleaned_path, summary = clean_and_summarize(file_path, OUTPUT_DIR)

        # Processing complete - notify user

        # Send cleaned file
        with open(cleaned_path, 'rb') as result:
            bot.send_document(message.chat.id, result, caption="✅ Here's your cleaned file")

        # Send summary in chunks
        MAX_MESSAGE_LENGTH = 4000
        summary_message = f"✅ Summary of cleaning:\n{summary}"

        for i in range(0, len(summary_message), MAX_MESSAGE_LENGTH):
            bot.send_message(message.chat.id, summary_message[i:i + MAX_MESSAGE_LENGTH])
            
        # Clean up the original file after successful processing
        if original_file_path and os.path.exists(original_file_path):
            try:
                os.remove(original_file_path)
                logger.info(f"Cleaned up temporary file after successful processing: {original_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temporary file: {str(cleanup_error)}")

    except Exception as e:
        # Handle specific error types with user-friendly messages
        error_text = None
        if "Ollama Error" in str(e) or "Ollama is not running" in str(e):
            error_text = "AI processing unavailable. The AI service (Ollama) is not responding."
        elif "File not found" in str(e):
            error_text = "The uploaded file could not be processed. Please try again."
        elif "File is too large" in str(e):
            error_text = "The file is too large to process. Please upload a smaller file."
        elif "CSV file is empty" in str(e) or "Empty" in str(e):
            error_text = "The CSV file appears to be empty. Please check your file and try again."
        elif "parse" in str(e).lower() or "encoding" in str(e).lower():
            error_text = "Could not parse the CSV file. Please ensure it's properly formatted."
        elif "missing values" in str(e).lower():
            error_text = "The file contains too many missing values to process effectively."
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
                logger.info(f"Cleaned up temporary file after error: {original_file_path}")
            except Exception as cleanup_error:
                logger.warning(f"Failed to clean up temporary file: {str(cleanup_error)}")

# Handle graceful shutdown
def signal_handler(sig, frame):
    logger.info("Shutdown signal received, closing bot...")
    bot.stop_polling()
    logger.info("Bot stopped polling")
    sys.exit(0)

signal.signal(signal.SIGINT, signal_handler)
signal.signal(signal.SIGTERM, signal_handler)

if __name__ == "__main__":
    logger.info("Starting Telegram Data Bot")
    try:
        # Validate environment
        from utils import validate_environment
        env_valid = validate_environment()
        if not env_valid:
            logger.warning("Environment validation failed - some features may not work")
        
        # Log configurations
        logger.info(f"Using directories: uploads={DOWNLOAD_DIR}, outputs={OUTPUT_DIR}")
        logger.info(f"File retention days: {FILE_RETENTION_DAYS}")
        logger.info(f"Maximum file size: {MAX_FILE_SIZE_MB} MB")
        logger.info(f"Allowed extensions: {', '.join(ALLOWED_EXTENSIONS)}")
        
        # Check Ollama status
        ollama_status = check_ollama()
        logger.info(f"Ollama status: {'Running' if ollama_status else 'Not running'}")
        
        # Start bot with exception handling
        logger.info("Bot is polling for messages...")
        bot.infinity_polling(timeout=10, long_polling_timeout=5, allowed_updates=["message"])
    except Exception as e:
        logger.critical(f"Fatal error in main loop: {str(e)}")
        sys.exit(1)
