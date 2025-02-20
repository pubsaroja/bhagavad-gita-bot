import os
import random
import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Bot Token & Webhook URL
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

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

        parts = line.split("\t", 1)  # Split only at the first tab
        if len(parts) == 2:
            if current_number:  # Save previous verse before starting a new one
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

# Function to get a random shloka
def get_random_shloka(chapter: str, user_id: int, with_audio: bool = False):
    global session_data

    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": set(), "last_shloka_index": None, "last_chapter": None}

    chapter = str(chapter).strip()

    if chapter == "0":
        chapter = random.choice(list(shlokas_hindi.keys()))
    
    if chapter not in shlokas_hindi:
        return "❌ Invalid chapter number. Please enter a number between 0-18.", None

    available_shlokas = [
        i for i in range(len(shlokas_hindi[chapter]))
        if i not in session_data[user_id]["used_shlokas"]
    ]

    if not available_shlokas:
        return f"✅ All shlokas from chapter {chapter} have been shown in this session!", None

    shloka_index = random.choice(available_shlokas)
    session_data[user_id]["used_shlokas"].add(shloka_index)
    session_data[user_id]["last_shloka_index"] = shloka_index
    session_data[user_id]["last_chapter"] = chapter

    verse, shloka_hindi = shlokas_hindi[chapter][shloka_index]
    _, shloka_telugu = shlokas_telugu[chapter][shloka_index]

    audio_file_name = f"{chapter}.{verse}.mp3"
    audio_link = f"{AUDIO_QUARTER_URL}{audio_file_name}" if with_audio else None

    return f"{chapter}.{verse}\n{shloka_hindi}\n{shloka_telugu}", audio_link

# Function to fetch the next n shlokas
def get_next_shlokas(user_id: int, count: int, with_audio: bool = False):
    if user_id not in session_data or session_data[user_id]["last_shloka_index"] is None:
        return "❌ No previous shloka found. Please request one first!", None

    chapter = session_data[user_id]["last_chapter"]
    last_index = session_data[user_id]["last_shloka_index"]
    total_shlokas = len(shlokas_hindi[chapter])

    results = []
    audio_links = []

    for _ in range(count):
        next_index = (last_index + 1) % total_shlokas  # Loop within chapter
        session_data[user_id]["last_shloka_index"] = next_index
        last_index = next_index

        verse, shloka_hindi = shlokas_hindi[chapter][next_index]
        _, shloka_telugu = shlokas_telugu[chapter][next_index]

        audio_file_name = f"{chapter}.{verse}.mp3"
        if with_audio:
            audio_links.append(f"{AUDIO_QUARTER_URL}{audio_file_name}")

        results.append(f"{chapter}.{verse}\n{shloka_hindi}\n{shloka_telugu}")

    return "\n\n".join(results), audio_links

# Message Handler
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_text = update.message.text.strip().lower()
    user_id = update.message.from_user.id

    with_audio = user_text.endswith("a")
    if with_audio:
        user_text = user_text[:-1]

    if user_text.isdigit():
        response, audio_url = get_random_shloka(user_text, user_id, with_audio)
    elif user_text == "s":
        response, audio_url = get_last_shloka(user_id, with_audio)
    elif user_text.startswith("n"):
        count = int(user_text[1:]) if user_text[1:].isdigit() else 1
        response, audio_urls = get_next_shlokas(user_id, count, with_audio)
    else:
        response, audio_url = "❌ Invalid input. Please enter a chapter number (1-18), '0' for any chapter, 's' for full shloka, or 'n' for next shloka.", None

    if response:
        await update.message.reply_text(response)
    if audio_urls:
        for audio_url in audio_urls:
            await update.message.reply_audio(audio_url)

# Main Function
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_polling()

if __name__ == "__main__":
    main()
