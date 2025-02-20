import random
from telegram import Update
from telegram.ext import Updater, CallbackContext, MessageHandler, Filters
import requests

# URLs for fetching shlokas
HINDI_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20with%20Uvacha.txt"

# Load shlokas into memory
def load_shlokas(url):
    response = requests.get(url)
    return response.text.split("\n\n") if response.status_code == 200 else []

hindi_shlokas = load_shlokas(HINDI_WITH_UVACHA_URL)
telugu_shlokas = load_shlokas(TELUGU_WITH_UVACHA_URL)

# Dictionary to store user last sent shloka
user_last_shloka = {}

# Function to send a shloka
def send_shloka(update: Update, context: CallbackContext, chapter=None):
    chat_id = update.message.chat_id
    
    if chapter is None:
        shloka_hindi = random.choice(hindi_shlokas)
        shloka_telugu = random.choice(telugu_shlokas)
    else:
        filtered_hindi = [s for s in hindi_shlokas if s.startswith(f"{chapter}.")]
        filtered_telugu = [s for s in telugu_shlokas if s.startswith(f"{chapter}.")]
        
        if not filtered_hindi or not filtered_telugu:
            update.message.reply_text("No shlokas found for this chapter.")
            return
        
        shloka_hindi = random.choice(filtered_hindi)
        shloka_telugu = random.choice(filtered_telugu)
    
    response = f"*Hindi:*\n{shloka_hindi}\n\n*Telugu:*\n{shloka_telugu}"
    update.message.reply_text(response, parse_mode='Markdown')
    
    # Store last sent shloka
    shloka_number = shloka_hindi.split("\n")[0]  # Extract verse number
    user_last_shloka[chat_id] = shloka_number

# Function to get the next shloka
def get_next_shloka(update: Update, context: CallbackContext, count=1):
    chat_id = update.message.chat_id
    if chat_id not in user_last_shloka:
        update.message.reply_text("Send a shloka first using a chapter number.")
        return
    
    last_shloka = user_last_shloka[chat_id]
    chapter, verse = map(int, last_shloka.split("."))
    
    next_shlokas_hindi = []
    next_shlokas_telugu = []
    
    for _ in range(count):
        verse += 1
        next_hindi = next((s for s in hindi_shlokas if s.startswith(f"{chapter}.{verse}")), None)
        next_telugu = next((s for s in telugu_shlokas if s.startswith(f"{chapter}.{verse}")), None)
        
        if not next_hindi or not next_telugu:
            chapter += 1  # Move to next chapter
            verse = 1
            next_hindi = next((s for s in hindi_shlokas if s.startswith(f"{chapter}.{verse}")), None)
            next_telugu = next((s for s in telugu_shlokas if s.startswith(f"{chapter}.{verse}")), None)
            
            if not next_hindi or not next_telugu:
                update.message.reply_text("End of Bhagavad Gita reached.")
                return
        
        next_shlokas_hindi.append(next_hindi)
        next_shlokas_telugu.append(next_telugu)
    
    response = "\n\n".join([f"*Hindi:*\n{h}\n\n*Telugu:*\n{t}" for h, t in zip(next_shlokas_hindi, next_shlokas_telugu)])
    update.message.reply_text(response, parse_mode='Markdown')
    
    user_last_shloka[chat_id] = f"{chapter}.{verse}"  # Update last shloka

# Command handler
def handle_message(update: Update, context: CallbackContext):
    text = update.message.text.strip().lower()
    
    if text.isdigit() and 0 <= int(text) <= 18:
        send_shloka(update, context, chapter=int(text) if text != "0" else None)
    elif text in ["n", "n1", "n2", "n3", "n4", "n5"]:
        get_next_shloka(update, context, count=int(text[1:]) if text != "n" else 1)
    else:
        update.message.reply_text("Invalid command. Send a number (1-18) to get a shloka, or 'n' for next shloka up to 'n5'.")

# Main function
def main():
    updater = Updater("YOUR_TELEGRAM_BOT_TOKEN", use_context=True)
    dp = updater.dispatcher
    dp.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))
    updater.start_polling()
    updater.idle()

if __name__ == "__main__":
    main()
