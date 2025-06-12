#!/usr/bin/env python3
"""
restart_bot.py

Utility to cleanly restart your MT5 trading bot from any
Windows or UNIX shell without manual directory changes.

Usage:
  1. Place this file (restart_bot.py) in your mt5-bot project folder.
  2. Open a new Command Prompt or terminal.
  3. Run:
       python restart_bot.py

It will:
  - Change into the project directory
  - Install or upgrade required packages:
      MetaTrader5, pandas, python-telegram-bot
  - Launch bot.py with the same interpreter
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Determine the directory where this script resides
    project_dir = Path(__file__).parent.resolve()
    print(f"→ Changing working directory to: {project_dir}")
    os.chdir(project_dir)

    # Install or update dependencies
    print("→ Installing/updating dependencies...")
    python = sys.executable
    subprocess.run([
        python, "-m", "pip", "install", "--upgrade",
        "MetaTrader5", "pandas", "python-telegram-bot"
    ], check=True)

    # Launch the bot
    print("→ Starting bot.py...")
    subprocess.run([python, "bot.py"], check=True)

if __name__ == "__main__":
    main()
