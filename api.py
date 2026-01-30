import json
import hmac
import hashlib
import urllib.parse
import time

from flask import Blueprint, request, jsonify, send_from_directory
from telebot import types

import os
from variables import bot

BOT_TOKEN = (os.getenv("BEST_INSTAGRAM_DOWNLOADER_BOT_API") or "").strip()
if not BOT_TOKEN:
    raise RuntimeError("Missing BEST_INSTAGRAM_DOWNLOADER_BOT_API env var")
from functions import (
    get_post_or_reel_shortcode_from_link,
    try_to_delete_message,
)
from riad_azz import get_instagram_media_links
from best_instagram_downloader import (
    wrong_pattern_msg,
    fail_msg,
    end_msg,
    caption_trail,
    bot_username,
    log,
)

api = Blueprint("api", __name__)

# ---------------------------
# Join-gate configuration
# ---------------------------
UPDATES_CHANNEL = "@quickgram_downloader"  # TODO: change this
JOIN_REQUIRED_ERROR = "Please join the updates channel first, then tap Download again."    

# ---------------------------
# Telegram Mini App security
# ---------------------------

def _tg_secret_key():
    return hmac.new(
        b"WebAppData",
        BOT_TOKEN.encode(),
        hashlib.sha256
    ).digest()

def verify_init_data(init_data: str, max_age: int = 3600) -> int:
    if not init_data:
        raise ValueError("Missing initData")

    parsed = dict(urllib.parse.parse_qsl(init_data))
    received_hash = parsed.pop("hash", None)
    if not received_hash:
        raise ValueError("Missing hash")

    auth_date = int(parsed.get("auth_date", 0))
    if time.time() - auth_date > max_age:
        raise ValueError("initData expired")

    data_check = "\n".join(f"{k}={parsed[k]}" for k in sorted(parsed))
    secret = _tg_secret_key()
    computed = hmac.new(secret, data_check.encode(), hashlib.sha256).hexdigest()

    if not hmac.compare_digest(computed, received_hash):
        raise ValueError("Invalid signature")

    user = json.loads(parsed["user"])
    return int(user["id"])
    
# Join Gate 
def is_user_joined_updates_channel(user_id: int) -> bool:
    """
    Returns True if user is a member/admin/creator in the updates channel.
    Note: for reliable checks, the bot should be an admin in the channel.
    """
    try:
        member = bot.get_chat_member(UPDATES_CHANNEL, user_id)
        status = getattr(member, "status", None)
        return status in ("member", "administrator", "creator")
    except Exception as e:
        # If we can't verify, treat as not joined (safe default)
        try:
            log(f"{bot_username} join-gate check error:\n{repr(e)}\nuser: {user_id}")
        except:
            pass
        return False

# ---------------------------
# Routes (LIVE HERE)
# ---------------------------

@api.get("/app")
def mini_app():
    return send_from_directory(".", "miniapp.html")

@api.post("/api/submit")
def submit_download():
    body = request.get_json(silent=True) or {}
    link = body.get("link", "").strip()
    init_data = body.get("initData", "").strip()

    if not link:
        return jsonify({"error": "Missing link"}), 400

    try:
        user_id = verify_init_data(init_data)

        # ✅ JOIN GATE ENFORCEMENT
        if not is_user_joined_updates_channel(user_id):
            return jsonify({
                "error": JOIN_REQUIRED_ERROR,
                "join_required": True
            }), 403

        process_link(user_id, link)
        return jsonify({"ok": True})

    except ValueError as e:
        # Auth/signature problems or expired initData
        try:
            log(f"{bot_username} miniapp auth error:\n{repr(e)}")
        except:
            pass
        return jsonify({"error": "Authorization failed"}), 403

    except Exception as e:
        try:
            log(f"{bot_username} miniapp error:\n{repr(e)}")
        except:
            pass
        return jsonify({"error": "Download failed. Try again later."}), 500

# ---------------------------
# Shared download logic
# ---------------------------

def process_link(chat_id: int, link: str):
    guide = bot.send_message(chat_id, "Ok wait a few moments...")

    shortcode = get_post_or_reel_shortcode_from_link(link)
    if not shortcode:
        try_to_delete_message(chat_id, guide.message_id)
        bot.send_message(chat_id, wrong_pattern_msg, parse_mode="HTML")
        return

    media_links, caption = get_instagram_media_links(shortcode)
    if not media_links:
        try_to_delete_message(chat_id, guide.message_id)
        bot.send_message(chat_id, fail_msg, parse_mode="HTML")
        return

    caption = caption or ""
    while len(caption) + len(caption_trail) > 1024:
        caption = caption[:-1]
    caption += caption_trail

    media = []
    for i, item in enumerate(media_links):
        if item["type"] == "video":
            m = types.InputMediaVideo(item["url"], caption if i == 0 else None)
        else:
            m = types.InputMediaPhoto(item["url"], caption if i == 0 else None)
        media.append(m)

    for i in range(0, len(media), 10):
        bot.send_media_group(chat_id, media[i:i+10])

    bot.send_message(chat_id, end_msg, parse_mode="HTML")
    try_to_delete_message(chat_id, guide.message_id)