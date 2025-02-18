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
    """Fetches and organizes shlokas from GitHub text files by chapter."""
    response = requests.get(url)
    
    if response.status_code != 200:
        print(f"⚠️ Error fetching data from {url} (Status Code: {response.status_code})")
        return {}

    shlokas = {}
    lines = response.text.split("\n")
    current_shloka = ""
    current_chapter = None

    for line in lines:
        line = line.strip()
        if not line:
            continue

        parts = line.split("\t", 1)
        if len(parts) == 2:
            full_number, text = parts
            chapter = full_number.split(".")[0]

            if chapter not in shlokas:
                shlokas[chapter] = []

            if current_chapter == chapter:
                current_shloka += " " + text
            else:
                if current_chapter and current_shloka:
                    shlokas[current_chapter].append(current_shloka.strip())

                current_chapter = chapter
                current_shloka = text

    if current_chapter and current_shloka:
        shlokas[current_chapter].append(current_shloka.strip())

    return shlokas

shlokas_hindi = load_shlokas_from_github(HINDI_WITHOUT_UVACHA_URL)
shlokas_telugu = load_shlokas_from_github(TELUGU_WITHOUT_UVACHA_URL)
full_shlokas_hindi = load_shlokas_from_github(HINDI_WITH_UVACHA_URL)
full_shlokas_telugu = load_shlokas_from_github(TELUGU_WITH_UVACHA_URL)

def get_random_shloka(chapter: str, user_id: int):
    """Returns the first quarter of a unique random shloka in Hindi & Telugu."""
    global session_data

    chapter = str(chapter).strip()

    if chapter == "0":
        chapter = random.choice([c for c in shlokas_hindi.keys() if shlokas_hindi[c]])

    if chapter not in shlokas_hindi or not shlokas_hindi[chapter]:
        return "❌ Invalid chapter number. Please enter a number between 1-18."

    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": {}, "last_shloka": None}

    if chapter not in session_data[user_id]["used_shlokas"]:
        session_data[user_id]["used_shlokas"][chapter] = set()

    used_shlokas = session_data[user_id]["used_shlokas"][chapter]
    total_shlokas = len(shlokas_hindi[chapter])

    if len(used_shlokas) >= total_shlokas:
        session_data[user_id]["used_shlokas"][chapter] = set()
        used_shlokas.clear()

    available_shlokas = [i for i in range(total_shlokas) if i not in used_shlokas]

    if not available_shlokas:
        return "✅ All shlokas from this chapter have been shown in this session! Resetting now..."

    shloka_index = random.choice(available_shlokas)
    used_shlokas.add(shloka_index)

    # Ensure valid indexing
    if shloka_index >= len(shlokas_hindi[chapter]) or shloka_index >= len(shlokas_telugu[chapter]):
        return "❌ Error: Invalid shloka index."

    shloka_hindi = shlokas_hindi[chapter][shloka_index]
    shloka_telugu = shlokas_telugu[chapter][shloka_index]

    if not shloka_hindi or not shloka_telugu:
        return "❌ Error: Empty shloka text."

    session_data[user_id]["last_shloka"] = (
        full_shlokas_hindi[chapter][shloka_index],
        full_shlokas_telugu[chapter][shloka_index]
    )

    # Get the first quarter of the shloka (split by space)
    hindi_words = shloka_hindi.split()
    telugu_words = shloka_telugu.split()

    # Get the first quarter (for splitting the shloka into 4 parts)
    first_quarter_hindi = " ".join(hindi_words[:len(hindi_words)//4])
    first_quarter_telugu = " ".join(telugu_words[:len(telugu_words)//4])

    return f"📖 **Hindi (Quarter 1):** {first_quarter_hindi}\n🕉 **Telugu (Quarter 1):** {first_quarter_telugu}"

def get_last_shloka(user_id: int):
    """Returns the full last displayed shloka in Hindi & Telugu."""
    if user_id in session_data and session_data[user_id]["last_shloka"]:
        shloka_hindi, shloka_telugu = session_data[user_id]["last_shloka"]

        if not shloka_hindi or not shloka_telugu:
            return ["❌ Error: Last shloka is empty."]

        return [f"📜 **Full Shloka (Hindi):** {shloka_hindi}\n🕉 **Telugu:** {shloka_telugu}"]

    return ["❌ No previous shloka found. Please request one first!"]

import logging

# Set up logging to track message length
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
        max_message_length = 4096
        logging.info(f"Message length: {len(response)}")

        # Split the message if it's too long
        while len(response) > max_message_length:
            await update.message.reply_text(response[:max_message_length])
            response = response[max_message_length:]
        
        # Send the remaining message chunk
        await update.message.reply_text(response)

async def start(update: Update, context: CallbackContext):
    """Sends a welcome message when the user starts the bot."""
    await update.message.reply_text("Welcome to the Bhagavad Gita Bot! Type a chapter number (1-18) to get a shloka, or 's' to get the last one.")

def main():
    """Main function to run the bot with webhook on Railway."""
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
