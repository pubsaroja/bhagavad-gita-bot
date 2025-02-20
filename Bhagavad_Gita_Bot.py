import os
import logging
from flask import Flask, request
import telegram
from telegram.ext import Updater, CommandHandler, MessageHandler, Filters, Dispatcher

# Load environment variables
TOKEN = os.getenv("BOT_TOKEN")  # Make sure Railway has this environment variable set
APP_URL = os.getenv("APP_URL")  # Example: https://bhagavad-gita-bot-production.up.railway.app

# Initialize Flask app
app = Flask(__name__)

# Setup Telegram bot
bot = telegram.Bot(token=TOKEN)

# Configure logging
logging.basicConfig(level=logging.INFO)

# Initialize dispatcher
dispatcher = Dispatcher(bot, None, use_context=True)

# Define /start command
def start(update, context):
    update.message.reply_text("Namaste! 🙏 Welcome to the Bhagavad Gita bot!")

# Handle text messages
def handle_message(update, context):
    text = update.message.text
    update.message.reply_text(f"You said: {text}")

# Add handlers
dispatcher.add_handler(CommandHandler("start", start))
dispatcher.add_handler(MessageHandler(Filters.text & ~Filters.command, handle_message))

# Webhook route
@app.route(f'/{TOKEN}', methods=['POST'])
def webhook():
    update = telegram.Update.de_json(request.get_json(), bot)
    dispatcher.process_update(update)
    return "OK", 200

# Set webhook
def set_webhook():
    webhook_url = f"{APP_URL}/{TOKEN}"
    bot.setWebhook(webhook_url)
    logging.info(f"Webhook set to {webhook_url}")

# Run Flask app
if __name__ == "__main__":
    set_webhook()  # Set webhook when the bot starts
    app.run(host="0.0.0.0", port=8080)  # Railway uses port 8080
