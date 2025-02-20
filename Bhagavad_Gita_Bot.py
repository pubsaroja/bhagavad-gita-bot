import os
import random
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Bot Token & Webhook URL
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# File URLs
HINDI_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20with%20Uvacha.txt"

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
                chapter, verse = current_number.split(".")[:2]  # Extract first two parts
                if chapter not in shlokas:
                    shlokas[chapter] = []
                shlokas[chapter].append((verse, "\n".join(current_text)))

            current_number = parts[0]  # New verse number
            current_text = [parts[1]]  # Start collecting new verse lines
        else:
            current_text.append(line)  # Continuation of previous verse

    # Save the last verse
    if current_number:
        chapter, verse = current_number.split(".")[:2]
        if chapter not in shlokas:
            shlokas[chapter] = []
        shlokas[chapter].append((verse, "\n".join(current_text)))

    return shlokas

# Load all shlokas
full_shlokas_hindi = load_shlokas_from_github(HINDI_WITH_UVACHA_URL)
full_shlokas_telugu = load_shlokas_from_github(TELUGU_WITH_UVACHA_URL)

import logging

logging.basicConfig(level=logging.INFO)

# Function to get the next shloka
def get_next_shloka(user_id: int, count: int = 1):
    if user_id not in session_data or "last_chapter" not in session_data[user_id]:
        return "❌ No previous shloka found. Please request one first!", None

    chapter = session_data[user_id]["last_chapter"]
    shloka_index = session_data[user_id]["last_shloka_index"]
    next_shlokas = []
    audio_links = []

    for _ in range(count):
        shloka_index += 1
        if shloka_index >= len(full_shlokas_hindi.get(chapter, [])):
            chapter = str(int(chapter) + 1)  # Move to the next chapter
            if chapter not in full_shlokas_hindi:
                return "✅ End of Bhagavad Gita reached!", None
            shloka_index = 0

        verse, shloka_hindi = full_shlokas_hindi[chapter][shloka_index]
        _, shloka_telugu = full_shlokas_telugu[chapter][shloka_index]
        audio_file_name = f"{chapter}.{verse}.mp3"
        audio_link = f"{AUDIO_FULL_URL}{audio_file_name}"

        next_shlokas.append(f"{chapter}.{verse}\n{shloka_hindi}\n{shloka_telugu}")
        audio_links.append(audio_link)

    session_data[user_id]["last_shloka_index"] = shloka_index
    session_data[user_id]["last_chapter"] = chapter

    return "\n\n".join(next_shlokas), audio_links[0] if audio_links else None

# Message Handler
async def handle_message(update: Update, context: CallbackContext) -> None:
    user_text = update.message.text.strip().lower()
    user_id = update.message.from_user.id

    with_audio = user_text.endswith("a")
    if with_audio:
        user_text = user_text[:-1]

    if user_text.startswith("n") and user_text[1:].isdigit():
        count = int(user_text[1:]) if len(user_text) > 1 else 1
        response, audio_url = get_next_shloka(user_id, count)
    else:
        response, audio_url = "❌ Invalid input. Please enter 'n' for next shloka or 'n2'-'n5' for multiple next shlokas.", None

    if response:
        await update.message.reply_text(response)
    if audio_url:
        await update.message.reply_audio(audio_url)

# Start Handler
async def start(update: Update, context: CallbackContext):
    await update.message.reply_text(
        "Jai Gurudatta!\n"
        "Welcome to Srimad Bhagavadgita Random Practice chatbot.\n"
        "Pressing n → Shows the next shloka.\n"
        "Pressing n2-n5 → Shows the next two to five shlokas.\n"
        "Pressing na → Plays the next shloka with audio.\n"
        "Pressing n2a-n5a → Plays the next two to five shlokas with audio."
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Set webhook for Telegram
    app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8443)),  # Railway assigns a port
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )

if __name__ == "__main__":
    main()

