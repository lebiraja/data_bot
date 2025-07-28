#!/usr/bin/env python3
"""
Data Bot - Main Entry Point
This file serves as the main entry point for the Data Bot application.
"""

import sys
from pathlib import Path

# Add the project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

# Import and run the bot
from src.core.bot import main

if __name__ == "__main__":
    main()
