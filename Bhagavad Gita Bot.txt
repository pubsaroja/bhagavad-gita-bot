import os
import random
import requests
from telegram import Update
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, CallbackContext

# Securely get the bot token from Railway environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# GitHub Raw File URLs (Replace these with your actual GitHub links)
HINDI_WITH_UVACHA_URL = "https://github.com/pubsaroja/bhagavad-gita-bot/blob/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://github.com/pubsaroja/bhagavad-gita-bot/blob/main/BG%20Telugu%20with%20Uvacha.txt"
HINDI_WITHOUT_UVACHA_URL = "https://github.com/pubsaroja/bhagavad-gita-bot/blob/main/BG%20Hindi%20without%20Uvacha.txt"
TELUGU_WITHOUT_UVACHA_URL = "https://github.com/pubsaroja/bhagavad-gita-bot/blob/main/BG%20Telugu%20Without%20Uvacha.txt"

# Dictionary to store session data (to prevent repetition)
session_data = {}

def load_shlokas_from_github(url):
    """Fetches and organizes shlokas from GitHub text files."""
    response = requests.get(url)
    shlokas = {}
    
    if response.status_code == 200:
        lines = response.text.split("\n")
        current_chapter = None
        
        for line in lines:
            line = line.strip()
            if line and "." in line:
                chapter, text = line.split("\t", 1)
                chapter = chapter.split(".")[0]  # Extract chapter number
                if chapter not in shlokas:
                    shlokas[chapter] = []
                shlokas[chapter].append(text)
    return shlokas

# Load shlokas from GitHub
shlokas_hindi = load_shlokas_from_github(HINDI_WITHOUT_UVACHA_URL)
shlokas_telugu = load_shlokas_from_github(TELUGU_WITHOUT_UVACHA_URL)
full_shlokas_hindi = load_shlokas_from_github(HINDI_WITH_UVACHA_URL)
full_shlokas_telugu = load_shlokas_from_github(TELUGU_WITH_UVACHA_URL)

def get_random_shloka(chapter: str, user_id: int):
    """Returns the first quarter of a unique random shloka in Hindi & Telugu."""
    global session_data
    
    # Initialize session if user is new
    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": set(), "last_shloka": None}

    if chapter == "0":  # Pick from any chapter
        chapter = random.choice(list(shlokas_hindi.keys()))

    if chapter in shlokas_hindi:
        available_shlokas = [
            i for i in range(len(shlokas_hindi[chapter])) 
            if i not in session_data[user_id]["used_shlokas"]
        ]
        
        if not available_shlokas:
            return "✅ All shlokas from this chapter have been shown in this session!"

        shloka_index = random.choice(available_shlokas)
        session_data[user_id]["used_shlokas"].add(shloka_index)

        shloka_hindi = shlokas_hindi[chapter][shloka_index].split()
        shloka_telugu = shlokas_telugu[chapter][shloka_index].split()
        
        # Store full shloka for retrieval when "s" is entered
        session_data[user_id]["last_shloka"] = (
            full_shlokas_hindi[chapter][shloka_index],
            full_shlokas_telugu[chapter][shloka_index]
        )

        return f"📖 **Hindi:** {shloka_hindi[0]}\n🕉 **Telugu:** {shloka_telugu[0]}"
    
    return "❌ Invalid chapter number. Please enter a number between 0-18."

def get_last_shloka(user_id: int):
    """Returns the full last displayed shloka in Hindi & Telugu."""
    if user_id in session_data and session_data[user_id]["last_shloka"]:
        shloka_hindi, shloka_telugu = session_data[user_id]["last_shloka"]
        return f"📜 **Full Shloka (Hindi):** {shloka_hindi}\n🕉 **Telugu:** {shloka_telugu}"
    return "❌ No previous shloka found. Please request one first!"

def start(update: Update, context: CallbackContext) -> None:
    update.message.reply_text(
        "🔹 Welcome! Send a chapter number (0-18) for a random shloka quarter.\n"
        "🔹 Send 's' to see the full last shloka.\n"
        "🔹 Shlokas won't repeat in a single session!"
    )

def handle_message(update: Update, context: CallbackContext) -> None:
    user_text = update.message.text.strip()
    user_id = update.message.chat_id

    if user_text.isdigit():
        response = get_random_shloka(user_text, user_id)
    elif user_text.lower() == "s":
        response = get_last_shloka(user_id)
    else:
        response = "❌ Please enter a valid chapter number (0-18) or 's' for the last shloka."

    update.message.reply_text(response)

def main():
    updater = Updater(TOKEN)
    dp = updater.dispatcher

    dp.add_handler(CommandHandler("start", start))
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
