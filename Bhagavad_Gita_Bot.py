import os
import random
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Your Railway domain

# GitHub Raw File URLs (Replace these with actual GitHub links)
HINDI_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/BG%20Telugu%20with%20Uvacha.txt"
HINDI_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/BG%20Hindi%20without%20Uvacha.txt"
TELUGU_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/BG%20Telugu%20Without%20Uvacha.txt"

# Dictionary to store user session data (to prevent repetition)
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
            chapter = full_number.split(".")[0]  # Extract only "chapter"

            if chapter not in shlokas:
                shlokas[chapter] = []

            # Append to existing shloka if it's the same chapter
            if current_chapter == chapter:
                current_shloka += " " + text
            else:
                if current_chapter and current_shloka:
                    shlokas[current_chapter].append(current_shloka.strip())

                current_chapter = chapter
                current_shloka = text

    # Save last shloka after finishing the loop
    if current_chapter and current_shloka:
        shlokas[current_chapter].append(current_shloka.strip())

    return shlokas

# Load shlokas from GitHub
shlokas_hindi = load_shlokas_from_github(HINDI_WITHOUT_UVACHA_URL)
shlokas_telugu = load_shlokas_from_github(TELUGU_WITHOUT_UVACHA_URL)
full_shlokas_hindi = load_shlokas_from_github(HINDI_WITH_UVACHA_URL)
full_shlokas_telugu = load_shlokas_from_github(TELUGU_WITH_UVACHA_URL)

def get_random_shloka(chapter: str, user_id: int):
    """Returns the first quarter of a unique random shloka in Hindi & Telugu."""
    global session_data

    chapter = str(chapter).strip()

    # Handle input `0` to select a random chapter
    if chapter == "0":
        chapter = random.choice([c for c in shlokas_hindi.keys() if shlokas_hindi[c]])

    print(f"Received chapter input: {chapter}")

    if chapter not in shlokas_hindi or not shlokas_hindi[chapter]:
        return "❌ Invalid chapter number. Please enter a number between 1-18."

    # Initialize session data for the user if not present
    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": {}, "last_shloka": None}

    if chapter not in session_data[user_id]["used_shlokas"]:
        session_data[user_id]["used_shlokas"][chapter] = set()

    used_shlokas = session_data[user_id]["used_shlokas"][chapter]
    total_shlokas = len(shlokas_hindi[chapter])

    # Reset session data if all shlokas have been used
    if len(used_shlokas) >= total_shlokas:
        session_data[user_id]["used_shlokas"][chapter] = set()
        used_shlokas.clear()

    available_shlokas = [i for i in range(total_shlokas) if i not in used_shlokas]

    if not available_shlokas:
        return "✅ All shlokas from this chapter have been shown in this session! Resetting now..."

    # Select a new random shloka
    shloka_index = random.choice(available_shlokas)
    used_shlokas.add(shloka_index)

    shloka_hindi = shlokas_hindi[chapter][shloka_index].split()
    shloka_telugu = shlokas_telugu[chapter][shloka_index].split()

    # Ensure full shloka exists
    if chapter not in full_shlokas_hindi or shloka_index >= len(full_shlokas_hindi[chapter]):
        return "❌ No shloka found for this chapter."

    session_data[user_id]["last_shloka"] = (
        full_shlokas_hindi[chapter][shloka_index],
        full_shlokas_telugu[chapter][shloka_index]
    )

    return f"📖 **Hindi:** {shloka_hindi[0]}\n🕉 **Telugu:** {shloka_telugu[0]}"

def get_last_shloka(user_id: int):
    """Returns the full last displayed shloka in Hindi & Telugu."""
    if user_id in session_data and session_data[user_id]["last_shloka"]:
        shloka_hindi, shloka_telugu = session_data[user_id]["last_shloka"]
        return f"📜 **Full Shloka (Hindi):** {shloka_hindi}\n🕉 **Telugu:** {shloka_telugu}"
    return "❌ No previous shloka found. Please request one first!"

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Handles user input."""
    user_text = update.message.text.strip()
    user_id = update.message.chat_id

    if user_text.isdigit():
        response = get_random_shloka(user_text, user_id)
    elif user_text.lower() == "s":
        response = get_last_shloka(user_id)
    else:
        response = "❌ Please enter a valid chapter number (1-18) or 's' for the last shloka."

    await update.message.reply_text(response)

async def start(update: Update, context: CallbackContext):
    """Sends a welcome message when the user starts the bot."""
    await update.message.reply_text("Welcome to the Bhagavad Gita Bot! Type a chapter number (1-18) to get a shloka, or 's' to get the last one.")

def main():
    """Main function to run the bot with webhook on Railway."""
    app = Application.builder().token(TOKEN).build()

    # Add handlers
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Use Webhooks instead of Polling for Railway
    PORT = int(os.getenv("PORT", 8443))
    app.run_webhook(
        listen="0.0.0.0",
        port=PORT,
        url_path=TOKEN,
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
