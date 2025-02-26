import os
import random
import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Set up logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Load environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN is missing! Set it in environment variables.")

# URLs for shloka text files and audio
HINDI_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20with%20Uvacha.txt"
ENGLISH_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/BG%20English%20with%20Uvacha.txt"
HINDI_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20without%20Uvacha.txt"
TELUGU_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20Without%20Uvacha.txt"
ENGLISH_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/BG%20English%20without%20Uvacha.txt"
AUDIO_FULL_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioFull/"

# Session data to track user progress
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

# Load shlokas
full_shlokas_hindi = load_shlokas_from_github(HINDI_WITH_UVACHA_URL)
full_shlokas_telugu = load_shlokas_from_github(TELUGU_WITH_UVACHA_URL)
full_shlokas_english = load_shlokas_from_github(ENGLISH_WITH_UVACHA_URL)
shlokas_hindi = load_shlokas_from_github(HINDI_WITHOUT_UVACHA_URL)
shlokas_telugu = load_shlokas_from_github(TELUGU_WITHOUT_UVACHA_URL)
shlokas_english = load_shlokas_from_github(ENGLISH_WITHOUT_UVACHA_URL)

# Function to get a specific shloka by chapter and verse index
def get_shloka(chapter: str, verse_idx: int, with_audio: bool = False, audio_only: bool = False):
    chapter = str(chapter)
    if chapter not in full_shlokas_hindi or verse_idx >= len(full_shlokas_hindi[chapter]):
        return None, None
    verse, shloka_hindi = full_shlokas_hindi[chapter][verse_idx]
    _, shloka_telugu = full_shlokas_telugu[chapter][verse_idx]
    _, shloka_english = full_shlokas_english[chapter][verse_idx]
    audio_file_name = f"{chapter}.{verse}.mp3"
    audio_link = f"{AUDIO_FULL_URL}{audio_file_name}" if with_audio else None
    text = f"{chapter}.{verse}\nTelugu:\n{shloka_telugu}\n\nHindi:\n{shloka_hindi}\n\nEnglish:\n{shloka_english}" if not audio_only else None
    return text, audio_link

# Function to get a random shloka
def get_random_shloka(chapter: str, user_id: int, with_audio: bool = False, audio_only: bool = False):
    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": {}, "last_chapter": None, "last_index": None}
    chapter = str(chapter).strip()
    if chapter == "0":
        chapter = random.choice(list(full_shlokas_hindi.keys()))
    if chapter not in full_shlokas_hindi:
        return "❌ Invalid chapter number. Please enter a number between 0-18.", None
    if chapter not in session_data[user_id]["used_shlokas"]:
        session_data[user_id]["used_shlokas"][chapter] = set()
    available_shlokas = [i for i in range(len(full_shlokas_hindi[chapter])) if i not in session_data[user_id]["used_shlokas"][chapter]]
    if not available_shlokas:
        return f"✅ All shlokas from chapter {chapter} have been shown! Try another chapter or /reset.", None
    shloka_index = random.choice(available_shlokas)
    session_data[user_id]["used_shlokas"][chapter].add(shloka_index)
    session_data[user_id]["last_chapter"] = chapter
    session_data[user_id]["last_index"] = shloka_index
    verse, shloka_hindi = full_shlokas_hindi[chapter][shloka_index]
    _, shloka_telugu = full_shlokas_telugu[chapter][shloka_index]
    _, shloka_english = full_shlokas_english[chapter][shloka_index]
    audio_file_name = f"{chapter}.{verse}.mp3"
    audio_link = f"{AUDIO_FULL_URL}{audio_file_name}" if with_audio else None
    text = f"{chapter}.{verse}\nTelugu:\n{shloka_telugu}\n\nHindi:\n{shloka_hindi}\n\nEnglish:\n{shloka_english}" if not audio_only else None
    return text, audio_link

# Function to get a specific shloka by chapter and verse number
def get_specific_shloka(chapter: str, verse: str, user_id: int, with_audio: bool = False, audio_only: bool = False):
    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": {}, "last_chapter": None, "last_index": None}
    chapter = str(chapter)
    verse = str(verse)
    if chapter not in full_shlokas_hindi:
        return "❌ Invalid chapter number. Please enter a number between 0-18.", None
    for idx, (v, _) in enumerate(full_shlokas_hindi[chapter]):
        if v == verse:
            verse_text, shloka_hindi = full_shlokas_hindi[chapter][idx]
            _, shloka_telugu = full_shlokas_telugu[chapter][idx]
            _, shloka_english = full_shlokas_english[chapter][idx]
            audio_file_name = f"{chapter}.{verse}.mp3"
            audio_link = f"{AUDIO_FULL_URL}{audio_file_name}" if with_audio else None
            session_data[user_id]["last_chapter"] = chapter
            session_data[user_id]["last_index"] = idx
            text = f"{chapter}.{verse}\nTelugu:\n{shloka_telugu}\n\nHindi:\n{shloka_hindi}\n\nEnglish:\n{shloka_english}" if not audio_only else None
            return text, audio_link
    return f"❌ Shloka {chapter}.{verse} not found!", None

# Function to get the last shloka
def get_last_shloka(user_id: int, with_audio: bool = False, audio_only: bool = False):
    if user_id in session_data and session_data[user_id]["last_index"] is not None:
        chapter = session_data[user_id]["last_chapter"]
        shloka_index = session_data[user_id]["last_index"]
        verse, shloka_hindi = full_shlokas_hindi[chapter][shloka_index]
        _, shloka_telugu = full_shlokas_telugu[chapter][shloka_index]
        _, shloka_english = full_shlokas_english[chapter][shloka_index]
        audio_file_name = f"{chapter}.{verse}.mp3"
        audio_link = f"{AUDIO_FULL_URL}{audio_file_name}" if with_audio else None
        text = f"{chapter}.{verse}\nTelugu:\n{shloka_telugu}\n\nHindi:\n{shloka_hindi}\n\nEnglish:\n{shloka_english}" if not audio_only else None
        return text, audio_link
    return "❌ No previous shloka found. Please request one first!", None

# Handle incoming messages
async def handle_message(update: Update, context: CallbackContext):
    user_text = update.message.text.strip().lower()
    user_id = update.message.from_user.id
    
    # Check for audio modifiers
    with_audio = user_text.endswith("a")
    audio_only = user_text.endswith("o")
    if audio_only:
        user_text = user_text[:-1]
    if with_audio:
        user_text = user_text[:-1]
    
    # Handle specific verse request (e.g., 18.1)
    if "." in user_text:
        try:
            chapter, verse = user_text.split(".", 1)
            if chapter.isdigit() and verse.isdigit():
                response, audio_url = get_specific_shloka(chapter, verse, user_id, with_audio, audio_only)
                if response:
                    await update.message.reply_text(response)
                if audio_url:
                    await update.message.reply_audio(audio_url)
                return
        except ValueError:
            pass
    
    # Handle chapter number or commands
    if user_text.isdigit():
        response, audio_url = get_random_shloka(user_text, user_id, with_audio, audio_only)
        if response:
            await update.message.reply_text(response)
        if audio_url:
            await update.message.reply_audio(audio_url)
    elif user_text == "f":
        response, audio_url = get_last_shloka(user_id, with_audio, audio_only)
        if response:
            await update.message.reply_text(response)
        if audio_url:
            await update.message.reply_audio(audio_url)
    elif user_text == "n":
        if user_id in session_data and session_data[user_id]["last_index"] is not None:
            chapter = session_data[user_id]["last_chapter"]
            next_idx = session_data[user_id]["last_index"] + 1
            response, audio_url = get_shloka(chapter, next_idx, with_audio, audio_only)
            if response:
                session_data[user_id]["last_index"] = next_idx
                await update.message.reply_text(response)
                if audio_url:
                    await update.message.reply_audio(audio_url)
            else:
                await update.message.reply_text("❌ No next shloka available!")
        else:
            await update.message.reply_text("❌ Please request a shloka first!")
    elif user_text == "p":
        if user_id in session_data and session_data[user_id]["last_index"] is not None:
            chapter = session_data[user_id]["last_chapter"]
            prev_idx = max(0, session_data[user_id]["last_index"] - 1)
            response, audio_url = get_shloka(chapter, prev_idx, with_audio, audio_only)
            if response:
                session_data[user_id]["last_index"] = prev_idx
                await update.message.reply_text(response)
                if audio_url:
                    await update.message.reply_audio(audio_url)
            else:
                await update.message.reply_text("❌ No previous shloka available!")
        else:
            await update.message.reply_text("❌ Please request a shloka first!")
    else:
        await update.message.reply_text(
            "❌ Invalid input. Please use:\n"
            "0-18: Random shloka from chapter\n"
            "chapter.verse: Specific shloka (e.g., 18.1)\n"
            "f: Last full shloka\n"
            "n: Next shloka\n"
            "p: Previous shloka\n"
            "Add 'a' for audio (e.g., '18a', '18.1a')\n"
            "Add 'o' for audio only (e.g., '18o', '18.1o')\n"
            "Use /reset to start fresh"
        )

# Start command
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Jai Gurudatta!\n"
        "Welcome to Srimad Bhagavadgita Random Practice chatbot.\n"
        "0-18 → Random shloka from chapter\n"
        "chapter.verse → Specific shloka (e.g., 18.1)\n"
        "f → Full last shloka\n"
        "n → Next shloka\n"
        "p → Previous shloka\n"
        "Add 'a' for audio\n"
        "Add 'o' for audio only\n"
        "Use /reset to start fresh"
    )

# Reset command
async def reset(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in session_data:
        del session_data[user_id]
    await update.message.reply_text("✅ Session reset! Start anew with any chapter.")

# Main function to run the bot
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_webhook(listen="0.0.0.0", port=int(os.getenv("PORT", 5000)), webhook_url=WEBHOOK_URL)

if __name__ == "__main__":
    main()
