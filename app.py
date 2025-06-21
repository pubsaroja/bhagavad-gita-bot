from flask import Flask, request, jsonify
from flask_cors import CORS
import json, random, re, os

app = Flask(__name__)
CORS(app)

# Load audio index
with open("gita_audio_index.json", encoding="utf-8") as f:
    full_index = json.load(f)

# Tag quarter part (1 to 4)
def quarter_num(entry):
    match = re.search(r"\.([1-4])\.mp3$", entry["quarter"])
    return int(match.group(1)) if match else 1

for e in full_index:
    e["qnum"] = quarter_num(e)

# Only use 1st and 3rd quarter
quarter_13 = [e for e in full_index if e["qnum"] in (1, 3)]

# Full shloka map for lookup
full_only = {}
for e in full_index:
    key = (e["chapter"], e["verse"])
    if key not in full_only:
        full_only[key] = e

def find_entry(ch, vs):
    return full_only.get((ch, vs))

# Webhook route
@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json(force=True)
    session = req.get("session", "")
    intent = req["queryResult"]["intent"]["displayName"]
    parameters = req["queryResult"].get("parameters", {})
    ctx_map = {c["name"].split("/")[-1]: c for c in req["queryResult"].get("outputContexts", [])}
    last = ctx_map.get("lastshloka", {}).get("parameters", {})

    # Initialize chapter and verse from context or defaults
    current_chapter = int(last.get("chapter", 1))
    current_verse = int(last.get("verse", 1))

    if intent == "ZeroIntent":
        entry = random.choice(quarter_13)
        return reply(entry, entry["quarter"], session)

    elif intent == "ChapterIntent":
        chap = int(parameters.get("chapter", current_chapter))
        opts = [e for e in quarter_13 if e["chapter"] == chap]
        entry = random.choice(opts) if opts else random.choice(quarter_13)
        return reply(entry, entry["quarter"], session)

    elif intent == "FullIntent":
        entry = find_entry(current_chapter, current_verse)
        if not entry:
            entry = random.choice(full_index)
        return reply(entry, entry["full"], session)

    elif intent == "NextIntent":
        verse = current_verse + 1
        entry = find_entry(current_chapter, verse)
        if not entry:
            # Move to next chapter or loop back to Chapter 1
            next_chapter = current_chapter + 1 if current_chapter < 18 else 1
            verse = 1
            entry = find_entry(next_chapter, verse)
        if not entry:
            entry = random.choice(full_index)
        return reply(entry, entry["full"], session)

    return jsonify({"fulfillmentText": "Sorry, I didn’t understand."})

# Response helper
def reply(entry, audio_url, session):
    text = f"Chapter {entry['chapter']}, Verse {entry['verse']}"
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
                            "mediaObjects": [
                                { "name": text, "contentUrl": audio_url }
                            ]
                        }}
                    ]
                }
            }
        },
        "outputContexts": [
            {
                "name": f"{session}/contexts/lastshloka",
                "lifespanCount": 5,
                "parameters": {
                    "chapter": float(entry["chapter"]),  # Use float to match Dialogflow
                    "verse": float(entry["verse"])
                }
            }
        ]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)