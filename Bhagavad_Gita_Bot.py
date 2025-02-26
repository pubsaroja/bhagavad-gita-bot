# File URLs (already correct, just confirming)
HINDI_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Hindi%20with%20Uvacha.txt"
TELUGU_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/refs/heads/main/BG%20Telugu%20with%20Uvacha.txt"
ENGLISH_WITH_UVACHA_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/BG%20English%20with%20Uvacha.txt"

# Audio URL - Switch to AudioFull for full audio clips
AUDIO_FULL_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioFull/"

# Load full shlokas (already correct, loaded from "with Uvacha" files)
full_shlokas_hindi = load_shlokas_from_github(HINDI_WITH_UVACHA_URL)
full_shlokas_telugu = load_shlokas_from_github(TELUGU_WITH_UVACHA_URL)
full_shlokas_english = load_shlokas_from_github(ENGLISH_WITH_UVACHA_URL)

# Update get_random_shloka to use full shlokas and full audio
def get_random_shloka(chapter: str, user_id: int, with_audio: bool = False, audio_only: bool = False):
    chapter = str(chapter).strip()
    if chapter == "0":
        chapter = random.choice(list(full_shlokas_hindi.keys()))
    if chapter not in full_shlokas_hindi:
        return "❌ Invalid chapter number. Please enter a number between 0-18.", None
    # Logic for random selection (unchanged)
    shloka_index = random.choice(available_shlokas)
    verse, shloka_hindi = full_shlokas_hindi[chapter][shloka_index]  # Full version
    _, shloka_telugu = full_shlokas_telugu[chapter][shloka_index]
    _, shloka_english = full_shlokas_english[chapter][shloka_index]
    audio_file_name = f"{chapter}.{int(verse)}.mp3"
    audio_link = f"{AUDIO_FULL_URL}{audio_file_name}" if with_audio else None  # Use AudioFull
    text = (f"{chapter}.{verse}\n"
            f"Telugu:\n{shloka_telugu}\n\n"
            f"Hindi:\n{shloka_hindi}\n\n"
            f"English:\n{shloka_english}") if not audio_only else None
    return text, audio_link

# Update get_specific_shloka (already using full shlokas, just fix audio)
def get_specific_shloka(chapter: str, verse: str, user_id: int, with_audio: bool = False, audio_only: bool = False):
    chapter = str(chapter)
    verse = str(verse)
    for idx, (v, _) in enumerate(full_shlokas_hindi[chapter]):
        if v == verse:
            verse_text, shloka_hindi = full_shlokas_hindi[chapter][idx]  # Full version
            _, shloka_telugu = full_shlokas_telugu[chapter][idx]
            _, shloka_english = full_shlokas_english[chapter][idx]
            audio_file_name = f"{chapter}.{int(verse)}.mp3"
            audio_link = f"{AUDIO_FULL_URL}{audio_file_name}" if with_audio else None  # Use AudioFull
            text = (f"{chapter}.{verse}\n"
                    f"Telugu:\n{shloka_telugu}\n\n"
                    f"Hindi:\n{shloka_hindi}\n\n"
                    f"English:\n{shloka_english}") if not audio_only else None
            return text, audio_link
    return f"❌ Shloka {chapter}.{verse} not found!", None

# Similar updates for get_shloka and get_last_shloka (use AUDIO_FULL_URL)
