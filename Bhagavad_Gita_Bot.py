import os
import random
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext
import logging

# Enable logging
logging.basicConfig(level=logging.INFO)

# Bot Token & Webhook URL
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

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
        print(f"⚠️ Error fetching data from {url} (Status Code: {response.status_code})")
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

# Function to get a random shloka and corresponding audio
def get_random_shloka(chapter: str, user_id: int):
    global session_data

    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": set(), "last_shloka_index": None, "last_chapter": None}

    chapter = str(chapter).strip()

    if chapter == "0":
        chapter = random.choice(list(full_shlokas_hindi.keys()))
        shloka_source_hindi = full_shlokas_hindi
        shloka_source_telugu = full_shlokas_telugu
        audio_url = AUDIO_FULL_URL
    else:
        if chapter not in shlokas_hindi:
            return "❌ Invalid chapter number. Please enter a number between 0-18.", None

        shloka_source_hindi = shlokas_hindi
        shloka_source_telugu = shlokas_telugu
        audio_url = AUDIO_QUARTER_URL

    available_shlokas = [
        i for i in range(len(shloka_source_hindi[chapter]))
        if i not in session_data[user_id]["used_shlokas"]
    ]

    if not available_shlokas:
        return f"✅ All shlokas from chapter {chapter} have been shown in this session!", None

    shloka_index = random.choice(available_shlokas)
    session_data[user_id]["used_shlokas"].add(shloka_index)

    session_data[user_id]["last_shloka_index"] = shloka_index
    session_data[user_id]["last_chapter"] = chapter  

    verse, shloka_hindi = shloka_source_hindi[chapter][shloka_index]
    _, shloka_telugu = shloka_source_telugu[chapter][shloka_index]

    audio_file_name = f"{chapter}.{verse}.mp3"
    audio_link = f"{audio_url}{audio_file_name}"

    return f"{chapter}.{verse}\n{shloka_hindi}\n{shloka_telugu}", audio_link

# Function to get the last full shloka and corresponding audio
def get_last_shloka(user_id: int):
    if user_id in session_data and session_data[user_id]["last_shloka_index"] is not None:
        chapter = session_data[user_id]["last_chapter"]
        shloka_index = session_data[user_id]["last_shloka_index"]

        if chapter in full_shlokas_hindi and shloka_index < len(full_shlokas_hindi[chapter]):
            verse, shloka_hindi = full_shlokas_hindi[chapter][shloka_index]
            _, shloka_telugu = full_shlokas_telugu[chapter][shloka_index]

            audio_file_name = f"{chapter}.{verse}.mp3"
            audio_link = f"{AUDIO_FULL_URL}{audio_file_name}"

            return f"{chapter}.{verse}\n{shloka_hindi}\n{shloka_telugu}", audio_link
        else:
            return "❌ Error: Unable to find the last shloka. Please try again.", None

    return "❌ No previous shloka found. Please request one first!", None

# Message Handler
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_text = update.message.text.strip()
    user_id = update.message.from_user.id

    if user_text.isdigit():
        response, audio_url = get_random_shloka(user_text, user_id)
    elif user_text.lower() == "s":
        response, audio_url = get_last_shloka(user_id)
    else:
        response, audio_url = "❌ Invalid input. Please enter a chapter number (1-18), '0' for any chapter, or 's' for the last shloka.", None

    if response:
        await update.message.reply_text(response)

    if audio_url:
        await update.message.reply_audio(audio=audio_url)  # 🔥 FIX: Autoplay audio for ALL cases

# Start Handler
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome to the Bhagavad Gita Bot! Type a chapter number (1-18) to get a shloka, or 's' to get the last one.")

# Main Function
def main():
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    PORT = int(os.getenv("PORT", 8443))
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
