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
WORD_INDEX_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/gita_word_index.txt"  # Update with your repo URL

if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN is missing!")

# Session data
session_data = {}

# Load existing shloka data
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

# Load word index
def load_word_index():
    response = requests.get(WORD_INDEX_URL)
    if response.status_code != 200:
        logger.error(f"⚠️ Error fetching word index from {WORD_INDEX_URL}")
        return {}
    word_index = {}
    lines = response.text.split("\n")
    for line in lines:
        parts = line.split(" = ")
        if len(parts) == 2:
            word, verse = parts
            if word not in word_index:
                word_index[word] = []
            word_index[word].append(verse)
    return word_index

word_index = load_word_index()

# Search word occurrences
async def search_word(update: Update, context: CallbackContext):
    query = update.message.text.strip().lower()
    user_id = update.message.from_user.id
    
    if query in word_index:
        occurrences = len(word_index[query])
        response = f"\U0001F50D '{query}' found in {occurrences} verse(s):\n\n"
        
        for entry in word_index[query]:
            verse_number = entry.split('||')[1].strip("()").replace(".", ".")
            
            hindi_verse = next((v for ch, vlist in shlokas_hindi.items() for vn, v in vlist if vn == verse_number), "Not found")
            telugu_verse = next((v for ch, vlist in shlokas_telugu.items() for vn, v in vlist if vn == verse_number), "Not found")
            english_verse = next((v for ch, vlist in shlokas_english.items() for vn, v in vlist if vn == verse_number), "Not found")
            
            response += f"Verse {verse_number}:\n\n"
            response += f"*Hindi:*\n{hindi_verse}\n\n"
            response += f"*Telugu:*\n{telugu_verse}\n\n"
            response += f"*English:*\n{english_verse}\n\n"
            response += "---------------------------------\n"
        
        await update.message.reply_text(response[:4096], parse_mode='Markdown')
    else:
        await update.message.reply_text(f"❌ No occurrences found for '{query}'.")

# Main function
def main():
    application = Application.builder().token(TOKEN).build()
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, search_word))
    application.run_polling()

if __name__ == "__main__":
    main()
