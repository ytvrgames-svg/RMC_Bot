import os
import discord
from discord.ext import tasks
from dotenv import load_dotenv
from TikTokApi import TikTokApi

# ----------------------
# Környezeti változók betöltése
load_dotenv()

TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = int(os.getenv("GUILD_ID"))
ANNOUNCE_CHANNEL_ID = int(os.getenv("ANNOUNCE_CHANNEL_ID"))
TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME")

if not TOKEN or not GUILD_ID or not ANNOUNCE_CHANNEL_ID or not TIKTOK_USERNAME:
    raise ValueError("Hiányzó környezeti változó! Ellenőrizd a .env fájlodat.")

# ----------------------
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
# Helper log függvény
def log_event(msg):
    print(msg)

# Dummy AI kérés (helyettesíthető a saját ask_ai függvényeddel)
async def ask_ai(user_text: str) -> str:
    return f"AI válasz: {user_text[::-1]}"  # csak példa, visszafordítja a szöveget

# ----------------------
# TikTok live check függvény
async def is_tiktok_live(username: str) -> bool:
    async with TikTokApi() as api:
        try:
            user = await api.user(username)
            return user.live_status
        except Exception as e:
            log_event(f"TikTok lekérés hiba: {e}")
            return False

# ----------------------
# TikTok live check loop
@tasks.loop(seconds=60)
async def tiktok_live_check():
    global live_announced, first_check

    channel = bot.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        guild = bot.get_guild(GUILD_ID)
        if guild:
            channel = guild.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        return

    try:
        live = await is_tiktok_live(TIKTOK_USERNAME)
    except Exception as e:
        log_event(f"Hiba a TikTok lekérés közben: {e}")
        return

    if first_check:
        live_announced = live
        first_check = False
        return

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

# ----------------------
bot.run(TOKEN)
