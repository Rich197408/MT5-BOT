# bot.py
import logging
import sys
import MetaTrader5 as mt5
from telegram import Update
from telegram.ext import Application, CommandHandler, ContextTypes

# import your backtest runner
from confluence_detector.backtest import run_backtest

# ─── CONFIG ────────────────────────────────────────────────────────────────────
# MT5
MT5_PATH = r"C:\Program Files\MetaTrader 5\terminal64.exe"
ACCOUNT   = 92214559
PASSWORD  = "E_HrX6Wp"
SERVER    = "MetaQuotes-Demo"

# Telegram
TELE_TOKEN = "7777754225:AAGJU4TLP2rS4LbM1lbK3xLi3u2s04GzudY"

# ─── LOGGING ───────────────────────────────────────────────────────────────────
logging.basicConfig(
    format="%(asctime)s %(levelname)s %(message)s",
    level=logging.INFO,
    stream=sys.stdout,
)
logger = logging.getLogger(__name__)


# ─── COMMAND HANDLERS ─────────────────────────────────────────────────────────

async def runbacktest_cmd(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handler for /runbacktest"""
    await update.message.reply_text("🔍 Starting backtest…")
    try:
        # run_backtest() should return a formatted string summary
        summary = run_backtest()
        # split long messages if needed
        for chunk in summary.split("\n\n"):
            await update.message.reply_text(chunk)
        await update.message.reply_text("✅ Backtest complete.")
    except Exception as e:
        logger.exception("Backtest failed")
        await update.message.reply_text(f"⚠️ Backtest error: {e}")


# ─── MAIN ─────────────────────────────────────────────────────────────────────

def main():
    # 1) Initialize MT5
    if not mt5.initialize(path=MT5_PATH, login=ACCOUNT, password=PASSWORD, server=SERVER):
        err = mt5.last_error()
        logger.error(f"❌ MT5 init failed: {err}")
        sys.exit(1)
    logger.info(f"✅ MT5 initialized: {ACCOUNT} @ {SERVER}")

    # 2) Build Telegram application
    app = Application.builder().token(TELE_TOKEN).build()

    # 3) Register handlers
    app.add_handler(CommandHandler("runbacktest", runbacktest_cmd))

    # 4) Start polling
    logger.info("🚀 Bot starting…")
    app.run_polling()


if __name__ == "__main__":
    main()

