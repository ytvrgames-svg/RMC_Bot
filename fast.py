import os
import discord          # ← ez kell, különben NameError
from discord.ext import tasks
from dotenv import load_dotenv
import requests

# Bot setup
intents = discord.Intents.default()
intents.message_content = True
intents.dm_messages = True
bot = discord.Client(intents=intents)

# TikTok live állapot
live_announced = False
first_check = True

# AI engedélyezett user ID
ALLOWED_USER_ID = 769266438115950613

# ----------------------
# TikTok live check
@tasks.loop(seconds=60)
async def tiktok_live_check():
    global live_announced, first_check
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        return

    live = await is_tiktok_live(TIKTOK_USERNAME)

    # Első futás: csak állapot beállítása
    if first_check:
        live_announced = live
        first_check = False
        return

    if live and not live_announced:
        await channel.send(f"🌟 @everyone {TIKTOK_USERNAME} most LIVE! 👉 https://www.tiktok.com/@{TIKTOK_USERNAME}/live")
        live_announced = True

    if not live:
        live_announced = False

# ----------------------
# AI DM handling
@bot.event
async def on_message(message: discord.Message):
    if message.author.bot:
        return

    if message.author.id != ALLOWED_USER_ID:
        return

    if not isinstance(message.channel, discord.DMChannel):
        return

    user_text = message.content.strip()
    log_event(f"USER: {user_text}")
    ai_response = await ask_ai(user_text)
    await message.channel.send(ai_response)
    log_event(f"AI: {ai_response}")

# ----------------------
@bot.event
async def on_ready():
    print(f"Bejelentkezve mint {bot.user}")
    if not tiktok_live_check.is_running():
        tiktok_live_check.start()
