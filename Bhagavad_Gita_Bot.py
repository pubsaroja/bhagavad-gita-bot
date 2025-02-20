import os
import logging
import json
from flask import Flask, request
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, CallbackContext, filters

TOKEN = os.getenv("BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")  # Set this in Railway

app = Flask(__name__)

# Setup logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Initialize Telegram Bot
tg_app = Application.builder().token(TOKEN).build()

# ---------------------------- Handlers ----------------------------

async def start(update: Update, context: CallbackContext):
    """Handles the /start command."""
    await update.message.reply_text("Welcome to Bhagavad Gita Bot! Choose a chapter.")

async def handle_message(update: Update, context: CallbackContext):
    """Handles incoming messages."""
    text = update.message.text
    chat_id = update.message.chat_id
    await update.message.reply_text(f"You said: {text}")  # Replace with Gita logic

# ---------------------------- Webhook Handling ----------------------------

@app.route(f"/{TOKEN}", methods=["POST"])
def webhook():
    """Handles incoming updates from Telegram."""
    try:
        update = Update.de_json(request.get_json(force=True), tg_app.bot)
        tg_app.update_queue.put_nowait(update)
        return "OK", 200
    except Exception as e:
        logger.error(f"Error handling webhook: {str(e)}")
        return "Error", 500

# ---------------------------- Bot Initialization ----------------------------

def main():
    """Start the bot with webhook."""
    logger.info("Starting bot...")

    # Add command handlers
    tg_app.add_handler(CommandHandler("start", start))
    tg_app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, handle_message))

    # Set webhook
    tg_app.run_webhook(
        listen="0.0.0.0",
        port=int(os.getenv("PORT", 8080)),
        webhook_url=f"{WEBHOOK_URL}/{TOKEN}"
    )

if __name__ == "__main__":
    main()
