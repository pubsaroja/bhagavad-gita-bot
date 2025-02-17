import os
import random
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Securely get the bot token from Railway environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")

# GitHub Raw File URLs (Replace these with your actual GitHub links)
HINDI_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/BG%20Telugu%20with%20Uvacha.txt"
HINDI_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/BG%20Hindi%20without%20Uvacha.txt"
TELUGU_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/BG%20Telugu%20Without%20Uvacha.txt"

# Dictionary to store session data (to prevent repetition)
session_data = {}

def load_shlokas_from_github(url):
    """Fetches and organizes shlokas from GitHub text files."""
    response = requests.get(url)
    shlokas = {}

    if response.status_code == 200:
        lines = response.text.split("\n")
        current_shloka = ""
        current_chapter_verse = None

        for line in lines:
            line = line.strip()
            if not line:  # Skip empty lines
                continue

            parts = line.split("\t", 1)
            if len(parts) == 2:
                full_number, text = parts
                chapter_verse = ".".join(full_number.split(".")[:2])  # Extract "chapter.verse"

                if chapter_verse not in shlokas:
                    shlokas[chapter_verse] = []

                # Append to existing shloka if it's the same chapter_verse
                if current_chapter_verse == chapter_verse:
                    current_shloka += " " + text
                else:
                    if current_chapter_verse and current_shloka:
                        shlokas[current_chapter_verse].append(current_shloka.strip())

                    current_chapter_verse = chapter_verse
                    current_shloka = text
            else:
                print(f"Skipping invalid line: {line}")

        # Save last shloka after finishing the loop
        if current_chapter_verse and current_shloka:
            shlokas[current_chapter_verse].append(current_shloka.strip())

    return shlokas

# Load shlokas from GitHub
shlokas_hindi = load_shlokas_from_github(HINDI_WITHOUT_UVACHA_URL)
shlokas_telugu = load_shlokas_from_github(TELUGU_WITHOUT_UVACHA_URL)
full_shlokas_hindi = load_shlokas_from_github(HINDI_WITH_UVACHA_URL)
full_shlokas_telugu = load_shlokas_from_github(TELUGU_WITH_UVACHA_URL)

def get_random_shloka(chapter: str, user_id: int):
    """Returns the first quarter of a unique random shloka in Hindi & Telugu."""
    global session_data

    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": set(), "last_shloka": None}

    if chapter == "0":
        chapter = random.choice(list(shlokas_hindi.keys()))

    # Logging the input and available chapters for debugging
    print(f"Received chapter input: {chapter}")
    print(f"Available chapters: {list(shlokas_hindi.keys())}")

    # Ensure the chapter is a valid chapter number
    chapter = chapter.strip()
    if chapter not in shlokas_hindi:
        return "❌ Invalid chapter number. Please enter a number between 0-18."

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
    user_text = update.message.text.strip()
    user_id = update.message.chat_id

    if user_text.isdigit():
        response = get_random_shloka(user_text, user_id)
    elif user_text.lower() == "s":
        response = get_last_shloka(user_id)
    else:
        response = "❌ Please enter a valid chapter number (0-18) or 's' for the last shloka."

    await update.message.reply_text(response)

# Define the start function
async def start(update: Update, context: CallbackContext):
    """Sends a welcome message when the user starts the bot."""
    await update.message.reply_text("Welcome to the Bhagavad Gita Bot! Type a chapter number (0-18) to get a shloka, or 's' to get the last one.")

def main():
    # Initialize the bot with the token
    app = Application.builder().token(TOKEN).build()

    # Add the /start command handler
    app.add_handler(CommandHandler("start", start))

    # Add the message handler for user input
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Start the bot
    app.run_polling()

if __name__ == "__main__":
    main()
