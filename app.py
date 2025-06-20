# app.py  (full replacement)

from flask import Flask, request, jsonify
from flask_cors import CORS
import json, random, re, os

app = Flask(__name__)
CORS(app)

# ----------------------------------------------------------------------
# Load index and split out quarter/full lists
# ----------------------------------------------------------------------
with open("gita_audio_index.json", encoding="utf-8") as f:
    full_index = json.load(f)

# Tag each entry with quarter_num (1‑4)
def quarter_num(entry):
    # Path looks like ".../Chapter 5/27.3.mp3"  -> quarter is ".3"
    match = re.search(r"\\.([1-4])\\.mp3$", entry["quarter"])
    return int(match.group(1)) if match else 1

for e in full_index:
    e["qnum"] = quarter_num(e)

quarter_13 = [e for e in full_index if e["qnum"] in (1, 3)]
full_only  = { (e["chapter"], e["verse"]): e for e in full_index }  # quick lookup

def find_entry(ch, vs):
    return full_only.get((ch, vs))

# ----------------------------------------------------------------------
# Webhook
# ----------------------------------------------------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json(force=True)
    intent = req["queryResult"]["intent"]["displayName"]
    ctx_map = {c["name"].split("/")[-1]: c for c in req["queryResult"].get("outputContexts", [])}
    last = ctx_map.get("lastshloka", {}).get("parameters", {})

    # ------------------------------------------------------------------
    # ZeroIntent  → random quarter (1 or 3)
    # ------------------------------------------------------------------
    if intent == "ZeroIntent":
        entry = random.choice(quarter_13)

    # ------------------------------------------------------------------
    # ChapterIntent  → random verse (quarter 1 or 3) inside that chapter
    # ------------------------------------------------------------------
    elif intent == "ChapterIntent":
        chap = int(req["queryResult"]["parameters"].get("chapter", 1))
        opts = [e for e in quarter_13 if e["chapter"] == chap] or quarter_13
        entry = random.choice(opts)

    # ------------------------------------------------------------------
    # FullIntent  → full audio (same chapter/verse as last_ctx)
    # ------------------------------------------------------------------
    elif intent == "FullIntent":
        chap = int(last.get("chapter", 1)); verse = int(last.get("verse", 1))
        entry = find_entry(chap, verse) or random.choice(full_index)
        return reply(entry, entry["full"])          # full audio

    # ------------------------------------------------------------------
    # NextIntent  → next verse FULL audio
    # ------------------------------------------------------------------
    elif intent == "NextIntent":
        chap = int(last.get("chapter", 1)); verse = int(last.get("verse", 1)) + 1
        nxt = find_entry(chap, verse)
        if not nxt:                                # wrap to next chapter
            chap = chap + 1 if chap < 18 else 1
            verse = 1
            nxt = find_entry(chap, verse)
        entry = nxt or random.choice(full_index)
        return reply(entry, entry["full"])          # full audio

    else:
        return jsonify({"fulfillmentText": "Sorry, I didn’t understand."})

    # default path (quarter audio)
    return reply(entry, entry["quarter"])


def reply(entry, audio_url):
    text = f"Chapter {entry['chapter']}, Verse {entry['verse']}"
    # --- Dialogflow‑compatible response ---
    return jsonify({
        "fulfillmentText": text,
        "payload": {
            "google": {
                "expectUserResponse": True,
                "richResponse": {
                    "items": [
                        { "simpleResponse": { "textToSpeech": text } },
                        { "mediaResponse": {
                              "mediaType": "AUDIO",
                              "mediaObjects": [{ "name": text, "contentUrl": audio_url }]
                          }}
                    ]
                }
            }
        },
        "outputContexts": [{
            "name": f\"{request.json['session']}/contexts/lastshloka\",
            "lifespanCount": 5,
            "parameters": {
                "chapter": entry["chapter"],
                "verse": entry["verse"]
            }}]
    })

if __name__ == "__main__":
    port = int(os.getenv("PORT", 8080))
    app.run(host=\"0.0.0.0\", port=port)
