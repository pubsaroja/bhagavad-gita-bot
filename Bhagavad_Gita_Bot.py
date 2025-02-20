import os
import random
import requests
import subprocess
from telegram import Update
from telegram.ext import Application, MessageHandler, filters, CallbackContext

# Telegram Bot Token & Webhook URL
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")

# Bhagavad Gita File URLs
HINDI_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20with%20Uvacha.txt"
HINDI_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20without%20Uvacha.txt"
TELUGU_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20Without%20Uvacha.txt"

AUDIO_QUARTER_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioQuarter/"
AUDIO_FULL_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioFull/"

# Function to download and convert MP3 to OGG (for autoplay)
def download_and_convert_audio(mp3_url):
    mp3_path = "audio.mp3"
    ogg_path = "audio.ogg"

    try:
        # Download MP3 file
        response = requests.get(mp3_url, stream=True)
        if response.status_code == 200:
            with open(mp3_path, "wb") as file:
                file.write(response.content)
            print("✅ MP3 file downloaded.")

            # Convert MP3 to OGG (Opus format for autoplay)
            subprocess.run(
                ["ffmpeg", "-i", mp3_path, "-c:a", "libopus", "-b:a", "64k", ogg_path, "-y"],
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
            )
            print("✅ Conversion to OGG completed.")
            return ogg_path

        else:
            print(f"⚠️ Failed to download audio: {mp3_url}")
            return None

    except Exception as e:
        print(f"⚠️ Error: {e}")
        return None

# Function to get a random shloka and audio
def get_random_shloka(chapter: str):
    chapter = chapter.strip()

    # Choose the correct audio folder
    audio_url = AUDIO_FULL_URL if chapter == "0" else AUDIO_QUARTER_URL

    # Pick a random verse (assuming 1-20)
    verse = random.randint(1, 20)
    audio_file_name = f"{chapter}.{verse}.mp3"
    audio_link = f"{audio_url}{audio_file_name}"

    return f"Chapter {chapter}, Verse {verse}", audio_link

# Message handler
async def handle_message(update: Update, context: CallbackContext):
    user_text = update.message.text.strip()

    if user_text.isdigit():
        response, audio_url = get_random_shloka(user_text)
    else:
        response, audio_url = "❌ Invalid input. Enter a number (1-18) or '0' for a random shloka.", None

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

    print("✅ Bot is running!")
    app.run_polling()

if __name__ == "__main__":
    main()
