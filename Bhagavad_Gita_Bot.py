import os
import random
import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import speech_recognition as sr
from pydub import AudioSegment

# Configure logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token & Webhook URL
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN is missing! Set it in Railway's environment variables.")

# File URLs
HINDI_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20with%20Uvacha.txt"
HINDI_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20without%20Uvacha.txt"
TELUGU_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20Without%20Uvacha.txt"

AUDIO_QUARTER_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioQuarter/"
AUDIO_FULL_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioFull/"

# Session data to track shown shlokas
session_data = {}

# Function to load shlokas from GitHub
def load_shlokas_from_github(url):
    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f"⚠️ Error fetching data from {url} (Status Code: {response.status_code})")
        return {}

    shlokas = {}
    current_number = None
    current_text = []

    lines = response.text.split("\n")
    for line in lines:
        line = line.strip()
        if not line:
            continue
        parts = line.split("\t", 1)
        if len(parts) == 2:
            if current_number:
                chapter, verse = current_number.split(".")[:2]
                if chapter not in shlokas:
                    shlokas[chapter] = []
                shlokas[chapter].append((verse, "\n".join(current_text)))
            current_number = parts[0]
            current_text = [parts[1]]
        else:
            current_text.append(line)
    if current_number:
        chapter, verse = current_number.split(".")[:2]
        if chapter not in shlokas:
            shlokas[chapter] = []
        shlokas[chapter].append((verse, "\n".join(current_text)))
    return shlokas

# Load all shlokas
shlokas_hindi = load_shlokas_from_github(HINDI_WITHOUT_UVACHA_URL)
shlokas_telugu = load_shlokas_from_github(TELUGU_WITHOUT_UVACHA_URL)
full_shlokas_hindi = load_shlokas_from_github(HINDI_WITH_UVACHA_URL)
full_shlokas_telugu = load_shlokas_from_github(TELUGU_WITH_UVACHA_URL)

def get_shloka(chapter: str, verse_idx: int, with_audio: bool = False):
    chapter = str(chapter)
    if chapter not in full_shlokas_hindi or verse_idx >= len(full_shlokas_hindi[chapter]):
        return None, None
    verse, shloka_hindi = full_shlokas_hindi[chapter][verse_idx]
    _, shloka_telugu = full_shlokas_telugu[chapter][verse_idx]
    audio_file_name = f"{chapter}.{int(verse)}.mp3"
    audio_link = f"{AUDIO_FULL_URL}{audio_file_name}" if with_audio else None
    logger.info(f"Audio URL for get_shloka: {audio_link}")
    return f"{chapter}.{verse}\n{shloka_hindi}\n{shloka_telugu}", audio_link

def get_random_shloka(chapter: str, user_id: int, with_audio: bool = False):
    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": {}, "last_chapter": None, "last_index": None}
    chapter = str(chapter).strip()
    if chapter == "0":
        chapter = random.choice(list(shlokas_hindi.keys()))
    if chapter not in shlokas_hindi:
        return "❌ Invalid chapter number. Please enter a number between 0-18.", None
    if chapter not in session_data[user_id]["used_shlokas"]:
        session_data[user_id]["used_shlokas"][chapter] = set()
    available_shlokas = [i for i in range(len(shlokas_hindi[chapter])) if i not in session_data[user_id]["used_shlokas"][chapter]]
    logger.info(f"User {user_id}, Chapter {chapter}, Available: {len(available_shlokas)}, Used: {len(session_data[user_id]['used_shlokas'][chapter])}")
    if not available_shlokas:
        return f"✅ All shlokas from chapter {chapter} have been shown! Try another chapter or /reset.", None
    shloka_index = random.choice(available_shlokas)
    session_data[user_id]["used_shlokas"][chapter].add(shloka_index)
    session_data[user_id]["last_chapter"] = chapter
    session_data[user_id]["last_index"] = shloka_index
    verse, shloka_hindi = shlokas_hindi[chapter][shloka_index]
    _, shloka_telugu = shlokas_telugu[chapter][shloka_index]
    audio_file_name = f"{chapter}.{int(verse)}.mp3"
    audio_link = f"{AUDIO_QUARTER_URL}{audio_file_name}" if with_audio else None
    logger.info(f"Audio URL for get_random_shloka: {audio_link}")
    return f"{chapter}.{verse}\n{shloka_hindi}\n{shloka_telugu}", audio_link

def get_last_shloka(user_id: int, with_audio: bool = False):
    if user_id in session_data and session_data[user_id]["last_index"] is not None:
        chapter = session_data[user_id]["last_chapter"]
        shloka_index = session_data[user_id]["last_index"]
        verse, shloka_hindi = full_shlokas_hindi[chapter][shloka_index]
        _, shloka_telugu = full_shlokas_telugu[chapter][shloka_index]
        audio_file_name = f"{chapter}.{int(verse)}.mp3"
        audio_link = f"{AUDIO_FULL_URL}{audio_file_name}" if with_audio else None
        return f"{chapter}.{verse}\n{shloka_hindi}\n{shloka_telugu}", audio_link
    return "❌ No previous shloka found. Please request one first!", None

async def handle_message(update: Update, context: CallbackContext):
    user_text = update.message.text.strip().lower()
    user_id = update.message.from_user.id
    with_audio = user_text.endswith("a")
    if with_audio:
        user_text = user_text[:-1]
    if user_text.isdigit():
        response, audio_url = get_random_shloka(user_text, user_id, with_audio)
        await update.message.reply_text(response)
        if audio_url:
            await update.message.reply_audio(audio_url)
    elif user_text == "s":
        response, audio_url = get_last_shloka(user_id, with_audio)
        await update.message.reply_text(response)
        if audio_url:
            await update.message.reply_audio(audio_url)
    elif user_text == "n":
        if user_id in session_data and session_data[user_id]["last_index"] is not None:
            chapter = session_data[user_id]["last_chapter"]
            next_idx = session_data[user_id]["last_index"] + 1
            response, audio_url = get_shloka(chapter, next_idx, with_audio)
            if response:
                session_data[user_id]["last_index"] = next_idx
                await update.message.reply_text(response)
                if audio_url:
                    await update.message.reply_audio(audio_url)
            else:
                await update.message.reply_text("❌ No next shloka available!")
        else:
            await update.message.reply_text("❌ Please request a shloka first!")
    elif user_text in ["n2", "n3", "n4", "n5"]:
        if user_id not in session_data or session_data[user_id]["last_index"] is None:
            await update.message.reply_text("❌ Please request a shloka first!")
            return
        chapter = session_data[user_id]["last_chapter"]
        current_idx = session_data[user_id]["last_index"]
        count = int(user_text[1:])
        responses = []
        audio_urls = []
        for i in range(count):
            next_idx = current_idx + i + 1
            response, audio_url = get_shloka(chapter, next_idx, with_audio)
            if response:
                responses.append(response)
                if audio_url:
                    audio_urls.append(audio_url)
            else:
                break
        if responses:
            session_data[user_id]["last_index"] = current_idx + len(responses)
            for response in responses:
                await update.message.reply_text(response)
            for audio_url in audio_urls:
                await update.message.reply_audio(audio_url)
        else:
            await update.message.reply_text("❌ No more shlokas available!")
    elif user_text in ["p", "pa"]:
        if user_id not in session_data or session_data[user_id]["last_index"] is None:
            await update.message.reply_text("❌ Please request a shloka first!")
            return
        chapter = session_data[user_id]["last_chapter"]
        current_idx = session_data[user_id]["last_index"]
        start_idx = max(0, current_idx - 2)
        end_idx = min(len(full_shlokas_hindi[chapter]), current_idx + 3)
        for idx in range(start_idx, end_idx):
            response, audio_url = get_shloka(chapter, idx, with_audio)
            if response:
                await update.message.reply_text(response)
                if audio_url:
                    await update.message.reply_audio(audio_url)
    else:
        await update.message.reply_text(
            "❌ Invalid input. Please use:\n"
            "0-18: Random shloka\n"
            "s: Last full shloka\n"
            "n: Next shloka\n"
            "n2-n5: Multiple next shlokas\n"
            "p: Previous 2, current & next 2 shlokas\n"
            "Add 'a' for audio (e.g., '1a', 'na')\n"
            "Or send a voice message with your request!"
        )

async def handle_voice(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    voice = update.message.voice
    file_id = voice.file_id
    
    # Download the voice file
    file = await context.bot.get_file(file_id)
    voice_file_path = f"voice_{user_id}.ogg"
    await file.download_to_drive(voice_file_path)
    
    try:
        # Convert .ogg to .wav
        wav_file_path = f"voice_{user_id}.wav"
        audio = AudioSegment.from_ogg(voice_file_path)
        audio.export(wav_file_path, format="wav")
        
        # Transcribe the audio
        recognizer = sr.Recognizer()
        with sr.AudioFile(wav_file_path) as source:
            audio_data = recognizer.record(source)
            try:
                text = recognizer.recognize_google(audio_data).strip().lower()
                logger.info(f"Transcribed voice message from user {user_id}: {text}")
                await update.message.reply_text(f"Recognized: {text}")
                
                # Process the transcribed text reusing handle_message logic
                context.user_data["text"] = text  # Temporarily store text
                await handle_message(update, context)  # Call existing handler
            except sr.UnknownValueError:
                await update.message.reply_text("❌ Sorry, I couldn’t understand the voice message. Please try again.")
            except sr.RequestError as e:
                await update.message.reply_text(f"❌ Error with speech recognition: {e}")
    except Exception as e:
        logger.error(f"Error processing voice message: {e}")
        await update.message.reply_text("❌ Error processing your voice message. Please try again.")
    finally:
        # Clean up temporary files
        if os.path.exists(voice_file_path):
            os.remove(voice_file_path)
        if os.path.exists(wav_file_path):
            os.remove(wav_file_path)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Jai Gurudatta!\n"
        "Welcome to Srimad Bhagavadgita Random Practice chatbot.\n"
        "0-18 → Random shloka from chapter\n"
        "0a-18a → With audio\n"
        "s → Full last shloka\n"
        "sa → Full last shloka with audio\n"
        "n → Next shloka\n"
        "na → Next with audio\n"
        "n2-n5 → Multiple next shlokas\n"
        "p → Previous 2, current & next 2\n"
        "pa → Same with audio\n"
        "Use /reset to start fresh\n"
        "Or send a voice message with your request!"
    )

async def reset(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in session_data:
        del session_data[user_id]
    await update.message.reply_text("✅ Session reset! Start anew with any chapter.")

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_handler(MessageHandler(filters.VOICE, handle_voice))  # Add voice message handler
    app.run_webhook(listen="0.0.0.0", port=int(os.getenv("PORT", 5000)), webhook_url=WEBHOOK_URL)

if __name__ == "__main__":
    main()
