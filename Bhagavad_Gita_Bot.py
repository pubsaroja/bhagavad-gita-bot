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
        if not line or line == "---":  # Skip empty lines or separators if any
            continue
        # Split line into term, translation, and verse
        try:
            if "=" in line and "||" in line:
                term_part, verse_part = line.rsplit("||", 1)
                term, translation = term_part.split("=", 1)
                term = term.strip().lower()
                translation = translation.strip()
                verse = verse_part.strip("()")
                if term not in word_index:
                    word_index[term] = []
                word_index[term].append((verse, translation))
        except ValueError as e:
            logger.warning(f"Skipping malformed line: {line} - {str(e)}")
    return word_index

word_index = load_word_index()

# Search word occurrences
def search_word_occurrences(term):
    term = term.lower()
    if term in word_index:
        occurrences = word_index[term]
        response = f"Found '{term}' in {len(occurrences)} verse(s):\n\n"
        for verse, translation in occurrences:
            response += f"Verse {verse}:\n"
            response += f"Sanskrit: {term}\n"
            response += f"Translation: {translation}\n\n"
        return response
    return f"No occurrences found for '{term}'."

# Search shlokas
def search_shlokas(starting_with, max_results=10, offset=0):
    results = []
    for chapter, shlokas in full_shlokas_telugu.items():
        for verse, text in shlokas:
            if text.strip().startswith(starting_with):
                first_quarter = text.split('\n')[0]
                results.append((chapter, verse, first_quarter))
    total_results = len(results)
    if max_results == -1:
        return results[offset:], total_results
    return results[offset:offset + max_results], total_results

SYLLABLE_MAP = {
    'a': 'అ', 'aa': 'ఆ', 'i': 'ఇ', 'ii': 'ఈ', 'u': 'ఉ', 'uu': 'ఊ',
    'e': 'ఎ', 'ee': 'ఏ', 'ai': 'ఐ', 'o': 'ఒ', 'oo': 'ఓ', 'au': 'ఔ',
    'ka': 'క', 'kha': 'ఖ', 'ga': 'గ', 'gha': 'ఘ', 'nga': 'ఙ',
    'cha': 'చ', 'chha': 'ఛ', 'ja': 'జ', 'jha': 'ఝ', 'nya': 'ఞ',
    'ta': 'ట', 'tha': 'ఠ', 'da': 'డ', 'dha': 'ఢ', 'na': 'ణ',
    'tha': 'త', 'thha': 'థ', 'da': 'ద', 'dha': 'ధ', 'na': 'న',
    'pa': 'ప', 'pha': 'ఫ', 'ba': 'బ', 'bha': 'భ', 'ma': 'మ',
    'ya': 'య', 'ra': 'ర', 'la': 'ల', 'va': 'వ', 'sha': 'శ',
    'ssa': 'ష', 'sa': 'స', 'ha': 'హ'
}

# Helper functions for chapter navigation
def get_previous_chapter(chapter):
    return "18" if chapter == "1" else str(int(chapter) - 1)

def get_next_chapter(chapter):
    return "1" if chapter == "18" else str(int(chapter) + 1)

def get_shloka_at_offset(current_chapter, current_idx, offset):
    chapter = current_chapter
    idx = current_idx + offset
    while idx < 0:
        prev_chapter = get_previous_chapter(chapter)
        num_shlokas_prev = len(full_shlokas_hindi[prev_chapter])
        idx += num_shlokas_prev
        chapter = prev_chapter
    while idx >= len(full_shlokas_hindi[chapter]):
        next_chapter = get_next_chapter(chapter)
        idx -= len(full_shlokas_hindi[chapter])
        chapter = next_chapter
    return chapter, idx

# Get a specific shloka by chapter and verse index
def get_shloka(chapter: str, verse_idx: int, with_audio: bool = False, audio_only: bool = False, full_audio: bool = False):
    chapter = str(chapter)
    if chapter not in full_shlokas_hindi or verse_idx >= len(full_shlokas_hindi[chapter]) or verse_idx < 0:
        logger.warning(f"No shloka found at chapter {chapter}, index {verse_idx}")
        return None, None
    verse, shloka_hindi = full_shlokas_hindi[chapter][verse_idx]
    _, shloka_telugu = full_shlokas_telugu[chapter][verse_idx]
    _, shloka_english = full_shlokas_english[chapter][verse_idx]
    audio_file_name = f"{chapter}.{int(verse)}.mp3"
    audio_url = AUDIO_FULL_URL if full_audio else AUDIO_QUARTER_URL
    audio_link = f"{audio_url}{audio_file_name}" if (with_audio or audio_only) else None
    text = f"{chapter}.{verse}\nTelugu:\n{shloka_telugu}\n\nHindi:\n{shloka_hindi}\n\nEnglish:\n{shloka_english}" if not audio_only else None
    logger.info(f"Retrieved shloka {chapter}.{verse}, audio: {audio_link}")
    return text, audio_link

# Get a random shloka
def get_random_shloka(chapter: str, user_id: int, with_audio: bool = False, audio_only: bool = False):
    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": {}, "last_chapter": None, "last_index": None, "search_results": [], "search_state": {}}
    chapter = str(chapter).strip()
    if chapter == "0":
        chapter = random.choice(list(shlokas_hindi.keys()))
    if chapter not in shlokas_hindi:
        return "❌ Invalid chapter number. Please enter a number between 0-18.", None
    if chapter not in session_data[user_id]["used_shlokas"]:
        session_data[user_id]["used_shlokas"][chapter] = set()
    available_shlokas = [i for i in range(len(shlokas_hindi[chapter])) if i not in session_data[user_id]["used_shlokas"][chapter]]
    if not available_shlokas:
        return f"✅ All shlokas from chapter {chapter} have been shown! Try another chapter or /reset.", None
    shloka_index = random.choice(available_shlokas)
    session_data[user_id]["used_shlokas"][chapter].add(shloka_index)
    session_data[user_id]["last_chapter"] = chapter
    session_data[user_id]["last_index"] = shloka_index
    verse, shloka_hindi = shlokas_hindi[chapter][shloka_index]
    _, shloka_telugu = shlokas_telugu[chapter][shloka_index]
    _, shloka_english = shlokas_english[chapter][shloka_index]
    audio_file_name = f"{chapter}.{int(verse)}.mp3"
    audio_link = f"{AUDIO_QUARTER_URL}{audio_file_name}" if (with_audio or audio_only) else None
    text = f"{chapter}.{verse}\nTelugu:\n{shloka_telugu}\n\nHindi:\n{shloka_hindi}\n\nEnglish:\n{shloka_english}" if not audio_only else None
    return text, audio_link

# Get a specific shloka by chapter and verse number
def get_specific_shloka(chapter: str, verse: str, user_id: int, with_audio: bool = False, audio_only: bool = False, full_audio: bool = False):
    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": {}, "last_chapter": None, "last_index": None, "search_results": [], "search_state": {}}
    chapter = str(chapter)
    verse = str(verse)
    if chapter not in full_shlokas_hindi:
        return "❌ Invalid chapter number. Please enter a number between 0-18.", None
    for idx, (v, _) in enumerate(full_shlokas_hindi[chapter]):
        if v == verse:
            verse_text, shloka_hindi = full_shlokas_hindi[chapter][idx]
            _, shloka_telugu = full_shlokas_telugu[chapter][idx]
            _, shloka_english = full_shlokas_english[chapter][idx]
            audio_file_name = f"{chapter}.{int(verse)}.mp3"
            audio_link = f"{AUDIO_FULL_URL if full_audio else AUDIO_QUARTER_URL}{audio_file_name}" if (with_audio or audio_only) else None
            session_data[user_id]["last_chapter"] = chapter
            session_data[user_id]["last_index"] = idx
            text = f"{chapter}.{verse}\nTelugu:\n{shloka_telugu}\n\nHindi:\n{shloka_hindi}\n\nEnglish:\n{shloka_english}" if not audio_only else None
            return text, audio_link
    return f"❌ Shloka {chapter}.{verse} not found!", None

# Get the last requested shloka
def get_last_shloka(user_id: int, with_audio: bool = False, audio_only: bool = False, full_audio: bool = False):
    if user_id in session_data and session_data[user_id]["last_index"] is not None:
        chapter = session_data[user_id]["last_chapter"]
        shloka_index = session_data[user_id]["last_index"]
        return get_shloka(chapter, shloka_index, with_audio, audio_only, full_audio)
    return "❌ No previous shloka found. Please request one first!", None

# Main message handler
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
            base_command = original_text[:-2]  # Remove 'ao'
        elif with_audio and not original_text.startswith("w "):  # Only apply 'a' modifier if not a word search
            base_command = original_text[:-1]  # Remove 'a' only if not a syllable or word search

        # Determine if full audio is needed
        full_audio = base_command in ["f", "n1", "n2", "n3", "n4", "n5", "p"] or (with_audio and not original_text.startswith("w "))

        logger.info(f"Base command: {base_command}, audio_only: {audio_only}, with_audio: {with_audio}, full_audio: {full_audio}")

        # Handle word search (e.g., 'w anagha')
        if base_command.startswith("w "):
            term = base_command[2:].strip()
            response = search_word_occurrences(term)
            await update.message.reply_text(response)
            return

        # Handle specific shloka request (e.g., "18.1", "18.1a", "18.1ao")
        if "." in base_command:
            try:
                chapter, verse = base_command.split(".", 1)
                if chapter.isdigit() and verse.isdigit():
                    response, audio_url = get_specific_shloka(chapter, verse, user_id, with_audio, audio_only, full_audio)
                    if not audio_only and response:
                        await update.message.reply_text(response)
                    if audio_url:
                        await update.message.reply_audio(audio_url)
                    return
            except ValueError:
                pass

        # ... (rest of the function remains unchanged)

        # Handle chapter number for random shloka (e.g., "0", "1", "0a", "1ao")
        if base_command.isdigit():
            response, audio_url = get_random_shloka(base_command, user_id, with_audio, audio_only)
            if not audio_only and response:
                await update.message.reply_text(response)
            if audio_url:
                await update.message.reply_audio(audio_url)
            return

        # Handle search requests (e.g., 'a', 'ba')
        if base_command in SYLLABLE_MAP:
            starting_with = SYLLABLE_MAP[base_command]
            results, total_results = search_shlokas(starting_with, max_results=10)
            session_data[user_id]["search_state"] = {
                "starting_with": starting_with,
                "all_results": results + search_shlokas(starting_with, max_results=-1, offset=10)[0],
                "offset": 10
            }
            if results:
                response = f"Found {total_results} shlokas starting with '{starting_with}' (showing first 10):\n"
                for i, (chapter, verse, first_quarter) in enumerate(results, 1):
                    response += f"{i}. {chapter}.{verse}: {first_quarter}\n"
                if total_results > 10:
                    response += "Reply 'more' for the next 10 or 'all' for all remaining shlokas."
                response += "\nOr reply with a number to see the full shloka."
                session_data[user_id]["search_results"] = results
                await update.message.reply_text(response)
            else:
                await update.message.reply_text(f"No shlokas found starting with '{starting_with}'.")
            return

        # Handle 'more' or 'all' for additional search results
        if base_command in ["more", "all"] and "search_state" in session_data.get(user_id, {}):
            search_state = session_data[user_id]["search_state"]
            starting_with = search_state["starting_with"]
            all_results = search_state["all_results"]
            offset = search_state["offset"]
            if base_command == "more":
                results = all_results[offset:offset + 10]
                session_data[user_id]["search_state"]["offset"] += 10
            else:  # 'all'
                results = all_results[offset:]
                session_data[user_id]["search_state"]["offset"] = len(all_results)
            if results:
                response = f"More shlokas starting with '{starting_with}':\n"
                start_index = offset + 1 if base_command == "more" else offset + 1
                for i, (chapter, verse, first_quarter) in enumerate(results, start_index):
                    response += f"{i}. {chapter}.{verse}: {first_quarter}\n"
                if base_command == "more" and session_data[user_id]["search_state"]["offset"] < len(all_results):
                    response += "Reply 'more' for the next 10 or 'all' for all remaining shlokas."
                response += "\nOr reply with a number to see the full shloka."
                session_data[user_id]["search_results"] = results
                await update.message.reply_text(response)
            else:
                await update.message.reply_text(f"No more shlokas found starting with '{starting_with}'.")
            return

        # Handle selection from search results (e.g., '1', '2')
        if base_command.isdigit() and "search_results" in session_data.get(user_id, {}):
            selection = int(base_command) - 1
            results = session_data[user_id]["search_results"]
            if 0 <= selection < len(results):
                chapter, verse, _ = results[selection]
                response, audio_url = get_specific_shloka(chapter, verse, user_id, with_audio, audio_only, full_audio)
                if not audio_only and response:
                    await update.message.reply_text(response)
                if audio_url:
                    await update.message.reply_audio(audio_url)
                session_data[user_id]["search_results"] = []  # Clear results after selection
            else:
                await update.message.reply_text("Invalid selection. Please try again.")
            return

        # Handle word search (e.g., 'w anagha')
        if base_command.startswith("w "):
            term = base_command[2:].strip()
            response = search_word_occurrences(term)
            await update.message.reply_text(response)
            return

        # Handle last shloka (e.g., "f", "fa", "fao")
        if base_command == "f":
            response, audio_url = get_last_shloka(user_id, with_audio, audio_only, full_audio)
            if not audio_only and response:
                await update.message.reply_text(response)
            if audio_url:
                await update.message.reply_audio(audio_url)
            return

        # Handle next shloka (e.g., "n1", "n1a", "n1ao")
        if base_command.startswith("n") and base_command[1:].isdigit():
            if user_id in session_data and session_data[user_id]["last_index"] is not None:
                current_chapter = session_data[user_id]["last_chapter"]
                current_idx = session_data[user_id]["last_index"]
                count = int(base_command[1:])
                responses = []
                audio_urls = []
                last_chapter = current_chapter
                last_idx = current_idx
                for i in range(count):
                    chapter, idx = get_shloka_at_offset(current_chapter, current_idx, i + 1)
                    response, audio_url = get_shloka(chapter, idx, with_audio, audio_only, full_audio)
                    if response or audio_url:
                        responses.append(response)
                        if audio_url:
                            audio_urls.append(audio_url)
                        last_chapter = chapter
                        last_idx = idx
                    else:
                        break  # Stop if no more shlokas are available
                if audio_urls or responses:
                    session_data[user_id]["last_chapter"] = last_chapter
                    session_data[user_id]["last_index"] = last_idx
                    if not audio_only:
                        for response in responses:
                            if response:
                                await update.message.reply_text(response)
                    for audio_url in audio_urls:
                        await update.message.reply_audio(audio_url)
                else:
                    await update.message.reply_text("❌ No next Shloka available!")
            else:
                await update.message.reply_text("❌ Please request a Shloka first!")
            return

        # Handle previous and next shlokas (e.g., "p", "pa", "pao")
        if base_command == "p":
            if user_id in session_data and session_data[user_id]["last_index"] is not None:
                current_chapter = session_data[user_id]["last_chapter"]
                current_idx = session_data[user_id]["last_index"]
                offsets = [-2, -1, 0, 1, 2]
                responses = []
                audio_urls = []
                logger.info(f"Processing 'p' for chapter {current_chapter}, current index {current_idx}")
                for offset in offsets:
                    chapter, idx = get_shloka_at_offset(current_chapter, current_idx, offset)
                    response, audio_url = get_shloka(chapter, idx, with_audio, audio_only, full_audio)
                    if response or audio_url:
                        responses.append(response)
                        if audio_url:
                            audio_urls.append(audio_url)
                            logger.info(f"Audio URL generated for {chapter}.{idx + 1}: {audio_url}")
                    else:
                        logger.warning(f"No data for chapter {chapter}, index {idx}")
                if audio_urls or responses:
                    if not audio_only:
                        for response in responses:
                            if response:
                                await update.message.reply_text(response)
                    for audio_url in audio_urls:
                        await update.message.reply_audio(audio_url)
                else:
                    await update.message.reply_text("❌ No shlokas available in this range!")
            else:
                await update.message.reply_text("❌ Please request a Shloka first!")
            return

        # Handle audio of last shloka (e.g., "o")
        if base_command == "o":
            if user_id in session_data and session_data[user_id]["last_index"] is not None:
                chapter = session_data[user_id]["last_chapter"]
                shloka_index = session_data[user_id]["last_index"]
                verse, _ = full_shlokas_hindi[chapter][shloka_index]
                audio_file_name = f"{chapter}.{int(verse)}.mp3"
                audio_link = f"{AUDIO_QUARTER_URL}{audio_file_name}"
                await update.message.reply_audio(audio_link)
            else:
                await update.message.reply_text("❌ No previous Shloka found. Please request one first!")
            return

        # Handle invalid input
        await update.message.reply_text(
            "❌ Invalid input. Please use:\n"
            "w <term>: Search word occurrences (e.g., 'w anagha')\n"
            "a, ba, etc.: Search shlokas by starting letter\n"
            "more: Next 10 search results\n"
            "all: All remaining search results\n"
            "1-10: Select a shloka from search results\n"
            "0-18: Random Shloka\n"
            "chapter.verse: Specific Shloka (e.g., 18.1)\n"
            "f: Last full Shloka\n"
            "n1-n5: Next Shloka(s) (continues to next chapter if needed)\n"
            "p: Previous 2, current & next 2 Shlokas\n"
            "o: Audio of last Shloka\n"
            "Add 'a' for audio with text (e.g., '1a')\n"
            "Add 'ao' for audio only (e.g., '1ao')\n"
            "Use /reset to start fresh"
        )
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}", exc_info=True)
        await update.message.reply_text("❌ An error occurred.")

# Command handlers
async def start(update: Update, context: CallbackContext):
    logger.info("Bot started with /start command")
    await update.message.reply_text(
        "Jai Gurudatta!\n"
        "Welcome to Srimad Bhagavadgita Bot.\n"
        "w <term> → Search word occurrences (e.g., 'w anagha')\n"
        "a, ba, etc. → Search shlokas by starting letter\n"
        "more → Next 10 search results\n"
        "all → All remaining search results\n"
        "1-10 → Select shloka from search results\n"
        "0-18 → Random Shloka from chapter\n"
        "0a → With audio\n"
        "0ao → Audio only\n"
        "chapter.verse → Specific Shloka (e.g., 18.1)\n"
        "chapter.verse + a → With audio (e.g., 18.1a)\n"
        "chapter.verse + ao → Audio only (e.g., 18.1ao)\n"
        "f → Full last Shloka\n"
        "fa → Full last Shloka with full audio\n"
        "fao → Full last Shloka audio only\n"
        "n1 → Next Shloka (continues to next chapter if needed)\n"
        "n1a → Next with audio\n"
        "n1ao → Next audio only\n"
        "n2-n5 → Multiple next Shlokas\n"
        "p → Previous 2, current & next 2\n"
        "pa → Same with audio\n"
        "pao → Same audio only\n"
        "o → Audio of last Shloka\n"
        "Use /reset to start fresh"
    )

async def reset(update: Update, context: CallbackContext):
    user_id = update.message.from_user.id
    if user_id in session_data:
        del session_data[user_id]
    await update.message.reply_text("✅ Session reset! Start anew with any chapter.")

# Main function
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
