import os
from dotenv import load_dotenv

import instaloader
from instaloader import *

import re
import requests
import traceback # to print error traceback
import telebot

import json
import urllib.parse

# we use dotenv to use os.getenv() instead of os.environ[]
# and read from '.env' in current folder instead of '/etc/environment'
# more guide:
# https://dev.to/jakewitcher/using-env-files-for-environment-variables-in-python-applications-55a1
load_dotenv(override=False)

# env variables
bot_token = (os.getenv("BEST_INSTAGRAM_DOWNLOADER_BOT_API") or "").strip()
if not bot_token:
    raise RuntimeError("Missing BEST_INSTAGRAM_DOWNLOADER_BOT_API env var")

log_channel_id_raw = (os.getenv("INSTAGRAM_DOWNLOADER_LOG_CHANNEL_ID") or "").strip()
log_channel_id = int(log_channel_id_raw) if log_channel_id_raw.lstrip("-").isdigit() else None

# initialize bot
bot = telebot.TeleBot(bot_token, parse_mode="HTML")

# settings
bot_username = "@quick_instagram_bot"
caption_trail = "\n\n\n" + bot_username
session_file_name = "session" # any name change should apply to .gitignore too

# warp socks proxy
warp_proxies_raw = os.environ.get("WARP_PROXIES", "[]").strip()
warp_proxies = json.loads(warp_proxies_raw or "[]")

# regex
insta_post_or_reel_reg = r'(?:https?://www\.)?instagram\.com\S*?/(p|reel)/([a-zA-Z0-9_-]{11})/?'
spotify_link_reg = r'(?:https?://)?open\.spotify\.com/(track|album|playlist|artist)/[a-zA-Z0-9]+'

# messages
start_msg = '''Send an instagram link to download.

It can be a post link like this:
https://www.instagram.com/p/DFx\_jLuACs3

Or it can be a reel link like this:
https://www.instagram.com/reel/C59DWpvOpgF'''

help_msg = '''<b>Instagram Downloader -- Help</b>

This is a link-based Instagram downloader. Send an Instagram post link and the bot will fetch the media and return it here as downloadable files.

<b>What it’s for</b>
- Saving images from Instagram posts without screenshots
- Grabbing carousel photos in a clean, original-quality format (when available)

<b>How it works</b>
1. Copy the link to an Instagram post
2. Paste the link into chat with this bot
3. The bot downloads the media and sends it back as files

<b>Supported right now</b>
- Public Instagram posts
- Photo posts and carousel images

<b>Private links</b>
Private links may work only if the bot’s current session has access to view the post. If it cannot access the content, the request will fail.

<b>Limits and expectations</b>
- Some posts may fail due to Instagram restrictions or rate limits
- If it fails, try again later or send a different link
- This bot does not claim video support in its current version

<b>Support</b>
If you run into issues or have questions, contact @asteriasmoons

You can share the bot to show the love!'''

privacy_msg = '''<b>Privacy</b>

This bot does not collect, store, or share any personal user data.

Links you send are used only to fetch the requested media and are not saved after processing.'''

end_msg = '''If you like the bot you can support me by giving a star <a href="https://github.com/asteriasmoons/instagram-downloader">here</a> ☆ (it's free)

You can also check out my other bot too: @lystaria_bot for more info use /lystaria'''

fail_msg = '''Sorry, my process wasn't successful. But you can try again another time or with another link.'''

wrong_pattern_msg = '''Wrong pattern.
You should send an instagram post or reel link.'''

reel_msg = '''Reel links are not supported at the moment. You can send post links instead.'''

lystaria_msg = '''<b>Lystaria Bot</b>
Hello! Thank you for being interested in my first project for Telegram. I built this bot for an entirely different use case and in an entirely different language.. so what is it?

Lystaria @lystaria_bot is a multi-management bot for many different things but overall its a productivity bot.
- Reminders (once/recurring)
- Events (once/recurring)
- Share/Join Events
- User Settings
- Calendar View (list style)
- Journal (with tag filter page)
- Prompts for your journal
- Reading Streaks Counter
- Add books with tbr, reading, etc.
- Generate Book Summaries
- Mini App or Command Driven!

I created this bot for my own personal use. I adore Telegram and its interface and design and the way bots function inside of it. Much like discord does but better and I knew immediately what my use case would be.. 

I NEEDED this bot for myself but I also wanted to see others benefit from it as well. I paid $15 to advertise it and got 35 subscribers on day two and a 4.2/5 star rating on day three with roughly 50 votes. It has been such a wonderful experience and I am always looking to refine the features for it. Try it out if you like, just click the bots username above!'''
