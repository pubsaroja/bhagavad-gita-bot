from flask import Flask, request, jsonify
from flask_cors import CORS
import json, random, os

app = Flask(__name__)
CORS(app)

# Load index
with open("gita_audio_index_deduplicated.json", encoding="utf-8") as f:
    audio_index = json.load(f)

# Only allow 1st and 3rd quarter entries
quarter_13 = [e for e in audio_index if e["quarter_part"] in (1, 3)]

# Map (chapter, verse) → full entry
full_index = {(e["chapter"], e["verse"]): e for e in audio_index}

def find_entry(chapter, verse):
    return full_index.get((chapter, verse))

@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json(force=True)
    intent = req["queryResult"]["intent"]["displayName"]
    ctxs = req["queryResult"].get("outputContexts", [])
    ctx_map = {c["name"].split("/")[-1]: c for c in ctxs}
    last = ctx_map.get("lastshloka", {}).get("parameters", {})

    if intent == "ZeroIntent":
        entry = random.choice(quarter_13)

    elif intent == "ChapterIntent":
        chapter = int(req["queryResult"]["parameters"].get("chapter", 1))
        candidates = [e for e in quarter_13 if e["chapter"] == chapter]
        entry = random.choice(candidates if candidates else quarter_13)

    elif intent == "FullIntent":
        chapter = int(last.get("chapter", 1))
        verse = int(last.get("verse", 1))
        entry = find_entry(chapter, verse)
        if entry:
            return respond(entry, entry["full"])
        else:
            return fallback("Full verse not found.")

    elif intent == "NextIntent":
        chapter = int(last.get("chapter", 1))
        verse = int(last.get("verse", 1)) + 1
        # Wrap to next chapter if needed
        if not find_entry(chapter, verse):
            chapter = 1 if chapter == 18 else chapter + 1
            verse = 1
        entry = find_entry(chapter, verse)
        if entry:
            return respond(entry, entry["full"])
        else:
            return fallback("Next verse not found.")

    else:
        return fallback("Sorry, I didn’t understand.")

    return respond(entry, entry["quarter"])

def respond(entry, audio_url):
    text = f"Chapter {entry['chapter']}, Verse {entry['verse']}"
    return jsonify({
        "fulfillmentText": text,
        "payload": {
            "google": {
                "expectUserResponse": True,
                "richResponse": {
                    "items": [
                        {"simpleResponse": {"textToSpeech": text}},
                        {
                            "mediaResponse": {
                                "mediaType": "AUDIO",
                                "mediaObjects": [
                                    {"name": text, "contentUrl": audio_url}
                                ]
                            }
                        }
                    ]
                }
            }
        },
        "outputContexts": [{
            "name": f"{request.json['session']}/contexts/lastshloka",
            "lifespanCount": 5,
            "parameters": {
                "chapter": entry["chapter"],
                "verse": entry["verse"]
            }
        }]
    })

def fallback(message):
    return jsonify({"fulfillmentText": message})

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
