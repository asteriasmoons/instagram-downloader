from functions import *
from riad_azz import get_instagram_media_links

import telebot
from telebot import types

# ----------------------------
# Join-gate configuration
# ----------------------------
UPDATES_CHANNEL = "@quickgram_downloader"  # TODO: set your channel username (must start with @)
UPDATES_CHANNEL_URL = "https://t.me/quickgram_downloader"  # TODO: set your channel URL

JOIN_GATE_MSG = """<b>Join Gate Entry</b>

Please join the updates channel. After joining, tap Refresh to unlock the bot.
"""

def is_user_joined_updates_channel(user_id: int) -> bool:
    """
    Returns True if user is a member/admin/creator in the updates channel.
    Note: For reliable checks, the bot should be an admin in the channel.
    """
    try:
        member = bot.get_chat_member(UPDATES_CHANNEL, user_id)
        status = getattr(member, "status", None)
        return status in ("member", "administrator", "creator")
    except Exception as e:
        # If we can't verify, treat as not joined (safe default)
        try:
            log(f"{bot_username} log:\n\njoin-check error: {repr(e)}\nuser: {user_id}")
        except:
            pass
        return False

def send_join_gate(chat_id: int):
    kb = types.InlineKeyboardMarkup(row_width=1)
    kb.add(
        types.InlineKeyboardButton("Join updates channel", url=UPDATES_CHANNEL_URL),
        types.InlineKeyboardButton("Refresh", callback_data="refresh_join_gate"),
    )
    bot.send_message(
        chat_id,
        JOIN_GATE_MSG,
        parse_mode="HTML",
        disable_web_page_preview=True,
        reply_markup=kb
    )

def require_join_or_gate(message) -> bool:
    """
    Returns True if allowed to proceed.
    If not allowed, sends the join gate and returns False.
    """
    user_id = message.from_user.id
    if is_user_joined_updates_channel(user_id):
        return True
    send_join_gate(message.chat.id)
    return False

@bot.callback_query_handler(func=lambda call: call.data == "refresh_join_gate")
def refresh_join_gate_handler(call):
    # Acknowledge the button press so Telegram doesn't show a loading spinner
    try:
        bot.answer_callback_query(call.id)
    except:
        pass

    user_id = call.from_user.id
    chat_id = call.message.chat.id

    if is_user_joined_updates_channel(user_id):
        # Optional: remove the gate message to reduce clutter
        try:
            bot.delete_message(chat_id, call.message.message_id)
        except:
            pass

        bot.send_message(chat_id, start_msg, parse_mode="HTML", disable_web_page_preview=True)
        try:
            log(f"{bot_username} log:\n\nuser: {chat_id}\n\nrefresh success (joined)")
        except:
            pass
    else:
        try:
            bot.answer_callback_query(
                call.id,
                "You still need to join the updates channel first.",
                show_alert=True
            )
        except:
            pass
        try:
            log(f"{bot_username} log:\n\nuser: {chat_id}\n\nrefresh denied (not joined)")
        except:
            pass

# ----------------------------
# Commands
# ----------------------------
@bot.message_handler(commands=['start'])
def start_command_handler(message):
    if not require_join_or_gate(message):
        log(f"{bot_username} log:\n\nuser: {message.chat.id}\n\nstart blocked (not joined)")
        return

    bot.send_message(message.chat.id, start_msg, parse_mode="HTML", disable_web_page_preview=True)
    log(f"{bot_username} log:\n\nuser: {message.chat.id}\n\nstart command")

@bot.message_handler(commands=['help'])
def help_command_handler(message):
    bot.send_message(message.chat.id, help_msg, parse_mode="HTML", disable_web_page_preview=True)
    log(f"{bot_username} log:\n\nuser: {message.chat.id}\n\nhelp command")

@bot.message_handler(commands=['privacy'])
def privacy_message_handler(message):
    bot.send_message(message.chat.id, privacy_msg, parse_mode="HTML", disable_web_page_preview=True)
    log(f"{bot_username} log:\n\nuser: {message.chat.id}\n\nprivacy command")

@bot.message_handler(commands=['lystaria_bot'])
def lystaria_message_handler(message):
    bot.send_message(message.chat.id, lystaria_msg, parse_mode="HTML", disable_web_page_preview=True)
    log(f"{bot_username} log:\n\nuser: {message.chat.id}\n\nlystaria command")

# ----------------------------
# Link handlers
# ----------------------------
@bot.message_handler(regexp=spotify_link_reg)
def spotify_link_handler(message):
    bot.send_message(
        message.chat.id,
        "This bot only supports Instagram links. Please send an Instagram post link.\n\n"
        "If you want to download from Spotify you can check out my other bot: @SpotSeekBot"
    )

@bot.message_handler(regexp=insta_post_or_reel_reg)
def post_or_reel_link_handler(message):
    # Gate check MUST be first to prevent bypass
    if not require_join_or_gate(message):
        log(f"{bot_username} log:\n\nuser: {message.chat.id}\n\nlink blocked (not joined)")
        return

    guide_msg_1 = None

    try:
        log(f"{bot_username} log:\n\nuser:\n{message.chat.id}\n\n✅ message text:\n{message.text}")
        guide_msg_1 = bot.send_message(message.chat.id, "Ok wait a few moments...")

        post_shortcode = get_post_or_reel_shortcode_from_link(message.text)
        print(post_shortcode)

        if not post_shortcode:
            log(f"{bot_username} log:\n\nuser: {message.chat.id}\n\n🛑 error in getting post_shortcode")
            try_to_delete_message(message.chat.id, guide_msg_1.message_id)
            return

        media_links, caption = get_instagram_media_links(post_shortcode)

        # If both empty, treat as failure
        if (not media_links) and (not caption):
            raise Exception("riad_azz returned nothing")

        # Caption handling
        if caption is None:
            caption = ''
        while len(caption) + len(caption_trail) > 1024:
            caption = caption[:-1]
        caption = caption + caption_trail

        media_list = []
        for idx, item in enumerate(media_links):
            if item.get('type') == 'video':
                if idx == 0:
                    media = telebot.types.InputMediaVideo(item['url'], caption=caption)
                else:
                    media = telebot.types.InputMediaVideo(item['url'])
            else:
                if idx == 0:
                    media = telebot.types.InputMediaPhoto(item['url'], caption=caption)
                else:
                    media = telebot.types.InputMediaPhoto(item['url'])
            media_list.append(media)

        def chunk_list(lst, n):
            for i in range(0, len(lst), n):
                yield lst[i:i + n]

        if len(media_list) == 1:
            media = media_list[0]
            if isinstance(media, telebot.types.InputMediaPhoto):
                bot.send_photo(message.chat.id, media.media, caption=media.caption)
            else:
                bot.send_video(message.chat.id, media.media, caption=media.caption)
        else:
            for chunk in chunk_list(media_list, 10):
                bot.send_media_group(message.chat.id, chunk)

        bot.send_message(message.chat.id, end_msg, parse_mode="HTML", disable_web_page_preview=True)

        if guide_msg_1:
            try_to_delete_message(message.chat.id, guide_msg_1.message_id)

        return

    except Exception as e:
        try:
            if guide_msg_1:
                try_to_delete_message(message.chat.id, guide_msg_1.message_id)
        except:
            pass

        log(f"{bot_username} log:\n\nuser: {message.chat.id}\n\n🛑 error in main body: {str(e)}")
        bot.send_message(message.chat.id, fail_msg, parse_mode="HTML", disable_web_page_preview=True)

# ----------------------------
# Fallback handler
# ----------------------------
@bot.message_handler(func=lambda message: True)
def wrong_pattern_handler(message):
    log(f"{bot_username} log:\n\nuser: {message.chat.id}\n\n❌wrong pattern: {message.text}")
    bot.send_message(message.chat.id, wrong_pattern_msg, parse_mode="HTML", disable_web_page_preview=True)