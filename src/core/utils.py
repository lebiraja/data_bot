# utils.py

import logging
import os
import subprocess
import time
from pathlib import Path

# Set up logging
# Configure logging
log_file_path = Path(__file__).parent.parent.parent / "logs" / "data_bot.log"
log_file_path.parent.mkdir(exist_ok=True)  # Ensure logs directory exists

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[logging.FileHandler(str(log_file_path)), logging.StreamHandler()],
)
logger = logging.getLogger("data_bot")

# Set log level based on environment variable if present
log_level = os.getenv("LOG_LEVEL", "INFO").upper()
if log_level in ("DEBUG", "INFO", "WARNING", "ERROR", "CRITICAL"):
    logger.setLevel(getattr(logging, log_level))
    logger.info(f"Log level set to {log_level}")


def cleanup_old_files(directory, days_to_keep):
    """
    Remove files older than the specified number of days

    Args:
        directory: Directory to clean up
        days_to_keep: Number of days to keep files
    """
    if not os.path.exists(directory):
        logger.warning(f"Directory {directory} does not exist, skipping cleanup")
        return

    logger.info(f"Cleaning up files in {directory} older than {days_to_keep} days")

    current_time = time.time()
    cutoff_time = current_time - (days_to_keep * 24 * 60 * 60)

    deleted_count = 0
    error_count = 0

    for filename in os.listdir(directory):
        file_path = os.path.join(directory, filename)

        # Skip directories
        if os.path.isdir(file_path):
            continue

        try:
            file_mod_time = os.path.getmtime(file_path)
            if file_mod_time < cutoff_time:
                os.remove(file_path)
                deleted_count += 1
                logger.debug(f"Deleted old file: {file_path}")
        except Exception as e:
            logger.error(f"Error while deleting {file_path}: {str(e)}")
            error_count += 1

    logger.info(
        f"Cleanup complete: {deleted_count} files deleted, {error_count} errors"
    )
    return deleted_count


def safe_delete_file(file_path):
    """
    Safely delete a file if it exists

    Args:
        file_path: Path to the file to delete

    Returns:
        Boolean indicating whether deletion was successful
    """
    if not file_path or not os.path.exists(file_path):
        return False

    try:
        os.remove(file_path)
        logger.debug(f"Successfully deleted file: {file_path}")
        return True
    except Exception as e:
        logger.error(f"Failed to delete file {file_path}: {str(e)}")
        return False


def validate_environment():
    """
    Validate that all necessary environment variables are set and dependencies are available

    Returns:
        Boolean indicating whether validation passed
    """
    missing_vars = []
    warnings = []

    # Check for required environment variables
    if not os.getenv("TELEGRAM_BOT_TOKEN"):
        missing_vars.append("TELEGRAM_BOT_TOKEN")

    # Check for Ollama installation
    try:
        result = subprocess.run(
            ["ollama", "list"], capture_output=True, text=True, timeout=5
        )
        if result.returncode != 0:
            warnings.append("Ollama is installed but may not be running properly")
    except (subprocess.SubprocessError, FileNotFoundError):
        warnings.append("Ollama does not appear to be installed or is not in PATH")

    # Check for required directories
    for directory in ["uploads", "outputs"]:
        if not os.path.exists(directory):
            try:
                os.makedirs(directory)
                logger.info(f"Created missing directory: {directory}")
            except Exception as e:
                warnings.append(f"Could not create directory {directory}: {str(e)}")

    # Log results
    if missing_vars:
        logger.error(
            f"Missing required environment variables: {', '.join(missing_vars)}"
        )

    if warnings:
        for warning in warnings:
            logger.warning(warning)

    return len(missing_vars) == 0


def create_dotenv_file(bot_token=None):
    """
    Create a .env file with the provided bot token

    Args:
        bot_token: Telegram bot token to save
    """
    env_path = ".env"

    # Check if .env already exists
    if os.path.exists(env_path):
        with open(env_path, "r") as f:
            content = f.read()

        # Check if token is already in the file
        if bot_token and "TELEGRAM_BOT_TOKEN" not in content:
            with open(env_path, "a") as f:
                f.write(f"\nTELEGRAM_BOT_TOKEN='{bot_token}'\n")
            logger.info("Added bot token to existing .env file")
    else:
        # Create new .env file
        with open(env_path, "w") as f:
            f.write("# Data Bot Environment Variables\n\n")
            if bot_token:
                f.write(f"TELEGRAM_BOT_TOKEN='{bot_token}'\n")
            else:
                f.write("# Add your Telegram bot token here\n")
                f.write("# TELEGRAM_BOT_TOKEN='your_token_here'\n")
        logger.info("Created new .env file")

