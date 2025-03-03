import os
import random
import requests
import logging
import json
import base64
from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, CallbackContext

# Configure logging
logging.basicConfig(format="%(asctime)s - %(levelname)s - %(message)s", level=logging.INFO)
logger = logging.getLogger(__name__)

# Bot Token & Webhook URL from environment variables
TOKEN = os.getenv("TELEGRAM_BOT_TOKEN")
WEBHOOK_URL = os.getenv("WEBHOOK_URL")
GITHUB_TOKEN = os.getenv("GITHUB_TOKEN")

if not TOKEN:
    raise ValueError("❌ TELEGRAM_BOT_TOKEN is missing! Set it in the environment variables.")
if not GITHUB_TOKEN:
    logger.warning("❌ GITHUB_TOKEN is missing! Meanings functionality will be unavailable.")

# GitHub repository details
REPO_OWNER = "pubsaroja"
REPO_NAME = "bhagavad-gita-bot"
MEANINGS_FILE = "meanings.txt"  # JSON file with meanings

# File URLs for shloka data
HINDI_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20with%20Uvacha.txt"
ENGLISH_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20English%20with%20Uvacha.txt"
HINDI_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20without%20Uvacha.txt"
TELUGU_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20Without%20Uvacha.txt"
ENGLISH_WITHOUT_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20English%20without%20Uvacha.txt"

# Audio URLs
AUDIO_QUARTER_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioQuarter/"
AUDIO_FULL_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioFull/"

# Session data to track user interactions
session_data = {}

# Load shlokas from GitHub
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

# Load all shlokas into memory
shlokas_hindi = load_shlokas_from_github(HINDI_WITHOUT_UVACHA_URL)
shlokas_telugu = load_shlokas_from_github(TELUGU_WITHOUT_UVACHA_URL)
shlokas_english = load_shlokas_from_github(ENGLISH_WITHOUT_UVACHA_URL)
full_shlokas_hindi = load_shlokas_from_github(HINDI_WITH_UVACHA_URL)
full_shlokas_telugu = load_shlokas_from_github(TELUGU_WITH_UVACHA_URL)
full_shlokas_english = load_shlokas_from_github(ENGLISH_WITH_UVACHA_URL)

# Fetch meanings file from GitHub
def fetch_meanings_file():
    if not GITHUB_TOKEN:
        logger.error("No GITHUB_TOKEN provided.")
        return None
    url = f"https://api.github.com/repos/{REPO_OWNER}/{REPO_NAME}/contents/{MEANINGS_FILE}"
    headers = {"Authorization": f"token {GITHUB_TOKEN}"}
    try:
        response = requests.get(url, headers=headers, timeout=10)
        response.raise_for_status()
        json_response = response.json()
        logger.info(f"GitHub API response: {json.dumps(json_response, indent=2)}")
        if "content" not in json_response:
            logger.error(f"Unexpected GitHub API response: 'content' field missing.")
            return None
        content = base64.b64decode(json_response["content"]).decode("utf-8")
        if not content.strip():
            logger.error("Fetched meanings.txt is empty.")
            return None
        logger.info(f"Raw meanings.txt content: {content[:100]}...")  # Log first 100 chars
        return json.loads(content)
    except requests.RequestException as e:
        logger.error(f"Failed to fetch {MEANINGS_FILE} from GitHub: {str(e)}")
        return None
    except json.JSONDecodeError as e:
        logger.error(f"Failed to parse meanings.txt as JSON: {str(e)}")
        return None

# Get meaning of a shloka
def get_meaning(shloka_id):
    meanings = fetch_meanings_file()
    if meanings is None:
        return "❌ Could not fetch meanings. Check GitHub token or meanings.txt file."
    if shloka_id in meanings:
        data = meanings[shloka_id]
        word_meanings = "\n".join([f"{word}: {meaning}" for word, meaning in data["ప్రతిపదార్థం"].items()]) if data["ప్రతిపదార్థం"] else "No word meanings available."
        translation = data["అర్థము"]
        return f"Word Meanings:\n{word_meanings}\n\nTranslation:\n{translation}"
    return f"Meaning for Shloka {shloka_id} not found in meanings.txt."

# Search for shlokas starting with a specific letter or syllable
def search_shlokas(starting_with, max_results=10):
    results = []
    for chapter, shlokas in full_shlokas_telugu.items():
        for verse, text in shlokas:
            if text.strip().startswith(starting_with):
                first_quarter = text.split('\n')[0]
                results.append((chapter, verse, first_quarter))
                if len(results) >= max_results:
                    return results
    return results

# Map Latin letters to Telugu syllables
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

# Get a random shloka from a chapter
def get_random_shloka(chapter: str, user_id: int, with_audio: bool = False, audio_only: bool = False):
    if user_id not in session_data:
        session_data[user_id] = {"used_shlokas": {}, "last_chapter": None, "last_index": None, "search_results": []}
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
    text = f"{chapter}.{verse}\nTelugu:\n{shloka_telugu}\n\nHindi:\n{
