import os
import json
from flask import Flask, request, abort

from variables import bot  # uses your existing bot instance from variables.py

import best_instagram_downloader  # ensures all @bot.message_handler decorators run

app = Flask(__name__)

BOT_TOKEN = (os.getenv("BEST_INSTAGRAM_DOWNLOADER_BOT_API") or "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Missing BEST_INSTAGRAM_DOWNLOADER_BOT_API env var")

WEBHOOK_SECRET = (os.getenv("WEBHOOK_SECRET") or "").strip()  # optional but recommended
PUBLIC_URL = (os.getenv("PUBLIC_URL") or "").strip()          # Render service URL (https://....onrender.com)

# Use a hard-to-guess path; token-in-path is common for Telegram bots
WEBHOOK_PATH = f"/webhook/{BOT_TOKEN}"
WEBHOOK_URL = f"{PUBLIC_URL}{WEBHOOK_PATH}" if PUBLIC_URL else ""

@app.get("/")
def health():
    return "ok"

@app.post(WEBHOOK_PATH)
def telegram_webhook():
    # Optional: a simple shared secret header check
    if WEBHOOK_SECRET:
        incoming = request.headers.get("X-Webhook-Secret", "")
        if incoming != WEBHOOK_SECRET:
            abort(403)

    update = request.get_json(silent=True)
    if not update:
        return "no update", 200

    # telebot expects an Update object; easiest is to feed raw JSON through types.Update
    from telebot.types import Update
    try:
        update_obj = Update.de_json(update)
        bot.process_new_updates([update_obj])
    except Exception as e:
        # Don't crash the web server; just log
        print("Webhook processing error:", repr(e))
    return "ok", 200

def setup_webhook():
    if not PUBLIC_URL:
        print("PUBLIC_URL is not set; cannot set webhook automatically.")
        return

    # Remove any existing webhook and set the new one
    bot.remove_webhook()
    # If you use WEBHOOK_SECRET, we’ll send it from Telegram via secret_token (supported by Telegram)
    if WEBHOOK_SECRET:
        bot.set_webhook(url=WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
    else:
        bot.set_webhook(url=WEBHOOK_URL)

    print("Webhook set to:", WEBHOOK_URL)

if __name__ == "__main__":
    # Render provides PORT
    port = int(os.getenv("PORT", "10000"))
    setup_webhook()
    app.run(host="0.0.0.0", port=port)