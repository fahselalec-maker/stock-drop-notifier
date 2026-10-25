#!/usr/bin/env python3
"""Best-effort free delayed intraday ETF dip alerts; no exact lows predicted."""
import json, os, sys, urllib.request, urllib.parse
from datetime import datetime
from zoneinfo import ZoneInfo

ETFS = [("MSCI World", "URTH", -5.0), ("Nasdaq 100", "QQQ", -7.0)]

def fetch(symbol, interval, window):
    url = "https://query1.finance.yahoo.com/v8/finance/chart/" + urllib.parse.quote(symbol) + "?interval=" + interval + "&range=" + window
    req = urllib.request.Request(url, headers={"User-Agent": "ETF-Dip-Monitor/1.0", "Accept": "application/json"})
    with urllib.request.urlopen(req, timeout=25) as response:
        payload = json.load(response)
    item = payload["chart"]["result"][0]
    ts = item.get("timestamp", [])
    quotes = item["indicators"]["quote"][0]
    return [(t, float(v)) for t, v in zip(ts, quotes["close"]) if v is not None]

def main():
    now = datetime.now(ZoneInfo("America/New_York"))
    if now.weekday() > 4 or not ((now.hour == 9 and now.minute >= 30) or 10 <= now.hour < 16):
        print("Outside US market hours; no alerts.")
        return
    date = now.strftime("%Y-%m-%d")
    stamp_path = ".etf-notified"
    if os.path.isfile(stamp_path) and open(stamp_path, encoding="utf-8").read().strip() == date:
        print("Already notified today.")
        return
    messages = []
    for name, symbol, threshold in ETFS:
        try:
            history = fetch(symbol, "1d", "1mo")
            intraday = fetch(symbol, "15m", "1d")
            if len(history) < 5 or len(intraday) < 3:
                raise ValueError("insufficient price bars")
            peak = max(v for _, v in history)
            # Exclude the last possibly unfinished bar.
            last = intraday[-2][1]
            prev = intraday[-3][1]
            change = (last / peak - 1) * 100
            # Simple confirmation: last closed candle higher than previous.
            if change <= threshold and last > prev:
                messages.append(f"{name} ({symbol}): {last:.2f} USD, {change:.2f}% from month high. Rebound in last closed 15-minute bar.")
            print(f"{symbol}: price {last:.2f}, dip {change:.2f}%, rebound={last > prev}")
        except Exception as exc:
            print(f"{symbol}: data failed: {exc}", file=sys.stderr)
    if not messages:
        print("No confirmed entry signal.")
        return
    message = "ETF DIP SIGNAL (delayed/free price feed)\n" + "\n".join(messages) + "\nNot a guaranteed bottom or buy recommendation."
    token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
    chat = os.environ["TELEGRAM_CHAT_ID"].strip()
    url = "https://api.telegram.org/bot" + token + "/sendMessage"
    data = urllib.parse.urlencode({"chat_id": chat, "text": message}).encode()
    with urllib.request.urlopen(urllib.request.Request(url, data=data), timeout=25) as res:
        result = json.load(res)
    if not result.get("ok"):
        raise RuntimeError("Telegram did not confirm message")
    with open(stamp_path, "w", encoding="utf-8") as f:
        f.write(date)
    print("SENT_SIGNAL=true")

if __name__ == "__main__":
    main()
