import os
import random
import requests
import ffmpeg
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Bot Token & Webhook URL
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# File URLs
HINDI_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20with%20Uvacha.txt"
HINDI_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20without%20Uvacha.txt"
TELUGU_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20Without%20Uvacha.txt"

AUDIO_QUARTER_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioQuarter/"
AUDIO_FULL_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioFull/"

# Session data to track shown shlokas
session_data = {}

# Function to download and convert audio for autoplay
def download_and_convert_audio(mp3_url):
    mp3_path = "temp_audio.mp3"
    ogg_path = "temp_audio.ogg"

    response = requests.get(mp3_url)
    if response.status_code == 200:
        with open(mp3_path, "wb") as file:
            file.write(response.content)

        # Convert MP3 to OGG (Opus codec) for autoplay
        ffmpeg.input(mp3_path).output(ogg_path, codec="libopus", audio_bitrate="64k").run(overwrite_output=True)

        return ogg_path  # Return OGG file path
    else:
        print(f"⚠️ Failed to download {mp3_url}")
        return None

# Function to get a random shloka and audio
def get_random_shloka(chapter: str, user_id: int):
    global session_data

    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": set(), "last_shloka_index": None, "last_chapter": None}

    chapter = str(chapter).strip()

    if chapter == "0":
        audio_url = AUDIO_FULL_URL
    else:
        audio_url = AUDIO_QUARTER_URL

    verse = random.randint(1, 20)  # Assuming up to 20 verses per chapter
    audio_file_name = f"{chapter}.{verse}.mp3"
    audio_link = f"{audio_url}{audio_file_name}"

    return f"Chapter {chapter}, Verse {verse}", audio_link

# Handler function for messages
async def handle_message(update: Update, context: CallbackContext):
    user_text = update.message.text.strip()
    user_id = update.message.from_user.id

    if user_text.isdigit():
        response, audio_url = get_random_shloka(user_text, user_id)
    else:
        response, audio_url = "❌ Invalid input. Enter a chapter number (1-18) or '0' for a random shloka.", None

    await update.message.reply_text(response)

    if audio_url:
        ogg_file = download_and_convert_audio(audio_url)
        if ogg_file:
            await update.message.reply_voice(voice=open(ogg_file, "rb"))
            os.remove(ogg_file)  # Clean up temp file

# Main function
def main():
    app = Application.builder().token(TOKEN).build()
    app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    app.run_polling()

if __name__ == "__main__":
    main()
