import time
import threading
import datetime as dt
import pytz
import pandas as pd
import MetaTrader5 as mt5
from telegram import Update
from telegram.ext import ApplicationBuilder, CommandHandler, ContextTypes

# === CONFIGURATION ===
# Your desired MT5 login (demo) – keep the bot locked to this
ACCOUNT_LOGIN    = 79002759
ACCOUNT_PASSWORD = "nimED60##"
ACCOUNT_SERVER   = "FundedNext-Server4"

SYMBOL           = "XAUUSD"

# Strategy A parameters
LOT_SIZE         = 1.0
ATR_PERIOD       = 14
ATR_MULTIPLIER   = 1.25
RETRACE_PCT      = 0.65
SL_PIPS          = 35
TP_PIPS          = 70

# UTC session windows: London 07–16, NY 12–21
SESSIONS = {
    "London":   (7, 16),
    "NewYork": (12, 21),
}

# Telegram
TELEGRAM_TOKEN   = "7777754225:AAGJU4TLP2rS4LbM1lbK3xLi3u2s04GzudY"
CHAT_ID          = None
bot_active       = False

# ——— Telegram handlers ——————————————————
async def cmd_start(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global bot_active, CHAT_ID
    bot_active, CHAT_ID = True, update.effective_chat.id
    await update.message.reply_text("✅ Bot started. Trading enabled (GMT sessions).")

async def cmd_stop(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    global bot_active
    bot_active = False
    await update.message.reply_text("⏸ Bot paused.")

async def cmd_status(update: Update, ctx: ContextTypes.DEFAULT_TYPE):
    acct = mt5.account_info()
    if not acct:
        await update.message.reply_text("⚠️ MT5 not connected.")
        return
    now_utc = dt.datetime.utcnow().strftime("%H:%M:%S")
    await update.message.reply_text(
        f"Account: {acct.login}\n"
        f"Server: {acct.server}\n"
        f"Time (UTC): {now_utc}\n"
        f"Status: {'Active' if bot_active else 'Paused'}\n"
        f"Balance: ${acct.balance:.2f}  Equity: ${acct.equity:.2f}"
    )

# ——— Helpers —————————————————————
def in_session(now_utc: dt.datetime) -> bool:
    return any(start <= now_utc.hour < end for start, end in SESSIONS.values())

def clamp_lot(v: float, info) -> float:
    vmin, vmax, step = info.volume_min, info.volume_max, info.volume_step
    vol = max(vmin, min(v, vmax))
    # round to nearest step
    steps = int((vol - vmin) / step)
    return round(vmin + steps * step, 8)

# ——— MT5 login enforcement —————————————————————
def ensure_login():
    """Attach to MT5, then login to the desired account."""
    mt5.shutdown()
    if not mt5.initialize():
        print("❌ mt5.initialize() failed; is MT5 running?")
        return False

    ok = mt5.login(ACCOUNT_LOGIN, ACCOUNT_PASSWORD, ACCOUNT_SERVER)
    if not ok:
        err = mt5.last_error()
        print(f"❌ mt5.login() failed: {err}")
        return False

    acct = mt5.account_info()
    print(f"🔑 Logged into MT5 Account #{acct.login} on {acct.server}")
    return True

# ——— Trading loop —————————————————————
def trading_loop(app):
    global bot_active

    # 1) Force-login at startup
    if not ensure_login():
        return

    info  = mt5.symbol_info(SYMBOL)
    point = info.point

    print(f"=== BOT READY: {SYMBOL}, SL {SL_PIPS}p, TP {TP_PIPS}p ===")
    if CHAT_ID:
        app.bot.send_message(CHAT_ID, "🤖 Bot is live (GMT sessions).")

    while True:
        now_utc = dt.datetime.utcnow().replace(tzinfo=pytz.UTC)

        # 2) Heartbeat
        sess = None
        for name,(s,e) in SESSIONS.items():
            if s <= now_utc.hour < e:
                sess = name
                break
        print(f"{now_utc.isoformat()} — heartbeat (session={sess})", flush=True)

        # 3) Auto-re-login if needed
        acct = mt5.account_info()
        if not acct or acct.login != ACCOUNT_LOGIN:
            print(f"⚠️ Detected login #{getattr(acct,'login',None)}; re-logging to {ACCOUNT_LOGIN}")
            if not ensure_login():
                time.sleep(30)
                continue
            info  = mt5.symbol_info(SYMBOL)
            point = info.point

        # 4) Only trade if /start and in valid session
        if bot_active and sess:
            # Fetch bars
            b30 = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_M30, 0, 500)
            b1h = mt5.copy_rates_from_pos(SYMBOL, mt5.TIMEFRAME_H1,  0, 200)
            df30, df1h = pd.DataFrame(b30), pd.DataFrame(b1h)

            # Convert to UTC index
            for df in (df30, df1h):
                df["time"] = pd.to_datetime(df["time"], unit="s").dt.tz_localize("UTC")
                df.set_index("time", inplace=True)

            # ATR on 30m
            df30["prev_close"] = df30["close"].shift(1)
            tr = (
                df30[["high","prev_close"]].max(1) -
                df30[["low","prev_close"]].min(1)
            )
            df30["atr"] = tr.rolling(ATR_PERIOD).mean()

            # EMA200 on 1h
            df1h["ema200"] = df1h["close"].ewm(span=200, adjust=False).mean()

            if len(df30) >= 3:
                T, prev, curr, nxt = (
                    df30.index[-2],
                    df30.iloc[-3],
                    df30.iloc[-2],
                    df30.iloc[-1],
                )

                # ATR threshold
                if (curr.high - curr.low) >= ATR_MULTIPLIER * curr["atr"]:
                    # 30m Order Block detection
                    bear = prev.close>prev.open and nxt.close<curr.close
                    bull = prev.close<prev.open and nxt.close>curr.close
                    if bear or bull:
                        # 1h OB check
                        H = T.floor("H")
                        ob1h = set()
                        for i in range(1, len(df1h)-1):
                            p,c,n = df1h.iloc[i-1], df1h.iloc[i], df1h.iloc[i+1]
                            if (p.close>p.open and n.close<c.close) or (p.close<p.open and n.close>c.close):
                                ob1h.add(df1h.index[i])
                        if H in ob1h:
                            price1h = df1h.at[H,"close"]
                            ema200   = df1h.at[H,"ema200"]
                            direction = "SELL" if bear else "BUY"
                            # EMA200 filter
                            if not ((direction=="SELL" and price1h>=ema200)
                                    or (direction=="BUY" and price1h<=ema200)):
                                # Calculate entry zone
                                span  = curr.high - curr.low
                                entry = (
                                    curr.high - RETRACE_PCT*span
                                ) if direction=="SELL" else (
                                    curr.low  + RETRACE_PCT*span
                                )
                                tick  = mt5.symbol_info_tick(SYMBOL)
                                price = tick.bid if direction=="SELL" else tick.ask
                                sl    = price + (SL_PIPS*point if direction=="SELL" else -SL_PIPS*point)
                                tp    = price - (TP_PIPS*point if direction=="SELL" else -TP_PIPS*point)

                                # Only fire if price has reached retrace entry
                                if (direction=="SELL" and price>=entry) or (direction=="BUY" and price<=entry):
                                    # No opposite-direction open
                                    pos = mt5.positions_get(symbol=SYMBOL) or []
                                    sides = { "BUY" if p.type==mt5.ORDER_TYPE_BUY else "SELL" for p in pos }
                                    if not ((direction=="SELL" and "BUY" in sides)
                                            or (direction=="BUY"  and "SELL" in sides)):
                                        vol = clamp_lot(LOT_SIZE, info)
                                        if mt5.account_info().margin_free >= vol * info.margin_initial:
                                            req = {
                                                "action": mt5.TRADE_ACTION_DEAL,
                                                "symbol": SYMBOL,
                                                "volume": vol,
                                                "type":   mt5.ORDER_TYPE_SELL if direction=="SELL" else mt5.ORDER_TYPE_BUY,
                                                "price":  price,
                                                "sl":     sl,
                                                "tp":     tp,
                                                "deviation":5,
                                                "magic":  1234501,
                                                "comment":"StrategyA"
                                            }
                                            print(">> ORDER SEND:", req)
                                            res = mt5.order_send(req)
                                            print("<< RESULT:", res)
                                            if CHAT_ID and res.retcode == mt5.TRADE_RETCODE_DONE:
                                                app.bot.send_message(
                                                    CHAT_ID,
                                                    f"🟢 {direction} {vol:.2f} @ {price:.2f} SL={sl:.2f} TP={tp:.2f}"
                                                )

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
