import os
import random
import logging
import requests  # Add this import for downloading files
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Load Bhagavad Gita shlokas from GitHub files
shlokas_hindi = {}
shlokas_telugu = {}
full_shlokas_hindi = {}
full_shlokas_telugu = {}

# Session tracking to prevent repetition in one session
session_data = {}

# Function to download the file if it is a URL
def download_file(url):
    """Downloads file content from the URL"""
    response = requests.get(url)
    if response.status_code == 200:
        return response.text
    else:
        return None

# Function to load shlokas from file content (either from a local file or downloaded)
def load_shlokas(filename_or_url):
    chapters = {}
    content = None

    # If it's a URL, download the content
    if filename_or_url.startswith("http"):
        content = download_file(filename_or_url)
    else:
        # If it's a local file, just open it
        with open(filename_or_url, "r", encoding="utf-8") as file:
            content = file.read()

    if content is None:
        return chapters  # Return empty chapters if file content couldn't be loaded

    # Process the content
    chapter_data = []
    chapter_num = None
    for line in content.splitlines():
        line = line.strip()
        if line.isdigit():  # Chapter number
            if chapter_num is not None:
                chapters[str(chapter_num)] = chapter_data
            chapter_num = int(line)
            chapter_data = []
        elif line:
            chapter_data.append(line)
    if chapter_num is not None:
        chapters[str(chapter_num)] = chapter_data

    return chapters

# Load shlokas from GitHub files
shlokas_hindi = load_shlokas("https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20without%20Uvacha.txt")
shlokas_telugu = load_shlokas("https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20Without%20Uvacha.txt")
full_shlokas_hindi = load_shlokas("https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20with%20Uvacha.txt")
full_shlokas_telugu = load_shlokas("https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20with%20Uvacha.txt")

# Function to extract the first quarter of the shloka
def get_first_quarter(text):
    words = text.split()
    quarter_length = max(1, len(words) // 4)  # Ensure at least 1 word
    return " ".join(words[:quarter_length])  # Extract first 25% words

# Function to fetch a random shloka from the specified chapter
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

    if shloka_index >= len(shlokas_hindi[chapter]) or shloka_index >= len(shlokas_telugu[chapter]):
        return "❌ Error: Invalid shloka index."

    shloka_hindi = shlokas_hindi[chapter][shloka_index]
    shloka_telugu = shlokas_telugu[chapter][shloka_index]

    if not shloka_hindi or not shloka_telugu:
        return "❌ Error: Empty shloka text."

    # ✅ Extract the first quarter of the shloka
    first_quarter_hindi = get_first_quarter(shloka_hindi)
    first_quarter_telugu = get_first_quarter(shloka_telugu)

    # Save the full shloka for later retrieval
    session_data[user_id]["last_shloka"] = (
        full_shlokas_hindi[chapter][shloka_index],
        full_shlokas_telugu[chapter][shloka_index]
    )

    return f"📖 **Hindi:** {first_quarter_hindi}\n🕉 **Telugu:** {first_quarter_telugu}"

# Function to fetch the last full shloka
def get_last_shloka(user_id: int):
    """Returns the last full shloka in Hindi & Telugu."""
    if user_id in session_data and session_data[user_id]["last_shloka"]:
        hindi_shloka, telugu_shloka = session_data[user_id]["last_shloka"]
        return f"📖 **Full Hindi:** {hindi_shloka}\n🕉 **Full Telugu:** {telugu_shloka}"
    return "❌ No previous shloka found. Try entering a chapter number first!"

# Telegram bot handlers
async def start(update: Update, context: CallbackContext) -> None:
    await update.message.reply_text(
        "🕉 **Welcome to the Bhagavad Gita Bot!**\n\n"
        "📜 Enter a chapter number (1-18) to get a random shloka.\n"
        "🔄 Enter '0' to get a random shloka from any chapter.\n"
        "📖 Enter 's' to see the last full shloka.\n"
        "🙏 Hare Krishna! 🙏"
    )

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

# Logging setup
logging.basicConfig(
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s", level=logging.INFO
)

# Telegram Bot Setup
TOKEN = os.getenv("BOT_TOKEN")  # Make sure your token is stored securely in environment variables

def main():
    """Start the bot."""
    application = Application.builder().token(TOKEN).build()

    application.add_handler(CommandHandler("start", start))
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    application.run_polling()

if __name__ == "__main__":
    main()
