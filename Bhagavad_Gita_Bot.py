import os
import random
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

HINDI_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20with%20Uvacha.txt"
HINDI_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20without%20Uvacha.txt"
TELUGU_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20Without%20Uvacha.txt"

session_data = {}

def load_shlokas_from_github(url):
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"⚠️ Error fetching data from {url} (Status Code: {response.status_code})")
        return {}

    shlokas = {}
    lines = response.text.split("\n")

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split("\t", 1)
        if len(parts) == 2:
            full_number, text = parts
            number_parts = full_number.split(".", 2)  # Ensure only first two parts are used
            chapter, verse = number_parts[:2]

            if chapter not in shlokas:
                shlokas[chapter] = []

            shlokas[chapter].append((verse, text))
    
    return shlokas

shlokas_hindi = load_shlokas_from_github(HINDI_WITHOUT_UVACHA_URL)
shlokas_telugu = load_shlokas_from_github(TELUGU_WITHOUT_UVACHA_URL)
full_shlokas_hindi = load_shlokas_from_github(HINDI_WITH_UVACHA_URL)
full_shlokas_telugu = load_shlokas_from_github(TELUGU_WITH_UVACHA_URL)

def get_random_shloka(chapter: str, user_id: int):
    global session_data

    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": set(), "last_shloka_index": None, "last_chapter": None}

    chapter = str(chapter).strip()

    if chapter == "0":
        chapter = random.choice(list(shlokas_hindi.keys()))

    if chapter not in shlokas_hindi:
        return "❌ Invalid chapter number. Please enter a number between 0-18."

    available_shlokas = [
        i for i in range(len(shlokas_hindi[chapter]))
        if i not in session_data[user_id]["used_shlokas"]
    ]

    if not available_shlokas:
        return f"✅ All shlokas from chapter {chapter} have been shown in this session!"

    shloka_index = random.choice(available_shlokas)
    session_data[user_id]["used_shlokas"].add(shloka_index)
    session_data[user_id]["last_shloka_index"] = shloka_index
    session_data[user_id]["last_chapter"] = chapter

    verse, shloka_hindi = shlokas_hindi[chapter][shloka_index]
    _, shloka_telugu = shlokas_telugu[chapter][shloka_index]

    return f"📖 **{chapter}.{verse}**\n🕉 {shloka_hindi}\n🕉 {shloka_telugu}"

def get_last_shloka(user_id: int):
    if user_id in session_data and session_data[user_id]["last_shloka_index"] is not None:
        chapter = session_data[user_id]["last_chapter"]
        shloka_index = session_data[user_id]["last_shloka_index"]
        verse, shloka_hindi = full_shlokas_hindi[chapter][shloka_index]
        _, shloka_telugu = full_shlokas_telugu[chapter][shloka_index]
        return f"📜 **{chapter}.{verse}**\n🕉 {shloka_hindi}\n🕉 {shloka_telugu}"
    return "❌ No previous shloka found. Please request one first!"

import logging

logging.basicConfig(level=logging.INFO)

async def handle_message(update: Update, context: CallbackContext) -> None:
    user_text = update.message.text.strip()
    user_id = update.message.from_user.id

    if user_text.isdigit():
        response = get_random_shloka(user_text, user_id)
    elif user_text.lower() == "s":
        response = get_last_shloka(user_id)
    else:
        response = "❌ Invalid input. Please enter a chapter number (1-18), '0' for any chapter, or 's' for the last shloka."

    if response:
        await update.message.reply_text(response)

async def start(update: Update, context: CallbackContext):
    await update.message.reply_text("Welcome to the Bhagavad Gita Bot! Type a chapter number (1-18) to get a shloka, or 's' to get the last one.")

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
