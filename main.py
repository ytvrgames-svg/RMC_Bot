import os
import wave
import asyncio
import tempfile
import threading
from queue import Queue
import logging
import audioop
import requests
from TikTokLive import TikTokLiveClient
import json
import yt_dlp as youtube_dl
import discord
from TikTokLive.events import ConnectEvent, LiveEndEvent
from discord import app_commands, FFmpegPCMAudio
from discord.ext import tasks
from discord.ext import commands, voice_recv
import sys
import traceback
from dotenv import load_dotenv
from gtts import gTTS
import whisper
from langdetect import detect, DetectorFactory
import google.generativeai as genai
import feedparser  # YouTube RSS

# ----------------------
# Opus betöltés (voice)
# opus_path = os.path.join(os.path.dirname(os.path.abspath(__file__)), "opus.dll")
# discord.opus.load_opus(opus_path)
# print("Opus betöltve:", discord.opus.is_loaded())

# DetectorFactory.seed = 0
# logging.getLogger("discord.ext.voice_recv.reader").setLevel(logging.WARNING)



# ----------------------
# ENV
load_dotenv()
TOKEN = os.getenv("DISCORD_TOKEN")
GUILD_ID = 957684316341670018
TIKTOK_USERNAME = os.getenv("TIKTOK_USERNAME")
ANNOUNCE_CHANNEL_ID = int(os.getenv("ANNOUNCE_CHANNEL_ID"))
guild_obj = discord.Object(id=GUILD_ID)
# YOUTUBE_CHANNEL_RSS = "https://www.youtube.com/@reflectmindchannel6214/videos"

tiktok_client = TikTokLiveClient(unique_id=TIKTOK_USERNAME)

is_live = False  # spam védelem
live_announced = False

# ----------------------
# Bot inicializálás
intents = discord.Intents.default()
intents.message_content = True
intents.voice_states = True
intents.members = True
intents.members = True
intents.dm_messages = True
bot = commands.Bot(command_prefix="!", intents=intents)

@bot.event
async def on_ready():
    for guild in bot.guilds:
        try:
            await guild.me.edit(nick="RMC")
        except:
            pass

# ----------------------
try:
    bot.run(TOKEN)
except Exception:
    traceback.print_exc()
    sys.exit(1)

# Gemini AI
# API_KEYS = [os.getenv("GEMINI_API_KEY"), os.getenv("GEMINI_API_KEY_2")]
# API_KEYS = [k for k in API_KEYS if k]
# current_key_index = 0
# model = None

# def configure_gemini():
#     global model
#     if not API_KEYS:
#         model = None
#         return
#     genai.configure(api_key=API_KEYS[current_key_index])
#     model = genai.GenerativeModel("gemini-flash-latest")
#     print(f"Gemini modell beállítva (Kulcs index: {current_key_index})")

# configure_gemini()

# def generate_content_safe(text, style_samples=None):
#     global current_key_index
#     if not model:
#         raise Exception("Nincs beállítva Gemini modell.")

#     prompt = text
#     if style_samples:
#         prompt = "Írj úgy, mint a barátom a következő példák alapján:\n"
#         for s in style_samples:
#             prompt += f"- {s}\n"
#         prompt += f"\nKérdés: {text}\nVálasz:"

#     for _ in range(len(API_KEYS)):
#         try:
#             return model.generate_content(prompt)
#         except Exception as e:
#             if "429" in str(e):
#                 current_key_index = (current_key_index + 1) % len(API_KEYS)
#                 configure_gemini()
#                 continue
#             else:
#                 raise e
#     raise Exception("Minden API kulcs kvótája elfogyott.")

# ----------------------
# Whisper
# whisper_model = whisper.load_model("medium")

# ----------------------
# Nyelv detektálás
# def detect_lang(text: str):
#     try:
#         lang = detect(text)
#         return "HU" if lang == "hu" else "EN"
#     except:
#         return "EN"

# ----------------------
# Bot memória
# MEMORY_FILE = "user_memory.json"
# try:
#     with open(MEMORY_FILE, "r", encoding="utf-8") as f:
#         user_memory = json.load(f)
# except:
#     user_memory = {}

# def save_memory():
#     with open(MEMORY_FILE, "w", encoding="utf-8") as f:
#         json.dump(user_memory, f, ensure_ascii=False, indent=2)

# ----------------------
# Stílus példák a barátodtól
# sample_texts = [
#     "Sziasztok Srácok 🤜🤛@everyone. Nos megnéztem Csabi barátom ajánlásával ezt a gamet ami nagyon durván agyfasz volt XD. Gyertek és nézzétek meg milyen is ez a játék.",
#     "Sziasztok Srácok😎 @everyone Elkezdtük a 2026os évet. A Tervünk az hogy ebben a seasonbe legalább a silvert elérjük.Gyertek és nézzétek meg milyen skillesek leszünk.",
#     "Sziasztok Srácok 😎 @everyone A mai nap folytatjuk a Tomb Raider Franchise Végigjátszást az 1. résszel. Innentől fogva csak VOD formájában fogjátok megkapni a tartalmat 🙂A Játék Lara Croft kalandjait követi, aki egy kalandor és régész is egyben. A történet központjában egy titokzatos, és ősi ereklye, a SCION áll, amit Lara megpróbál megszerezni, miközben érdekes és veszélyes helyszíneken kell átvágnia magát.",
#     "Sziasztok Srácok😎 @everyone Folytatjuk a Free 3 horror games sorozatommat a 2. szezonnal ahol újabb 3 Horror Demót fogunk megnézni igy Csütörtök este. Viszont innentől fogva streamben fogjuk végignézni ezeket.Gyertek és nézzük meg együtt milyenek is lesznek ezek a játékok.",
#     "Sziasztok Srácok😎 @everyone Idén még elkezdem nektek játszani a GeoGuessrt, amit majd jövőre is folytatni fogok. Gyertek be és segitsetek nekem mert ebben a játékban még nagyon kezdő vagyok XD."
# ]

# ----------------------
class MyClient(discord.Client):
    def __init__(self):
        intents = discord.Intents.default()
        intents.message_content = True
        intents.voice_states = True
        intents.members = True
        super().__init__(intents=intents)

        self.tree = app_commands.CommandTree(self)
        self.vc = {}  # guild_id -> VoiceClient
        self.listen_threads = {}  # guild_id -> threading.Thread
        self.audio_queues = {}  # guild_id -> Queue

    async def setup_hook(self):
        self.tree.clear_commands(guild=None)
        await self.tree.sync()
        await self.tree.sync(guild=guild_obj)
        print("Slash parancsok szinkronizálva")

client = MyClient()

# ----------------------
# TTS lejátszás voice-ban
# async def speak_in_voice(guild_id: int, text: str, lang: str = "hu"):
#     vc = client.vc.get(guild_id)
#     if not vc or not vc.is_connected():
#         return

#     with tempfile.NamedTemporaryFile(delete=False, suffix=".mp3") as f:
#         tts = gTTS(text=text, lang="hu" if lang=="HU" else "en")
#         tts.save(f.name)
#         path = f.name

#     source = FFmpegPCMAudio(path)
#     vc.play(source)
#     while vc.is_playing():
#         await asyncio.sleep(0.2)
#     os.remove(path)

# ----------------------
# Voice hallgatás
# def start_listening(vc: discord.VoiceClient, guild_id: int):
#     audio_queue = Queue()
#     client.audio_queues[guild_id] = audio_queue

#     class DummySink(voice_recv.AudioSink):
#         def wants_opus(self):
#             return False
#         def write(self, user, data):
#             if vc.is_playing():
#                 rms = audioop.rms(data.pcm, 2)
#                 if rms > 2500:
#                     vc.stop()
#             audio_queue.put(data.pcm)
#         def cleanup(self):
#             pass

#     sink = DummySink()
#     vc.listen(sink)

#     async def loop():
#         buffer = bytearray()
#         while vc.is_connected():
#             while not audio_queue.empty():
#                 buffer.extend(audio_queue.get())
#             if len(buffer) >= 300000:
#                 with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:
#                     f_path = f.name
#                 with wave.open(f_path, 'wb') as wf:
#                     wf.setnchannels(2)
#                     wf.setsampwidth(2)
#                     wf.setframerate(48000)
#                     wf.writeframes(buffer)
#                 buffer.clear()
#                 try:
#                     def process_blocking(path):
#                         result = whisper_model.transcribe(path, fp16=False, language="hu")
#                         text = result['text'].strip()
#                         if not text:
#                             return None, None
#                         lang = detect_lang(text)
#                         response = generate_content_safe(text)
#                         return response.text, lang
#                     ai_text, lang = await asyncio.to_thread(process_blocking, f_path)
#                     if ai_text:
#                         await speak_in_voice(guild_id, ai_text, lang=lang)
#                 except Exception as e:
#                     print("Voice AI hiba:", e)
#                 finally:
#                     os.remove(f_path)
#             else:
#                 await asyncio.sleep(0.1)
#     asyncio.run_coroutine_threadsafe(loop(), client.loop)

# ----------------------
# /join
# @client.tree.command(name="join", description="Csatlakozik a hangcsatornára", guild=guild_obj)
# async def join(interaction: discord.Interaction):
#     await interaction.response.defer(ephemeral=True)
#     if not interaction.user.voice:
#         await interaction.followup.send("Nem vagy hangcsatornában.")
#         return
#     channel = interaction.user.voice.channel
#     vc = interaction.guild.voice_client
#     if vc and vc.is_connected():
#         if vc.channel.id == channel.id:
#             await interaction.followup.send("Már bent vagyok.")
#             return
#         await vc.disconnect()
#     vc = await channel.connect(cls=voice_recv.VoiceRecvClient)
#     client.vc[interaction.guild.id] = vc
#     t = threading.Thread(target=start_listening, args=(vc, interaction.guild.id), daemon=True)
#     t.start()
#     client.listen_threads[interaction.guild.id] = t
#     await interaction.followup.send(f"Csatlakoztam: **{channel}**", ephemeral=True)

# ----------------------
# /leave
# @client.tree.command(name="leave", description="Kilép a hangcsatornából", guild=guild_obj)
# async def leave(interaction: discord.Interaction):
#     vc = interaction.guild.voice_client
#     if not vc or not vc.is_connected():
#         await interaction.response.send_message("Nem vagyok hangcsatornában.", ephemeral=True)
#         return
#     channel = vc.channel
#     await vc.disconnect()
#     client.vc.pop(interaction.guild.id, None)
#     await interaction.response.send_message(f"Kiléptem: **{channel}**", ephemeral=True)

# ----------------------
# Rang parancsok
# @client.tree.command(name="add_rank", description="Rangot ad az adott felhasználónak", guild=guild_obj)
# async def add_rank(interaction: discord.Interaction, user: discord.Member, rang: str):
#     await interaction.response.defer(ephemeral=True)
#     if interaction.user.guild_permissions.administrator:
#         role = discord.utils.get(interaction.guild.roles, name=rang)
#         if role:
#             try:
#                 await user.add_roles(role)
#                 await interaction.followup.send(f"Sikeresen hozzáadva: **{role.name}** -> {user.mention}", ephemeral=True)
#             except: await interaction.followup.send("Hiba a rang hozzáadásnál", ephemeral=True)
#         else: await interaction.followup.send("Nem található ilyen rang", ephemeral=True)
#     else: await interaction.followup.send("Nincs admin jogosultságod.", ephemeral=True)

# @client.tree.command(name="remove_rank", description="Eltávolítja a rangot", guild=guild_obj)
# async def remove_rank(interaction: discord.Interaction, user: discord.Member, rang: str):
#     await interaction.response.defer(ephemeral=True)
#     if interaction.user.guild_permissions.administrator:
#         role = discord.utils.get(interaction.guild.roles, name=rang)
#         if role:
#             try:
#                 await user.remove_roles(role)
#                 await interaction.followup.send(f"Sikeresen eltávolítva: **{role.name}** -> {user.mention}", ephemeral=True)
#             except: await interaction.followup.send("Hiba a rang eltávolításnál", ephemeral=True)
#         else: await interaction.followup.send("Nem található ilyen rang", ephemeral=True)
#     else: await interaction.followup.send("Nincs admin jogosultságod.", ephemeral=True)

# ----------------------
# DM AI esemény
# @client.event
# async def on_message(message):
#     if message.author.bot:
#         return
#     content = message.content.lower().strip()
#     if message.guild is None:
#         user_id = str(message.author.id)
#
#         # Memória törlés
#         if content in ["/delete", "/erase", "/reset"]:
#             try: await message.delete()
#             except: pass
#             user_memory.pop(user_id, None)
#             save_memory()
#             await message.channel.send("🧠 Memóriád törölve lett.")
#             return
#
#         # AI válasz stílusban
#         prev_memory = user_memory.get(user_id, "")
#         prompt_text = prev_memory + "\nUser: " + message.content
#         try:
#             response = generate_content_safe(prompt_text, style_samples=sample_texts)
#             await message.channel.send(response.text)
#             user_memory[user_id] = prompt_text + "\nBot: " + response.text
#             save_memory()
#         except Exception as e:
#             print("AI hiba:", e)
#             await message.channel.send("Most nem tudok válaszolni 😕")

# ----------------------
# YouTube videó figyelés
# last_video_id = None
# @tasks.loop(minutes=5)
# async def check_new_video():
#     global last_video_id
#     feed = feedparser.parse(YOUTUBE_CHANNEL_RSS)
#     if feed.entries:
#         latest = feed.entries[0]
#         video_id = latest.yt_videoid
#         if video_id != last_video_id:
#             last_video_id = video_id
#             guild = client.get_guild(GUILD_ID)
#             if guild:
#                 channel = discord.utils.get(guild.text_channels, name="general")
#                 if channel:
#                     await channel.send(f"📢 Új videó: {latest.title}\n{latest.link}")

@client.event
async def on_ready():
    print(f"Bejelentkezve mint {client.user}")
    await client.tree.sync()
    # check_new_video.start()
    tiktok_live_check.start()

# ----------------------
# @client.tree.command(
#     name="test_video",
#     description="Teszt videó értesítés AI-leírással",
#     guild=discord.Object(id=GUILD_ID)
# )
# async def test_video(interaction: discord.Interaction, url: str):
#     await interaction.response.defer(thinking=True)
#     try:
#         # YouTube cím lekérése
#         ydl_opts = {'quiet': True, 'skip_download': True}
#         with youtube_dl.YoutubeDL(ydl_opts) as ydl:
#             info = ydl.extract_info(url, download=False)
#             title = info.get('title', 'Új videó')
#             description = info.get('description', '')
#
#         # AI prompt összeállítása
#         formatted_samples = "\n".join([f"- {s}" for s in sample_texts])
#         prompt = (
#             f"Te vagy a videós, aki ezeket a példákat írta. Írj egy új Discord bejelentést a legújabb videódhoz ugyanebben a stílusban.\n"
#             f"Használd a 'Sziasztok Srácok' beköszönést, emojikat és az @everyone taget.\n"
#             f"Ne spoilerezd le a videót, csak egy általános bemutatót írj.\n"
#             f"Példák a stílusodra:\n{formatted_samples}\n\n"
#             f"Az új videó adatai:\n"
#             f"Cím: {title}\n"
#             f"Leírás: {str(description)[:500]}\n"
#             f"Link: {url}\n\n"
#             f"A bejelentés szövege:"
#         )
#
#         # AI válasz
#         response = generate_content_safe(prompt)
#         text = response.text
#
#         # Chatbe küldés
#         await interaction.followup.send(f"🎬 Új videó feltöltve! Nézd meg: {url}\n\n{text}")
#
#     except Exception as e:
#         print("AI hiba videóhoz:", e)
#         await interaction.followup.send("Hiba történt a videó leírás generálásánál 😕")

# ----------------------
# ---- TIKTOK LIVE CHECK ----
def is_tiktok_live(username: str) -> bool:
    url = f"https://www.tiktok.com/@{username}/live"
    headers = {"User-Agent": "Mozilla/5.0"}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        return r.status_code == 200 and "isLiveBroadcast" in r.text
    except:
        return False

# ----------------------
# ---- LOOP ----
@tasks.loop(seconds=60)
async def tiktok_live_check():
    global live_announced
    channel = client.get_channel(ANNOUNCE_CHANNEL_ID)
    if not channel:
        return

    live = is_tiktok_live(TIKTOK_USERNAME)

    if live and not live_announced:
        await channel.send(
            f"🔴 **LIVE MOST!**\n"
            f"@everyone gyertek be 👇\n"
            f"https://www.tiktok.com/@{TIKTOK_USERNAME}/live"
        )
        live_announced = True

    if not live:
        live_announced = False

# ----------------------

client.run(TOKEN)
