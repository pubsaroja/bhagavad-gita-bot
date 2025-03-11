import os
import random
import requests
import logging
import json
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Configure logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token & GitHub URL
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")
WORD_INDEX_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/gita_word_index.txt"  # Replace with your actual URL

if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN is missing!")

# Session data
session_data = {}

# Load existing shloka data (unchanged)
HINDI_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20with%20Uvacha.txt"
ENGLISH_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20English%20with%20Uvacha.txt"
HINDI_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20without%20Uvacha.txt"
TELUGU_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20Without%20Uvacha.txt"
ENGLISH_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20English%20without%20Uvacha.txt"
AUDIO_QUARTER_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioQuarter/"
AUDIO_FULL_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioFull/"

def load_shlokas_from_github(url):
    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f"⚠️ Error fetching data from {url}")
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

shlokas_hindi = load_shlokas_from_github(HINDI_WITHOUT_UVACHA_URL)
shlokas_telugu = load_shlokas_from_github(TELUGU_WITHOUT_UVACHA_URL)
shlokas_english = load_shlokas_from_github(ENGLISH_WITHOUT_UVACHA_URL)
full_shlokas_hindi = load_shlokas_from_github(HINDI_WITH_UVACHA_URL)
full_shlokas_telugu = load_shlokas_from_github(TELUGU_WITH_UVACHA_URL)
full_shlokas_english = load_shlokas_from_github(ENGLISH_WITH_UVACHA_URL)

# Load word index
def load_word_index():
    response = requests.get(WORD_INDEX_URL)
    if response.status_code != 200:
        logger.error(f"⚠️ Error fetching word index from {WORD_INDEX_URL}")
        return {}
    word_index = {}
    lines = response.text.split("\n")
    for line in lines:
        line = line.strip()
        if not line or line.startswith("%"):
            continue
        # Extract term and verse (if present)
        parts = line.split(" = ")
        if len(parts) < 2:
            continue
        term = parts[0].strip().lower()  # Case-insensitive search
        # Check if verse is present in parentheses
        verse_match = line.split("(")
        if len(verse_match) > 1:
            verse = verse_match[1].split(")")[0].strip()
            if term not in word_index:
                word_index[term] = []
            if verse not in word_index[term]:  # Avoid duplicates
                word_index[term].append(verse)
    return word_index

word_index = load_word_index()

# Search word occurrences
def search_word_occurrences(term):
    term = term.lower()  # Case-insensitive search
    if term not in word_index or not word_index[term]:
        return f"No occurrences found for '{term}'."
    
    occurrences = len(word_index[term])
    response = f"Found '{term}' in {occurrences} verse(s):\n"
    
    for verse in sorted(word_index[term]):  # Sort for consistent output
        chapter, verse_num = verse.split(".")
        response += f"{verse}:\n"
        
        # Fetch Telugu shloka
        telugu_text = "Telugu: (not found)"
        if chapter in shlokas_telugu:
            shloka_idx = next((i for i, v in enumerate(shlokas_telugu[chapter]) if v[0] == verse_num), None)
            if shloka_idx is not None:
                telugu_text = f"Telugu: {shlokas_telugu[chapter][shloka_idx][1]}"
        
        # Fetch Hindi shloka
        hindi_text = "Hindi: (not found)"
        if chapter in shlokas_hindi:
            shloka_idx = next((i for i, v in enumerate(shlokas_hindi[chapter]) if v[0] == verse_num), None)
            if shloka_idx is not None:
                hindi_text = f"Hindi: {shlokas_hindi[chapter][shloka_idx][1]}"
        
        # Fetch English shloka
        english_text = "English: (not found)"
        if chapter in shlokas_english:
            shloka_idx = next((i for i, v in enumerate(shlokas_english[chapter]) if v[0] == verse_num), None)
            if shloka_idx is not None:
                english_text = f"English: {shlokas_english[chapter][shloka_idx][1]}"
        
        response += f"{telugu_text}\n{hindi_text}\n{english_text}\n\n"
    
    return response

# Rest of the code remains unchanged (abbreviated for brevity)
async def handle_message(update: Update, context: CallbackContext):
    try:
        original_text = update.message.text.strip().lower()
        user_id = update.message.from_user.id
        logger.info(f"Received input: {original_text} from user {user_id}")

        # Check for audio modifiers and preserve the base command
        audio_only = original_text.endswith("ao")
        with_audio = original_text.endswith("a") and not audio_only and original_text not in SYLLABLE_MAP
        base_command = original_text
        if audio_only:
            base_command = original_text[:-2]
        elif with_audio:
            base_command = original_text[:-1]

        full_audio = base_command in ["f", "n1", "n2", "n3", "n4", "n5", "p"] or with_audio or audio_only

        # Handle word search (e.g., 'w dhR^itaraashhTra')
        if base_command.startswith("w "):
            term = base_command[2:].strip()
            response = search_word_occurrences(term)
            await update.message.reply_text(response)
            return

        # ... [Rest of the handle_message function remains unchanged]

    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ An error occurred.")

# Command handlers and main function (unchanged)
async def start(update: Update, context: CallbackContext):
    logger.info("Bot started with /start command")
    await update.message.reply_text(
        "Jai Gurudatta!\n"
        "Welcome to Srimad Bhagavadgita Bot.\n"
        "w <term> → Search word occurrences (e.g., 'w dhR^itaraashhTra')\n"
        # ... [Rest of the start message]
    )

async def reset(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in session_data:
        del session_data[user_id]
    await update.message.reply_text("✅ Session reset! Start anew with any chapter.")

def main():
    logger.info("Starting the bot...")
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(CommandHandler("reset", reset))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    logger.info("Starting polling mode")
    app.run_polling()

if __name__ == "__main__":
    main()
