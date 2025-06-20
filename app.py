from flask import Flask, request, jsonify
from flask_cors import CORS  # ✅ New line
import json, random

app = Flask(__name__)
CORS(app)  # ✅ Enable CORS for all routes

with open("gita_audio_index.json", encoding="utf-8") as f:
    audio_data = json.load(f)

def find_entry(chapter, verse):
    return next((e for e in audio_data if e["chapter"] == chapter and e["verse"] == verse), None)

@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json()
    intent = req["queryResult"]["intent"]["displayName"]
    session = req["session"]
    context_dict = {ctx["name"].split("/")[-1]: ctx for ctx in req["queryResult"].get("outputContexts", [])}
    last_ctx = context_dict.get("lastshloka", {}).get("parameters", {})

    if intent == "ZeroIntent":
        entry = random.choice(audio_data)
    elif intent == "ChapterIntent":
        chapter = int(req["queryResult"]["parameters"].get("chapter", 1))
        candidates = [e for e in audio_data if e["chapter"] == chapter]
        entry = random.choice(candidates) if candidates else random.choice(audio_data)
    elif intent == "FullIntent":
        chapter = int(last_ctx.get("chapter", 1))
        verse = int(last_ctx.get("verse", 1))
        entry = find_entry(chapter, verse) or random.choice(audio_data)
        return build_response(f"Chapter {entry['chapter']}, Verse {entry['verse']}", entry["full"], entry)
    elif intent == "NextIntent":
        chapter = int(last_ctx.get("chapter", 1))
        verse = int(last_ctx.get("verse", 1)) + 1
        next_entry = find_entry(chapter, verse)
        if not next_entry:
            chapter = chapter + 1 if chapter < 18 else 1
            verse = 1
            next_entry = find_entry(chapter, verse)
        entry = next_entry or random.choice(audio_data)
    else:
        return jsonify({"fulfillmentText": "Sorry, I didn't understand that."})

    return build_response(f"Chapter {entry['chapter']}, Verse {entry['verse']}", entry["quarter"], entry)

def build_response(text, audio_url, entry):
    return jsonify({
        "payload": {
            "google": {
                "expectUserResponse": True,
                "richResponse": {
                    "items": [
                        { "simpleResponse": { "textToSpeech": text } },
                        {
                            "mediaResponse": {
                                "mediaType": "AUDIO",
                                "mediaObjects": [
                                    { "name": text, "contentUrl": audio_url }
                                ]
                            }
                        }
                    ]
                }
            }
        },
        "fulfillmentText": text,
        "outputContexts": [
            {
                "name": f"{request.json['session']}/contexts/lastshloka",
                "lifespanCount": 5,
                "parameters": {
                    "chapter": entry["chapter"],
                    "verse": entry["verse"]
                }
            }
        ]
    })

if __name__ == "__main__":
    app.run(host='0.0.0.0', port=8080)
