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
    update = request.get_json(silent=True)
    if not update:
        return "no update", 200

    from telebot.types import Update
    try:
        update_obj = Update.de_json(update)
        bot.process_new_updates([update_obj])
    except Exception as e:
        print("Webhook processing error:", repr(e))

    return "ok", 200

def setup_webhook():
    if not PUBLIC_URL:
        print("PUBLIC_URL is not set; cannot set webhook automatically.")
        return

    try:
        info = bot.get_webhook_info()
        if info and getattr(info, "url", "") == WEBHOOK_URL:
            print("Webhook already set correctly:", WEBHOOK_URL)
            return

        bot.remove_webhook()

        if WEBHOOK_SECRET:
            bot.set_webhook(url=WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
        else:
            bot.set_webhook(url=WEBHOOK_URL)

        print("Webhook set to:", WEBHOOK_URL)

    except Exception as e:
        print("Webhook setup failed (will continue running):", repr(e)) 

def setup_webhook():
    if not PUBLIC_URL:
        print("PUBLIC_URL is not set; cannot set webhook automatically.")
        return

    try:
        bot.remove_webhook()

        if WEBHOOK_SECRET:
            bot.set_webhook(url=WEBHOOK_URL, secret_token=WEBHOOK_SECRET)
        else:
            bot.set_webhook(url=WEBHOOK_URL)

        print("Webhook set to:", WEBHOOK_URL)

    except Exception as e:
        # IMPORTANT: don't crash the server if Telegram rate-limits
        print("Webhook setup failed (will continue running):", repr(e))

if __name__ == "__main__":
    # Render provides PORT
    port = int(os.getenv("PORT", "10000"))
    setup_webhook()
    app.run(host="0.0.0.0", port=port)
