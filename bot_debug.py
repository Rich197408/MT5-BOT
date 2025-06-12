# bot_debug.py

import time
import threading
import datetime as dt
import pytz
import pandas as pd
import MetaTrader5 as mt5
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === CONFIGURATION ===
ACCOUNT_LOGIN      = 92214559
ACCOUNT_PASSWORD   = "E_HrX6Wp"
ACCOUNT_SERVER     = "MetaQuotes-Demo"
SYMBOL             = "XAUUSD"
BROKER_TZ          = "Etc/GMT-1"

LOT_SIZE           = 1.0
ATR_PERIOD         = 14
ATR_MULTIPLIER     = 1.25
RETRACE_PCT        = 0.65
SL_PIPS            = 35
TP1_PIPS           = 40
TP2_PIPS           = 70
PART1_SIZE         = 0.8
PART2_SIZE         = 0.2
DAILY_CAP_USD      = -800
COMMISSION_PER_LOT = 0.0

SESSIONS = {"London":(7,16), "New York":(12,21)}
TELEGRAM_TOKEN     = "7777754225:AAGJU4TLP2rS4LbM1lbK3xLi3u2s04GzudY"
CHAT_ID            = None

# Debug override: force a single order_send on first tick
DEBUG_OVERRIDE = True

bot_active = True
daily_pnl  = {}
last_date  = None
high_impact_events = []

async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global bot_active, CHAT_ID
    bot_active, CHAT_ID = True, update.effective_chat.id
    await update.message.reply_text("✅ Bot resumed (debug mode).")

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global bot_active
    bot_active = False
    await update.message.reply_text("⏸ Bot paused.")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    acct = mt5.account_info()
    bal, eq = acct.balance, acct.equity
    today = dt.datetime.utcnow().date().isoformat()
    pnl = daily_pnl.get(today, 0.0)
    pos = mt5.positions_get(symbol=SYMBOL) or []
    dirs = ["BUY" if p.type==mt5.ORDER_TYPE_BUY else "SELL" for p in pos]
    text = (
        f"Debug Bot: {'🟢 Active' if bot_active else '🔴 Paused'}\n"
        f"Balance: ${bal:.2f}  Equity: ${eq:.2f}\n"
        f"Today PnL: ${pnl:.2f} (cap {DAILY_CAP_USD:+})\n"
        f"Open positions: {len(pos)} [{','.join(dirs)}]"
    )
    await update.message.reply_text(text)

def tag_session(ts):
    for name,(s,e) in SESSIONS.items():
        if s <= ts.hour < e: return name
    return None

def compute_indicators(df30, df1h):
    df30["prev_close"] = df30["close"].shift(1)
    tr = (df30[["high","prev_close"]].max(axis=1)
         - df30[["low","prev_close"]].min(axis=1))
    df30["atr"] = tr.rolling(ATR_PERIOD).mean()
    df1h["ema200"] = df1h["close"].ewm(span=200, adjust=False).mean()

def detect_1h_ob(df1h):
    ob = set()
    for i in range(1,len(df1h)-1):
        p,c,n = df1h.iloc[i-1], df1h.iloc[i], df1h.iloc[i+1]
        if (p.close>p.open and n.close<c.close) or (p.close<p.open and n.close>c.close):
            ob.add(df1h.index[i])
    return ob

def clamp_volume(desired, info):
    vmin, vmax, step = info.volume_min, info.volume_max, info.volume_step
    vol = max(vmin, min(desired, vmax))
    steps = int((vol - vmin)/step)
    return round(vmin + steps*step, 8)

def send_telegram(app, msg):
    if CHAT_ID:
        app.bot.send_message(chat_id=CHAT_ID, text=msg)

def trading_loop(app):
    global daily_pnl, last_date, DEBUG_OVERRIDE

    mt5.initialize()
    mt5.login(ACCOUNT_LOGIN, ACCOUNT_PASSWORD, ACCOUNT_SERVER)
    info = mt5.symbol_info(SYMBOL)
    point = info.point

    print(f">>> SYMBOL {SYMBOL} volume_min={info.volume_min}, step={info.volume_step}, max={info.volume_max}")
    send_telegram(app, "🤖 Debug Bot started & logged in.")

    while True:
        now = dt.datetime.utcnow().replace(tzinfo=pytz.UTC)
        today = now.date().isoformat()
        if last_date != today:
            daily_pnl = {today:0.0}
            last_date = today

        if not bot_active:
            time.sleep(1); continue

        # Fetch & localize
        b30 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M30, 0, 500)
        b1h = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1,  0, 200)
        df30 = pd.DataFrame(b30); df1h = pd.DataFrame(b1h)
        for df in (df30, df1h):
            df["time"] = (pd.to_datetime(df["time"], unit="s")
                          .dt.tz_localize(BROKER_TZ)
                          .dt.tz_convert("UTC"))
            df.set_index("time", inplace=True)

        compute_indicators(df30, df1h)
        ob1h = detect_1h_ob(df1h)

        acct   = mt5.account_info()
        margin = acct.margin_free
        spread = info.spread * point
        comm   = COMMISSION_PER_LOT * LOT_SIZE

        if len(df30) < 3:
            time.sleep(1); continue

        T    = df30.index[-2]
        prev, curr, nxt = df30.iloc[-3], df30.iloc[-2], df30.iloc[-1]
        session = tag_session(T)
        print(f"{now.isoformat()} — Bar: {T.isoformat()}, session={session}")

        # Compute entry params
        height   = curr.high - curr.low
        entry_lvl= (curr.high-RETRACE_PCT*height) if prev.close>prev.open else (curr.low+RETRACE_PCT*height)
        SL_price = (curr.high+SL_PIPS*point)   if prev.close>prev.open else (curr.low-SL_PIPS*point)
        TP_price = (entry_lvl-TP2_PIPS*point)  if prev.close>prev.open else (entry_lvl+TP2_PIPS*point)
        direction= "SELL" if prev.close>prev.open else "BUY"
        price    = mt5.symbol_info_tick(SYMBOL).bid if direction=="SELL" else mt5.symbol_info_tick(SYMBOL).ask

        # Force debug order once
        if DEBUG_OVERRIDE:
            DEBUG_OVERRIDE = False
            vol = clamp_volume(LOT_SIZE, info)
            req = {
                "action":    mt5.TRADE_ACTION_DEAL,
                "symbol":    SYMBOL,
                "volume":    vol,
                "type":      mt5.ORDER_TYPE_SELL if direction=="SELL" else mt5.ORDER_TYPE_BUY,
                "price":     price,
                "sl":        SL_price,
                "tp":        TP_price,
                "deviation": 5,
                "magic":     1234501,
                "comment":   "DEBUG_ORDER"
            }
            print(">> ORDER SEND REQ:", req)
            res = mt5.order_send(req)
            print("<< ORDER SEND RES:", res)
        time.sleep(1)

def main():
    app = ApplicationBuilder().token(TELEGRAM_TOKEN).build()
    app.add_handler(CommandHandler("start",  cmd_start))
    app.add_handler(CommandHandler("stop",   cmd_stop))
    app.add_handler(CommandHandler("status", cmd_status))

    threading.Thread(target=trading_loop, args=(app,), daemon=True).start()
    app.run_polling()

if __name__=="__main__":
    main()
