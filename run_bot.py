# run_bot.py

#!/usr/bin/env python3
"""
Utility script to re‑initialize your environment and launch the MT5 bot.
Place this file in your project folder (e.g. C:\Users\Administrator\Downloads\mt5-bot),
then from any shell run:

    python run_bot.py

It will:

1. Change working directory into this script’s folder.
2. Install/upgrade required Python packages.
3. Launch bot.py in this environment.
"""

import os
import sys
import subprocess
from pathlib import Path

def main():
    # Determine project directory (where this script lives)
    project_dir = Path(__file__).parent.resolve()
    print(f"→ Changing working dir to: {project_dir}")
    os.chdir(project_dir)

    # Ensure required packages are installed
    print("→ Installing/Updating dependencies: MetaTrader5, pandas, python-telegram-bot")
    python = sys.executable
    subprocess.run([python, "-m", "pip", "install", "--upgrade",
                    "MetaTrader5", "pandas", "python-telegram-bot"], check=True)

    # Launch the bot
    print("→ Starting MT5 bot (bot.py)...")
    subprocess.run([python, "bot.py"], check=True)

if __name__ == "__main__":
    main()
