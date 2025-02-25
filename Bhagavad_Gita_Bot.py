import os
import random
import requests
import logging
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Configure logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token & Webhook URL
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN is missing! Set it in Railway's environment variables.")

# File URLs
HINDI_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20with%20Uvacha.txt"
HINDI_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20without%20Uvacha.txt"
TELUGU_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20Without%20Uvacha.txt"

AUDIO_QUARTER_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioQuarter/"
AUDIO_FULL_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioFull/"

# Session data to track shown shlokas per chapter
session_data = {}

# Function to load shlokas from GitHub
def load_shlokas_from_github(url):
    response = requests.get(url)
    if response.status_code != 200:
        logger.error(f"⚠️ Error fetching data from {url} (Status Code: {response.status_code})")
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
shlokas_hindi = load_shlokas_from_github(HINDI_WITHOUT_UVACHA_URL)
shlokas_telugu = load_shlokas_from_github(TELUGU_WITHOUT_UVACHA_URL)
full_shlokas_hindi = load_shlokas_from_github(HINDI_WITH_UVACHA_URL)
full_shlokas_telugu = load_shlokas_from_github(TELUGU_WITH_UVACHA_URL)

def get_shloka(chapter: str, verse_idx: int, with_audio: bool = False):
    chapter = str(chapter)
    while chapter in full_shlokas_hindi:
        if verse_idx < len(full_shlokas_hindi[chapter]):
            verse, shloka_hindi = full_shlokas_hindi[chapter][verse_idx]
            _, shloka_telugu = full_shlokas_telugu[chapter][verse_idx]
            
            audio_file_name = f"{chapter}.{verse}.mp3"
            audio_link = f"{AUDIO_FULL_URL}{audio_file_name}" if with_audio else None
            
            return f"{chapter}.{verse}\n{shloka_hindi}\n{shloka_telugu}", audio_link, chapter, verse_idx
        else:
            # Move to the next chapter
            verse_idx = verse_idx - len(full_shlokas_hindi[chapter])
            chapter = str(int(chapter) + 1)
    return None, None, None, None

def get_random_shloka(chapter: str, user_id: int, with_audio: bool = False):
    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": {}, "last_chapter": None, "last_index": None}

    chapter = str(chapter).strip()
    if chapter == "0":
        chapter = random.choice(list(shlokas_hindi.keys()))
    
    if chapter not in shlokas_hindi:
        return "❌ Invalid chapter number. Please enter a number between 0-18.", None

    # Initialize used_shlokas for this chapter if not present
    if chapter not in session_data[user_id]["used_shlokas"]:
        session_data[user_id]["used_shlokas"][chapter] = set()

    available_shlokas = [
        i for i in range(len(shlokas_hindi[chapter]))
        if i not in session_data[user_id]["used_shlokas"][chapter]
    ]

    if not available_shlokas:
        return f"✅ All shlokas from chapter {chapter} have been shown! Type 'c' to continue with this chapter.", None

    shloka_index = random.choice(available_shlokas)
    session_data[user_id]["used_shlokas"][chapter].add(shloka_index)
    session_data[user_id]["last_chapter"] = chapter
    session_data[user_id]["last_index"] = shloka_index

    verse, shloka_hindi = shlokas_hindi[chapter][shloka_index]
    _, shloka_telugu = shlokas_telugu[chapter][shloka_index]
    
    audio_file_name = f"{chapter}.{verse}.mp3"
    audio_link = f"{AUDIO_QUARTER_URL}{audio_file_name}" if with_audio else None
    
    return f"{chapter}.{verse}\n{shloka_hindi}\n{shloka_telugu}", audio_link

def get_specific_shloka(chapter: str, verse: str, user_id: int, with_audio: bool = False):
    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": {}, "last_chapter": None, "last_index": None}

    chapter = str(chapter)
    verse_idx = int(verse) - 1  # Convert to 0-based index
    
    if chapter not in full_shlokas_hindi or verse_idx < 0 or verse_idx >= len(full_shlokas_hindi[chapter]):
        return "❌ Invalid chapter or verse number. Use format 'chapter.verse' (e.g., 18.5).", None
    
    response, audio_url, new_chapter, new_idx = get_shloka(chapter, verse_idx, with_audio)
    if response:
        session_data[user_id]["last_chapter"] = new_chapter
        session_data[user_id]["last_index"] = new_idx
    return response, audio_url

def get_last_shloka(user_id: int, with_audio: bool = False):
    if user_id in session_data and session_data[user_id]["last_index"] is not None:
        chapter = session_data[user_id]["last_chapter"]
        shloka_index = session_data[user_id]["last_index"]
        verse, shloka_hindi = full_shlokas_hindi[chapter][shloka_index]
        _, shloka_telugu = full_shlokas_telugu[chapter][shloka_index]

        audio_file_name = f"{chapter}.{verse}.mp3"
        audio_link = f"{AUDIO_FULL_URL}{audio_file_name}" if with_audio else None

        return f"{chapter}.{verse}\n{shloka_hindi}\n{shloka_telugu}", audio_link
    return "❌ No previous shloka found. Please request one first!", None

async def handle_message(update: Update, context: CallbackContext):
    user_text = update.message.text.strip().lower()
    user_id = update.message.from_user.id

    with_audio = user_text.endswith("a")
    if with_audio:
        user_text = user_text[:-1]

    # Handle specific shloka request (e.g., "18.5")
    if "." in user_text:
        try:
            chapter, verse = user_text.split(".")
            response, audio_url = get_specific_shloka(chapter, verse, user_id, with_audio)
            await update.message.reply_text(response)
            if audio_url:
                await update.message.reply_audio(audio_url)
        except ValueError:
            await update.message.reply_text("❌ Invalid format. Use 'chapter.verse' (e.g., 18.5).")
        return
            
    elif user_text.isdigit():
        response, audio_url = get_random_shloka(user_text, user_id, with_audio)
        await update.message.reply_text(response)
        if audio_url:
            await update.message.reply_audio(audio_url)
            
    elif user_text == "f":
        response, audio_url = get_last_shloka(user_id, with_audio)
        await update.message.reply_text(response)
        if audio_url:
            await update.message.reply_audio(audio_url)
            
    elif user_text == "n1":  # Changed from 'n' to 'n1'
        if user_id in session_data and session_data[user_id]["last_index"] is not None:
            chapter = session_data[user_id]["last_chapter"]
            next_idx = session_data[user_id]["last_index"] + 1
            response, audio_url, new_chapter, new_idx = get_shloka(chapter, next_idx, with_audio)
            if response:
                session_data[user_id]["last_chapter"] = new_chapter
                session_data[user_id]["last_index"] = new_idx
                await update.message.reply_text(response)
                if audio_url:
                    await update.message.reply_audio(audio_url)
            else:
                await update.message.reply_text("❌ No more shlokas available!")
        else:
            await update.message.reply_text("❌ Please request a shloka first!")
            
    elif user_text in ["n2", "n3", "n4", "n5"]:
        if user_id not in session_data or session_data[user_id]["last_index"] is None:
            await update.message.reply_text("❌ Please request a shloka first!")
            return
            
        chapter = session_data[user_id]["last_chapter"]
        current_idx = session_data[user_id]["last_index"]
        count = int(user_text[1:])
        
        responses = []
        audio_urls = []
        last_chapter = chapter
        last_idx = current_idx
        
        # Fetch `count` consecutive shlokas
        for i in range(count):
            response, audio_url, new_chapter, new_idx = get_shloka(last_chapter, last_idx + 1, with_audio)
            if response:
                responses.append(response)
                if audio_url:
                    audio_urls.append(audio_url)
                last_chapter = new_chapter
                last_idx = new_idx
            else:
                break
                
        if responses:
            session_data[user_id]["last_chapter"] = last_chapter
            session_data[user_id]["last_index"] = last_idx
            for response in responses:
                await update.message.reply_text(response)
            for audio_url in audio_urls:
                await update.message.reply_audio(audio_url)
        else:
            await update.message.reply_text("❌ No more shlokas available!")
            
    elif user_text in ["p", "pa"]:
        if user_id not in session_data or session_data[user_id]["last_index"] is None:
            await update.message.reply_text("❌ Please request a shloka first!")
            return
            
        chapter = session_data[user_id]["last_chapter"]
        current_idx = session_data[user_id]["last_index"]
        
        # Calculate starting point (2 shlokas back)
        start_chapter = chapter
        start_idx = current_idx - 2
        responses = []
        audio_urls = []
        last_chapter = chapter
        last_idx = current_idx
        
        # Handle going backwards across chapters
        while start_idx < 0 and int(start_chapter) > 1:
            start_chapter = str(int(start_chapter) - 1)
            start_idx += len(full_shlokas_hindi[start_chapter])
        
        # Fetch 5 continuous shlokas (prev 2, current, next 2)
        chapter = start_chapter
        idx = max(0, start_idx)
        for _ in range(5):  # 5 shlokas total
            response, audio_url, new_chapter, new_idx = get_shloka(chapter, idx, with_audio)
            if response:
                responses.append(response)
                if audio_url:
                    audio_urls.append(audio_url)
                last_chapter = new_chapter
                last_idx = new_idx
                chapter = new_chapter
                idx = new_idx + 1
            else:
                break
        
        if responses:
            session_data[user_id]["last_chapter"] = last_chapter
            session_data[user_id]["last_index"] = last_idx
            for response in responses:
                await update.message.reply_text(response)
            for audio_url in audio_urls:
                await update.message.reply_audio(audio_url)

    elif user_text == "c":
        if user_id in session_data and session_data[user_id]["last_chapter"] is not None:
            chapter = session_data[user_id]["last_chapter"]
            if chapter in session_data[user_id]["used_shlokas"]:
                session_data[user_id]["used_shlokas"][chapter].clear()
                await update.message.reply_text(f"✅ Chapter {chapter} has been reset. You can now get random shlokas again!")
            else:
                await update.message.reply_text("❌ No shlokas have been shown from this chapter yet!")
        else:
            await update.message.reply_text("❌ Please request a shloka first!")
            
    else:
        await update.message.reply_text(
            "❌ Invalid input.\n"
            "✨ Please use:\n"
            "- 0-18 → Get a random shloka from a chapter\n"
            "- chapter.verse → Get a specific shloka (e.g., 18.5)\n"
            "- Add 'a' for audio (e.g., 0a, 18.5a)\n\n"
            "🎯 Navigation:\n"
            "- f → Full version of the last shloka\n"
            "- fa → Full version with audio\n"
            "- n1 → Next shloka\n"
            "- n1a → Next shloka with audio\n"
            "- n2-n5 → Next 2-5 shlokas\n"
            "- p → Previous 2, current, and next 2 shlokas\n"
            "- pa → Same with audio\n"
            "- c → Reset current chapter for more random shlokas"
        )

async def start(update: Update, context: CallbackContext):
    user_text = update.message.text.strip().lower()
    user_id = update.message.from_user.id
    if user_text == "18a":  # Temporary test
        await update.message.reply_audio("https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioFull/18.1.mp3")
        return
    await update.message.reply_text(
"Jai Gurudatta! 🙏\n"
        "Welcome to the Srimad Bhagavad Gita Random Practice Bot!\n\n"
        "✨ Features:\n"
        "- 0-18 → Get a random shloka from a chapter\n"
        "- chapter.verse → Get a specific shloka (e.g., 18.5)\n"
        "- Add 'a' for audio (e.g., 0a, 18.5a)\n\n"
        "🎯 Navigation:\n"
        "- f → Full version of the last shloka\n"
        "- fa → Full version with audio\n"
        "- n1 → Next shloka\n"
        "- n1a → Next shloka with audio\n"
        "- n2-n5 → Next 2-5 shlokas\n"
        "- p → Previous 2, current, and next 2 shlokas\n"
        "- pa → Same with audio\n"
        "- c → Reset current chapter for more random shlokas"
    )

def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.run_webhook(listen="0.0.0.0", port=int(os.getenv("PORT", 5000)), webhook_url=WEBHOOK_URL)

if __name__ == "__main__":
    main()
