#!/usr/bin/env python3
"""Send one daily Telegram report from stock-drop-notifier verbose output."""
import os
import re
import sys
import urllib.parse
import urllib.request
from datetime import datetime
from zoneinfo import ZoneInfo

data = sys.stdin.read()
pattern = re.compile(r"^.*?\s{2}(.+?) \(([^)]+)\): (OK|TRIGGERED) \(Current: \$([\d.]+), Peak: \$([\d.]+), Change: ([-\d.]+)%, Threshold: ([-\d.]+)%\)", re.M)
matches = pattern.findall(data)
date = datetime.now(ZoneInfo("Europe/Berlin")).strftime("%d.%m.%Y")
if len(matches) != 2:
    message = f"ETF-Tagesbericht {date}\nKurspruefung unvollstaendig. Bitte GitHub Actions kontrollieren."
    valid = False
else:
    lines = [f"ETF-Tagesbericht {date}", "Stand: letzter verfuegbarer Tagesschluss (USD)", ""]
    for name, symbol, status, price, peak, change, threshold in matches:
        state = "DIP-ALARM" if status == "TRIGGERED" else "Kein Dip-Alarm"
        lines.append(f"{name} ({symbol}): {price} USD | {change}% vom 1-Monats-Hoch | Grenze {threshold}% | {state}")
    lines.extend(["", "Referenz-ETFs in USD, keine Kaufempfehlung."])
    message = "\n".join(lines)
    valid = True

token = os.environ["TELEGRAM_BOT_TOKEN"].strip()
chat = os.environ["TELEGRAM_CHAT_ID"].strip()
url = f"https://api.telegram.org/bot{token}/sendMessage"
payload = urllib.parse.urlencode({"chat_id": chat, "text": message}).encode()
with urllib.request.urlopen(urllib.request.Request(url, data=payload), timeout=25) as response:
    body = response.read().decode()
    if '"ok":true' not in body.replace(" ", ""):
        raise RuntimeError("Telegram did not confirm delivery")
print("Daily Telegram report sent.")
if not valid:
    sys.exit("ETF data incomplete; sent error notification")
