import os
import json
import hmac
import hashlib
import urllib.parse
from api import api
from flask import Flask, request, send_from_directory, jsonify

from variables import bot  # uses your existing bot instance from variables.py

import best_instagram_downloader  # ensures all @bot.message_handler decorators run

app = Flask(__name__)
app.register_blueprint(api)

BOT_TOKEN = (os.getenv("BEST_INSTAGRAM_DOWNLOADER_BOT_API") or "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Missing BEST_INSTAGRAM_DOWNLOADER_BOT_API env var")
    
def _tg_webapp_secret_key(bot_token: str) -> bytes:
    # Telegram WebApp signature key derivation
    return hmac.new(b"WebAppData", bot_token.encode("utf-8"), hashlib.sha256).digest()

def verify_telegram_webapp_init_data(init_data: str, bot_token: str, max_age_seconds: int = 3600) -> dict:
    """
    Verifies Telegram Mini App initData and returns parsed fields.
    Raises ValueError if invalid.
    """
    if not init_data:
        raise ValueError("Missing initData")

    parsed = dict(urllib.parse.parse_qsl(init_data, keep_blank_values=True))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing hash")

    # Optional freshness check
    auth_date = int(parsed.get("auth_date", "0") or "0")
    if auth_date:
        now = int(__import__("time").time())
        if now - auth_date > max_age_seconds:
            raise ValueError("initData is too old")

    data_check_string = "\n".join(f"{k}={parsed[k]}" for k in sorted(parsed.keys()))

    secret_key = _tg_webapp_secret_key(bot_token)
    computed_hash = hmac.new(secret_key, data_check_string.encode("utf-8"), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed_hash, received_hash):
        raise ValueError("Invalid initData signature")

    return parsed

def extract_user_id_from_init_data_fields(fields: dict) -> int:
    user_raw = fields.get("user")
    if not user_raw:
        raise ValueError("No user in initData")

    user_obj = json.loads(user_raw)
    user_id = int(user_obj.get("id"))
    return user_id 

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
