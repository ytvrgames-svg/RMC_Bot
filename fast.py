import os
import requests
import discord
from discord.ext import tasks
from dotenv import load_dotenv

# ----------------------
# ENV betöltése
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
ANNOUNCE_CHANNEL_ID = int(os.getenv("ANNOUNCE_CHANNEL_ID"))
TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME")

# ----------------------
intents = discord.Intents.default()
intents.message_content = True
bot = discord.Client(intents=intents)

# ----------------------
live_announced = False

def is_tiktok_live(username: str) -> bool:
    """Ellenőrzi, hogy a TikTok user live-e."""
    url = f"https://www.tiktok.com/@{username}/live"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.status_code == 200 and "isLiveBroadcast" in r.text
    except:
        return False

# ----------------------
@tasks.loop(seconds=60)
async def tiktok_live_check():
    global live_announced
    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        return

    live = is_tiktok_live(TIKTOK_USERNAME)

    if live and not live_announced:
        await channel.send(
             f"🌟 Sziasztok! @everyone! 🌟\n"
            f"Gyere és csatlakozz hozzám, nézzük együtt a streamet! 💖🎉\n"
            f"👉 https://www.tiktok.com/@{TIKTOK_USERNAME}/live"
        )
        live_announced = True

    if not live:
        live_announced = False

# ----------------------
@bot.event
async def on_ready():
    print(f"Bejelentkezve mint {bot.user}")
    tiktok_live_check.start()

# ----------------------
bot.run(TOKEN)
