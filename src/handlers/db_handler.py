# db_handler.py

import json
import os
import sqlite3
import traceback
import sys
from pathlib import Path

# Add parent directories to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent))

from src.core.utils import logger

# Configuration
DB_PATH = str(Path(__file__).parent.parent.parent / "db" / "bot_data.db")
MAX_HISTORY_MESSAGES = 20  # Maximum number of messages to keep in context


class DBHandler:
    def __init__(self, db_path=DB_PATH):
        """
        Initialize the database handler

        Args:
            db_path: Path to the SQLite database file
        """
        self.db_path = db_path
        self._ensure_db_exists()

    def _get_connection(self):
        """
        Get a database connection with row factory set to return rows as dictionaries

        Returns:
            SQLite connection object
        """
        try:
            conn = sqlite3.connect(self.db_path)
            conn.row_factory = sqlite3.Row
            return conn
        except sqlite3.Error as e:
            logger.error(f"Database connection error: {str(e)}")
            raise

    def _ensure_db_exists(self):
        """
        Check if the database exists and create it if it doesn't

        Creates necessary tables for users and chat history
        """
        try:
            # Create directory if it doesn't exist
            db_dir = os.path.dirname(self.db_path)
            if db_dir and not os.path.exists(db_dir):
                os.makedirs(db_dir)

            # Get connection and create tables
            conn = self._get_connection()
            cursor = conn.cursor()

            # Create users table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                chat_mode INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                last_active TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                preferences TEXT DEFAULT '{}'
            )
            """
            )

            # Create chat history table
            cursor.execute(
                """
            CREATE TABLE IF NOT EXISTS chat_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (user_id) REFERENCES users (user_id)
            )
            """
            )

            conn.commit()
            conn.close()
            logger.info("Database initialized successfully")
        except sqlite3.Error as e:
            logger.error(f"Database initialization error: {str(e)}")
            logger.error(traceback.format_exc())
            raise

    # User Management Functions
    def get_user(self, user_id):
        """
        Get user information from the database

        Args:
            user_id: Telegram user ID

        Returns:
            User data as dictionary or None if user doesn't exist
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()

            if user:
                # Convert row to dict and parse preferences
                user_dict = dict(user)
                user_dict["preferences"] = json.loads(user_dict["preferences"])
                conn.close()
                return user_dict

            conn.close()
            return None
        except sqlite3.Error as e:
            logger.error(f"Error getting user {user_id}: {str(e)}")
            return None

    def add_or_update_user(self, user_id, chat_mode=None, preferences=None):
        """
        Add a new user or update an existing user

        Args:
            user_id: Telegram user ID
            chat_mode: 0 for data cleaning mode, 1 for chat mode
            preferences: Dictionary of user preferences

        Returns:
            Boolean indicating success
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Check if user exists
            cursor.execute("SELECT * FROM users WHERE user_id = ?", (user_id,))
            user = cursor.fetchone()

            if user:
                # Update existing user
                updates = []
                params = []

                if chat_mode is not None:
                    updates.append("chat_mode = ?")
                    params.append(chat_mode)

                if preferences is not None:
                    updates.append("preferences = ?")
                    params.append(json.dumps(preferences))

                # Always update last_active
                updates.append("last_active = CURRENT_TIMESTAMP")

                if updates:
                    query = f"UPDATE users SET {', '.join(updates)} WHERE user_id = ?"
                    params.append(user_id)
                    cursor.execute(query, params)
            else:
                # Add new user
                if preferences is None:
                    preferences = {}
                if chat_mode is None:
                    chat_mode = 0

                cursor.execute(
                    "INSERT INTO users (user_id, chat_mode, preferences) VALUES (?, ?, ?)",
                    (user_id, chat_mode, json.dumps(preferences)),
                )

            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adding/updating user {user_id}: {str(e)}")
            return False

    def set_user_chat_mode(self, user_id, chat_mode):
        """
        Set user's chat mode

        Args:
            user_id: Telegram user ID
            chat_mode: 0 for data cleaning mode, 1 for chat mode

        Returns:
            Boolean indicating success
        """
        return self.add_or_update_user(user_id, chat_mode=chat_mode)

    def get_user_chat_mode(self, user_id):
        """
        Get user's current chat mode

        Args:
            user_id: Telegram user ID

        Returns:
            0 for data cleaning mode, 1 for chat mode, 0 as default if user doesn't exist
        """
        user = self.get_user(user_id)
        if user:
            return user.get("chat_mode", 0)
        # Create user with default mode if not exists
        self.add_or_update_user(user_id)
        return 0

    def update_user_preference(self, user_id, key, value):
        """
        Update a specific user preference

        Args:
            user_id: Telegram user ID
            key: Preference key
            value: Preference value

        Returns:
            Boolean indicating success
        """
        try:
            user = self.get_user(user_id)
            preferences = user.get("preferences", {}) if user else {}
            preferences[key] = value
            return self.add_or_update_user(user_id, preferences=preferences)
        except Exception as e:
            logger.error(f"Error updating user preference: {str(e)}")
            return False

    # Chat History Functions
    def add_message(self, user_id, role, content):
        """
        Add a message to chat history

        Args:
            user_id: Telegram user ID
            role: 'user' or 'assistant'
            content: Message content

        Returns:
            Boolean indicating success
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            # Ensure user exists
            self.add_or_update_user(user_id)

            # Add message
            cursor.execute(
                "INSERT INTO chat_history (user_id, role, content) VALUES (?, ?, ?)",
                (user_id, role, content),
            )

            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error adding message for user {user_id}: {str(e)}")
            return False

    def get_chat_history(self, user_id, limit=MAX_HISTORY_MESSAGES):
        """
        Get chat history for a user

        Args:
            user_id: Telegram user ID
            limit: Maximum number of messages to retrieve

        Returns:
            List of message dictionaries with role and content
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute(
                "SELECT role, content, timestamp FROM chat_history WHERE user_id = ? ORDER BY timestamp DESC LIMIT ?",
                (user_id, limit),
            )
            messages = cursor.fetchall()

            # Convert to list of dictionaries and reverse to chronological order
            history = [dict(message) for message in messages]
            history.reverse()  # Get chronological order

            conn.close()
            return history
        except sqlite3.Error as e:
            logger.error(f"Error getting chat history for user {user_id}: {str(e)}")
            return []

    def clear_chat_history(self, user_id):
        """
        Clear chat history for a user

        Args:
            user_id: Telegram user ID

        Returns:
            Boolean indicating success
        """
        try:
            conn = self._get_connection()
            cursor = conn.cursor()

            cursor.execute("DELETE FROM chat_history WHERE user_id = ?", (user_id,))

            conn.commit()
            conn.close()
            return True
        except sqlite3.Error as e:
            logger.error(f"Error clearing chat history for user {user_id}: {str(e)}")
            return False

    def get_formatted_chat_context(self, user_id, limit=MAX_HISTORY_MESSAGES):
        """
        Get formatted chat context for LLM prompt

        Args:
            user_id: Telegram user ID
            limit: Maximum number of messages to include

        Returns:
            Formatted string for LLM context
        """
        history = self.get_chat_history(user_id, limit)
        if not history:
            return ""

        context = "Previous conversation:\n"
        for msg in history:
            role_prefix = "User: " if msg["role"] == "user" else "Assistant: "
            context += f"{role_prefix}{msg['content']}\n"

        return context


# Create a singleton instance for easy import
db = DBHandler()

# Test connection and initialization when module is imported
try:
    test_conn = sqlite3.connect(DB_PATH)
    test_conn.close()
    logger.info("Database connection successful")
except sqlite3.Error as e:
    logger.error(f"Database connection test failed: {str(e)}")

