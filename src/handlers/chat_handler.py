# chat_handler.py

import time
import traceback
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.handlers.db_handler import db
from src.handlers.ollama_handler import is_ollama_running, query_ollama
from src.core.utils import logger

# Configuration
CHAT_MODEL = "llama3.2:3b"  # Different model from the data cleaning one
MAX_CONTEXT_LENGTH = 15000  # Maximum context length in characters
DEFAULT_SYSTEM_PROMPT = """You are a helpful assistant that provides clear and concise answers.
Be friendly, informative, and respectful in your responses.
If you're unsure about something, admit it rather than making up information."""


class ChatHandler:
    def __init__(self, model=CHAT_MODEL):
        """
        Initialize the chat handler

        Args:
            model: The Ollama model to use for chat responses
        """
        self.model = model
        self._check_model_availability()

    def _check_model_availability(self):
        """
        Check if the specified chat model is available in Ollama

        Logs a warning if Ollama is not running or the model is not available
        """
        if not is_ollama_running():
            logger.warning(
                "Ollama is not running. Chat functionality may be limited."
            )
            return False

        try:
            # Simple query to check if model works
            test_prompt = (
                "Hello! This is a test message. Please respond with 'OK'."
            )
            query_ollama(test_prompt, self.model, max_retries=1)
            logger.info(f"Chat model {self.model} is available")
            return True
        except Exception as e:
            logger.warning(
                f"Chat model {self.model} may not be available: {str(e)}"
            )
            return False

    def set_user_chat_mode(self, user_id, chat_mode):
        """
        Set user's chat mode in the database

        Args:
            user_id: Telegram user ID
            chat_mode: 0 for data cleaning mode, 1 for chat mode

        Returns:
            Boolean indicating success
        """
        return db.set_user_chat_mode(user_id, chat_mode)

    def get_user_chat_mode(self, user_id):
        """
        Get user's current chat mode

        Args:
            user_id: Telegram user ID

        Returns:
            0 for data cleaning mode, 1 for chat mode
        """
        return db.get_user_chat_mode(user_id)

    def is_chat_mode(self, user_id):
        """
        Check if user is in chat mode

        Args:
            user_id: Telegram user ID

        Returns:
            Boolean indicating if user is in chat mode
        """
        return db.get_user_chat_mode(user_id) == 1

    def switch_to_chat_mode(self, user_id):
        """
        Switch user to chat mode

        Args:
            user_id: Telegram user ID

        Returns:
            Welcome message for chat mode
        """
        success = self.set_user_chat_mode(user_id, 1)
        if success:
            return (
                "🤖 *Chat Mode Activated*\n\n"
                "I'm now your personal assistant. Ask me anything!\n\n"
                "Your chat history will be saved for context.\n"
                "To switch back to Data Cleaning mode, use /datamode command."
            )
        else:
            return "⚠️ Error switching to chat mode. Please try again."

    def switch_to_data_mode(self, user_id):
        """
        Switch user to data cleaning mode

        Args:
            user_id: Telegram user ID

        Returns:
            Confirmation message for data mode
        """
        success = self.set_user_chat_mode(user_id, 0)
        if success:
            return (
                "📊 *Data Cleaning Mode Activated*\n\n"
                "Send me a CSV file and I'll clean it for you.\n\n"
                "To switch back to Chat mode, use /chatmode command."
            )
        else:
            return "⚠️ Error switching to data cleaning mode. Please try again."

    def clear_history(self, user_id):
        """
        Clear user's chat history

        Args:
            user_id: Telegram user ID

        Returns:
            Confirmation message
        """
        success = db.clear_chat_history(user_id)
        if success:
            return "🧹 Your chat history has been cleared."
        else:
            return "⚠️ Error clearing chat history. Please try again."

    def process_message(self, user_id, message_text):
        """
        Process a user message and generate a response

        Args:
            user_id: Telegram user ID
            message_text: User's message text

        Returns:
            Assistant's response
        """
        try:
            # Check if Ollama is running
            if not is_ollama_running():
                return (
                    "⚠️ AI service is currently unavailable. Please try again later."
                )

            # Store user message in database
            db.add_message(user_id, "user", message_text)

            # Get conversation context
            context = self._prepare_context(user_id)

            # Generate prompt with context
            prompt = self._generate_prompt(context, message_text)

            # Get response from Ollama
            start_time = time.time()
            response = query_ollama(prompt, self.model)
            end_time = time.time()

            logger.info(
                f"Generated chat response in {end_time - start_time:.2f} seconds"
            )

            # Store assistant response in database
            db.add_message(user_id, "assistant", response)

            return response
        except Exception as e:
            error_message = f"Error processing message: {str(e)}"
            logger.error(error_message)
            logger.error(traceback.format_exc())
            return (
                "⚠️ I encountered an error while processing your message. "
                "Please try again later."
            )

    def _prepare_context(self, user_id):
        """
        Prepare conversation context for the model

        Args:
            user_id: Telegram user ID

        Returns:
            Formatted context string
        """
        # Get user's chat history
        context = db.get_formatted_chat_context(user_id)

        # Trim context if too long
        if len(context) > MAX_CONTEXT_LENGTH:
            # Keep the beginning of context (system prompt) and the most recent messages
            context_parts = context.split("\n")
            system_part = context_parts[0] + "\n"
            remaining_length = MAX_CONTEXT_LENGTH - len(system_part)
            recent_part = "\n".join(context_parts[-remaining_length:])
            context = (
                system_part + "...[older messages omitted]...\n" + recent_part
            )

        return context

    def _generate_prompt(self, context, message):
        """
        Generate a complete prompt with system prompt, context, and user message

        Args:
            context: Conversation context
            message: User's message

        Returns:
            Complete prompt for Ollama
        """
        system_prompt = DEFAULT_SYSTEM_PROMPT

        if context:
            prompt = (
                f"{system_prompt}\n\n{context}\n\nUser: {message}\nAssistant:"
            )
        else:
            prompt = f"{system_prompt}\n\nUser: {message}\nAssistant:"

        return prompt

    def get_help_message(self):
        """
        Get help message for chat mode

        Returns:
            Help message text
        """
        return """🤖 *Chat Mode Help*

You can chat with me about anything! Here are some commands:

/chatmode - Switch to chat mode
/datamode - Switch to data cleaning mode
/clear - Clear your chat history
/help - Show this help message

Your conversation history is saved to provide context for our discussions. 
Use /clear to reset it anytime."""


# Create singleton instance for easy import
chat_handler = ChatHandler()

