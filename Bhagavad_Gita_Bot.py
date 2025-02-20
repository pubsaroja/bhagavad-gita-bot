import os
import random
import requests
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# ✅ Replace this with your actual bot token
TOKEN = os.getenv("BOT_TOKEN")  

# ✅ Corrected URLs for fetching text and audio
HINDI_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20without%20Uvacha.txt"
TELUGU_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20without%20Uvacha.txt"
HINDI_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20with%20Uvacha.txt"
AUDIO_QUARTER_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioQuarter/"
AUDIO_FULL_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioFull/"

# ✅ Storing user session data
user_sessions = {}

async def start(update: Update, context: CallbackContext) -> None:
    """Handles the /start command"""
    user_id = update.message.chat_id
    user_sessions[user_id] = {"history": []}  # Initialize session
    await update.message.reply_text(
        "📖 Welcome to Bhagavad Gita Bot!\n\n"
        "👉 Press a chapter number (1-18) to get a random shloka.\n"
        "👉 Press '0' for a random shloka from all chapters.\n"
        "👉 Press 's' to get the full shloka.\n"
        "👉 Press '5a' (or any chapter + 'a') for a shloka with audio.\n"
        "👉 Press 'n', 'n1', 'n2', ... to get the next shlokas."
    )

def fetch_text_data(url):
    """Fetches text data from the GitHub repository"""
    response = requests.get(url)
    return response.text.splitlines() if response.status_code == 200 else []

hindi_without_uvacha = fetch_text_data(HINDI_WITHOUT_UVACHA_URL)
telugu_without_uvacha = fetch_text_data(TELUGU_WITHOUT_UVACHA_URL)
hindi_with_uvacha = fetch_text_data(HINDI_WITH_UVACHA_URL)
telugu_with_uvacha = fetch_text_data(TELUGU_WITH_UVACHA_URL)

def get_random_shloka(chapter=None, with_audio=False):
    """Returns a random shloka and its metadata"""
    if chapter:
        hindi_shlokas = [line for line in hindi_without_uvacha if line.startswith(f"{chapter}.")]
        telugu_shlokas = [line for line in telugu_without_uvacha if line.startswith(f"{chapter}.")]
    else:
        hindi_shlokas = hindi_without_uvacha
        telugu_shlokas = telugu_without_uvacha

    if not hindi_shlokas or not telugu_shlokas:
        return None, None, None

    selected_shloka = random.choice(hindi_shlokas)
    chapter, verse = selected_shloka.split(".", 1)[0], selected_shloka.split(".", 1)[1].split()[0]

    audio_file_name = f"{chapter}.{verse}.mp3"
    audio_url = f"{AUDIO_QUARTER_URL}{audio_file_name}" if with_audio else None

    if with_audio and requests.head(audio_url).status_code != 200:
        audio_url = None  # Disable audio if file not found

    return selected_shloka, hindi_shlokas, telugu_shlokas, audio_url

async def handle_message(update: Update, context: CallbackContext) -> None:
    """Handles user messages and fetches appropriate shlokas"""
    user_id = update.message.chat_id
    user_input = update.message.text.strip().lower()

    if user_id not in user_sessions:
        user_sessions[user_id] = {"history": []}  # Initialize session

    if user_input.isdigit():  
        chapter = int(user_input)
        shloka, _, _, audio_url = get_random_shloka(chapter)
        if shloka:
            user_sessions[user_id]["history"].append(shloka)
            await update.message.reply_text(f"📜 {shloka}")
            if audio_url:
                await update.message.reply_audio(audio=audio_url)

    elif user_input == "s":  
        if user_sessions[user_id]["history"]:
            last_shloka = user_sessions[user_id]["history"][-1]
            chapter, verse = last_shloka.split(".", 1)[0], last_shloka.split(".", 1)[1].split()[0]
            full_hindi = next((line for line in hindi_with_uvacha if line.startswith(f"{chapter}.{verse}")), None)
            full_telugu = next((line for line in telugu_with_uvacha if line.startswith(f"{chapter}.{verse}")), None)
            response = f"🇮🇳 Hindi:\n{full_hindi}\n\n🇮🇳 Telugu:\n{full_telugu}"
            await update.message.reply_text(response)

    elif user_input.endswith("a") and user_input[:-1].isdigit():  
        chapter = int(user_input[:-1])
        shloka, _, _, audio_url = get_random_shloka(chapter, with_audio=True)
        if shloka:
            user_sessions[user_id]["history"].append(shloka)
            await update.message.reply_text(f"📜 {shloka}")
            if audio_url:
                await update.message.reply_audio(audio=audio_url)

    elif user_input.startswith("n"):  
        num_shlokas = int(user_input[1:]) if len(user_input) > 1 else 1
        if user_sessions[user_id]["history"]:
            last_shloka = user_sessions[user_id]["history"][-1]
            chapter, verse = map(int, last_shloka.split(".", 1)[0:2])
            response = ""
            for _ in range(num_shlokas):
                verse += 1
                next_shloka = next((line for line in hindi_without_uvacha if line.startswith(f"{chapter}.{verse}")), None)
                if next_shloka:
                    user_sessions[user_id]["history"].append(next_shloka)
                    response += f"📜 {next_shloka}\n\n"
            if response:
                await update.message.reply_text(response)

async def error_handler(update: Update, context: CallbackContext) -> None:
    """Handles any unexpected errors"""
    print(f"⚠️ Exception: {context.error}")

def main():
    """Starts the bot"""
    app = Application.builder().token(TOKEN).build()

    app.add_handler(CommandHandler("start", start))
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))
    app.add_error_handler(error_handler)

    print("🤖 Bot is running...")
    app.run_polling()

if __name__ == "__main__":
    main()
