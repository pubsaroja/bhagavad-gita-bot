import os
import json
from pathlib import Path

# ✅ Adjust path to your folder location
base_path = Path(r"C:\Users\91990\My Drive (dr.p.udayabhaskar@gmail.com)\Gita\GitHub\bhagavad-gita-bot")

quarter_base_url = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioQuarterAll"
full_base_url = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/AudioFull"

quarter_path = base_path / "AudioQuarterAll"
entries = []

for chapter_folder in quarter_path.glob("Chapter *"):
    ch = int(chapter_folder.name.split(" ")[1])
    for mp3_file in chapter_folder.glob("*.mp3"):
        name = mp3_file.stem  # e.g., 1.1
        parts = name.split(".")
        if len(parts) != 2:
            continue
        ch_num, verse_num = parts
        try:
            ch_num = int(ch_num)
            verse_num = int(verse_num)
        except ValueError:
            continue

        # We'll mark this as quarter=1 or 3, alternating
        # or randomly mark all as quarter 1 for safety
        assumed_quarter = 1 if verse_num % 2 != 0 else 3

        quarter_url = f"{quarter_base_url}/Chapter {ch}/{name}.mp3"
        full_url = f"{full_base_url}/{ch}.{verse_num}.mp3"

        entries.append({
            "chapter": ch,
            "verse": verse_num,
            "quarter_part": assumed_quarter,
            "quarter": quarter_url,
            "full": full_url
        })

# Save it
output_path = base_path / "gita_audio_index.json"
with output_path.open("w", encoding="utf-8") as f:
    json.dump(entries, f, indent=2)

print(f"✅ Saved gita_audio_index.json with {len(entries)} entries.")
