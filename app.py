import json
import re
from flask import Flask, request, jsonify
from datetime import datetime
import random
import os

app = Flask(__name__)

# Load audio index
with open('gita_audio_index.json', 'r') as f:
    audio_index = json.load(f)

# Add quarter number
def quarter_num(entry):
    if not isinstance(entry["quarter"], str):
        print(f"Invalid quarter field: {entry['quarter']} for entry {entry}")
        return None
    match = re.search(r"\.([1-4])\.mp3$", entry["quarter"])
    return int(match.group(1)) if match else None

for e in audio_index:
    e["qnum"] = quarter_num(e)

# Webhook endpoint
@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    query_result = req.get('queryResult', {})
    intent_name = query_result.get('intent', {}).get('displayName', '')
    parameters = query_result.get('parameters', {})
    output_contexts = query_result.get('outputContexts', [])

    response = {
        "fulfillmentText": "",
        "outputContexts": [],
        "payload": {"google": {"expectUserResponse": True, "richResponse": {"items": []}}}
    }

    if intent_name == "ZeroIntent":
        entry = random.choice([e for e in audio_index if e.get("qnum")])
        chapter, verse = map(int, entry["full"].split('/')[-1].replace('.mp3', '').split('.'))
        response["fulfillmentText"] = f"Playing random shloka {chapter}.{verse}"
        response["payload"]["google"]["richResponse"]["items"].append({
            "mediaResponse": {
                "mediaType": "AUDIO",
                "mediaObjects": [{
                    "contentUrl": f"https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/maintenance/{entry['quarter']}",
                    "name": f"Shloka {chapter}.{verse}"
                }]
            }
        })
        response["outputContexts"] = [{
            "name": f"{req['session']}/contexts/shloka-context",
            "lifespanCount": 5,
            "parameters": {"chapter": chapter, "verse": verse}
        }]

    elif intent_name == "FullIntent":
        chapter = parameters.get('chapter')
        verse = parameters.get('verse')
        if chapter and verse:
            entry = next((e for e in audio_index if e["full"].endswith(f"{int(chapter)}.{int(verse)}.mp3")), None)
            if entry:
                response["fulfillmentText"] = f"Playing full shloka {chapter}.{verse}"
                response["payload"]["google"]["richResponse"]["items"].append({
                    "mediaResponse": {
                        "mediaType": "AUDIO",
                        "mediaObjects": [{
                            "contentUrl": f"https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/maintenance/{entry['full']}",
                            "name": f"Full Shloka {chapter}.{verse}"
                        }]
                    }
                })
                response["outputContexts"] = [{
                    "name": f"{req['session']}/contexts/shloka-context",
                    "lifespanCount": 5,
                    "parameters": {"chapter": chapter, "verse": verse}
                }]
            else:
                response["fulfillmentText"] = "Full shloka not found."

    elif intent_name == "NextIntent":
        chapter = parameters.get('chapter')
        verse = parameters.get('verse')
        if chapter and verse:
            current_entry = next((e for e in audio_index if e["full"].endswith(f"{int(chapter)}.{int(verse)}.mp3")), None)
            if current_entry:
                current_idx = audio_index.index(current_entry)
                next_entry = audio_index[current_idx + 1] if current_idx + 1 < len(audio_index) else None
                if next_entry:
                    next_chapter, next_verse = map(int, next_entry["full"].split('/')[-1].replace('.mp3', '').split('.'))
                    response["fulfillmentText"] = f"Playing next shloka {next_chapter}.{next_verse}"
                    response["payload"]["google"]["richResponse"]["items"].append({
                        "mediaResponse": {
                            "mediaType": "AUDIO",
                            "mediaObjects": [{
                                "contentUrl": f"https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/maintenance/{next_entry['quarter']}",
                                "name": f"Shloka {next_chapter}.{next_verse}"
                            }]
                        }
                    })
                    response["outputContexts"] = [{
                        "name": f"{req['session']}/contexts/shloka-context",
                        "lifespanCount": 5,
                        "parameters": {"chapter": next_chapter, "verse": next_verse}
                    }]
                else:
                    response["fulfillmentText"] = "No next shloka available."
            else:
                response["fulfillmentText"] = "Current shloka not found."

    elif intent_name == "ChapterIntent":
        chapter = parameters.get('chapter')
        if chapter:
            entry = next((e for e in audio_index if e["full"].startswith(f"AudioFull/{int(chapter)}.1")), None)
            if entry:
                verse = 1
                response["fulfillmentText"] = f"Playing shloka {chapter}.{verse}"
                response["payload"]["google"]["richResponse"]["items"].append({
                    "mediaResponse": {
                        "mediaType": "AUDIO",
                        "mediaObjects": [{
                            "contentUrl": f"https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/maintenance/{entry['quarter']}",
                            "name": f"Shloka {chapter}.{verse}"
                        }]
                    }
                })
                response["outputContexts"] = [{
                    "name": f"{req['session']}/contexts/shloka-context",
                    "lifespanCount": 5,
                    "parameters": {"chapter": chapter, "verse": verse}
                }]
            else:
                response["fulfillmentText"] = f"Chapter {chapter} not found."

    else:
        response["fulfillmentText"] = "Unknown command."

    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=8080)
