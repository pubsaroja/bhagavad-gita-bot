# ─── app.py ──────────────────────────────────────────────────────────────
from flask import Flask, request, jsonify
from flask_cors import CORS
import json, random, re, os, sys

app = Flask(__name__)
CORS(app)

# ----------------------------------------------------------------------
# Load the audio index
# ----------------------------------------------------------------------
try:
    with open("gita_audio_index.json", encoding="utf-8") as f:
        full_index = json.load(f)
except FileNotFoundError:
    print("❌  gita_audio_index.json not found – container will exit.", file=sys.stderr)
    sys.exit(1)

if not full_index:
    print("❌  gita_audio_index.json is empty – container will exit.", file=sys.stderr)
    sys.exit(1)

# Tag each entry with quarter number 1‑4  (…/27.3.mp3 → 3)
def quarter_num(entry):
    m = re.search(r"/([1-4])\\.mp3$", entry["quarter"])
    return int(m.group(1)) if m else 1

for e in full_index:
    e["qnum"] = quarter_num(e)

quarter_13 = [e for e in full_index if e["qnum"] in (1, 3)]
full_lookup = { (e["chapter"], e["verse"]): e for e in full_index }

def find_entry(ch, vs):
    return full_lookup.get((ch, vs))

# ----------------------------------------------------------------------
# Webhook
# ----------------------------------------------------------------------
@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json(force=True)
    intent = req["queryResult"]["intent"]["displayName"]
    ctx = {c["name"].split("/")[-1]: c for c in
           req["queryResult"].get("outputContexts", [])}.get("lastshloka", {})
    last = ctx.get("parameters", {})

    if intent == "ZeroIntent":
        entry = random.choice(quarter_13)

    elif intent == "ChapterIntent":
        chap = int(req["queryResult"]["parameters"].get("chapter", 1))
        cand = [e for e in quarter_13 if e["chapter"] == chap] or quarter_13
        entry = random.choice(cand)

    elif intent == "FullIntent":
        chap = int(last.get("chapter", 1)); verse = int(last.get("verse", 1))
        entry = find_entry(chap, verse) or random.choice(full_index)
        return reply(entry, entry["full"])            # full audio

    elif intent == "NextIntent":
        chap = int(last.get("chapter", 1)); verse = int(last.get("verse", 1)) + 1
        nxt = find_entry(chap, verse)
        if not nxt:                                   # wrap to next chapter
            chap = chap + 1 if chap < 18 else 1
            verse = 1
            nxt = find_entry(chap, verse)
        entry = nxt or random.choice(full_index)
        return reply(entry, entry["full"])            # full audio

    else:
        return jsonify({"fulfillmentText": "Sorry, I didn’t understand."})

    # default → quarter (1 or 3)
    return reply(entry, entry["quarter"])


def reply(entry, audio_url):
    text = f"Chapter {entry['chapter']}, Verse {entry['verse']}"
    return jsonify({
        "fulfillmentText": text,
        "payload": {
            "google": {
                "expectUserResponse": True,
                "richResponse": {
                    "items": [
                        {"simpleResponse": {"textToSpeech": text}},
                        {"mediaResponse": {
                            "mediaType": "AUDIO",
                            "mediaObjects": [{"name": text, "contentUrl": audio_url}]
                        }}
                    ]
                }
            }
        },
        "outputContexts": [{
            "name": f"{request.json['session']}/contexts/lastshloka",
            "lifespanCount": 5,
            "parameters": {"chapter": entry["chapter"], "verse": entry["verse"]}
        }]
    })

# ----------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------
if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
