import json
import re
from flask import Flask, request, jsonify
import random
import requests

app = Flask(__name__)

# Load audio index
with open('gita_audio_index.json', 'r') as f:
    audio_index = json.load(f)

# Add quarter number
def quarter_num(entry):
    if not isinstance(entry["quarter"], str):
        print(f"Invalid quarter field: {entry['quarter']} for entry {entry}")
        return None
    match = re.search(r"/(\d+)\.([1-4])\.mp3$", entry["quarter"])
    return int(match.group(2)) if match else None

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
    base_url = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/"

    if intent_name == "ZeroIntent":
        valid_entries = [e for e in audio_index if e.get("qnum") is not None]
        if not valid_entries:
            response["fulfillmentText"] = "No valid shlokas available."
            return jsonify(response)
        entry = random.choice(valid_entries)
        chapter, verse = entry["chapter"], entry["verse"]
        response["fulfillmentText"] = f"Playing random shloka {chapter}.{verse}"
        response["payload"]["google"]["richResponse"]["items"].append({
            "mediaResponse": {
                "mediaType": "AUDIO",
                "mediaObjects": [{
                    "contentUrl": f"{base_url}{entry['quarter']}",
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
            chapter, verse = int(chapter), int(verse)
            entry = next((e for e in audio_index if e["chapter"] == chapter and e["verse"] == verse and e["qnum"] is not None), None)
            if entry:
                audio_path = entry['full'] if requests.head(f"{base_url}{entry['full']}").status_code == 200 else entry['quarter']
                response["fulfillmentText"] = f"Playing full shloka {chapter}.{verse}"
                response["payload"]["google"]["richResponse"]["items"].append({
                    "mediaResponse": {
                        "mediaType": "AUDIO",
                        "mediaObjects": [{
                            "contentUrl": f"{base_url}{audio_path}",
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
                response["fulfillmentText"] = f"Full shloka {chapter}.{verse} not found."

    elif intent_name == "NextIntent":
        chapter = parameters.get('chapter')
        verse = parameters.get('verse')
        if chapter and verse:
            chapter, verse = int(chapter), int(verse)
            current_entry = next((e for e in audio_index if e["chapter"] == chapter and e["verse"] == verse), None)
            if current_entry:
                current_idx = audio_index.index(current_entry)
                for i in range(current_idx + 1, len(audio_index)):
                    if audio_index[i]["qnum"] is not None:
                        next_entry = audio_index[i]
                        break
                else:
                    next_entry = None
                if next_entry:
                    next_chapter, next_verse = next_entry["chapter"], next_entry["verse"]
                    response["fulfillmentText"] = f"Playing next shloka {next_chapter}.{next_verse}"
                    response["payload"]["google"]["richResponse"]["items"].append({
                        "mediaResponse": {
                            "mediaType": "AUDIO",
                            "mediaObjects": [{
                                "contentUrl": f"{base_url}{next_entry['quarter']}",
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
                response["fulfillmentText"] = f"Current shloka {chapter}.{verse} not found."

    elif intent_name == "ChapterIntent":
        chapter = parameters.get('chapter')
        if chapter:
            chapter = int(chapter)
            entry = next((e for e in audio_index if e["chapter"] == chapter and e["verse"] == 1 and e["qnum"] is not None), None)
            if entry:
                verse = 1
                response["fulfillmentText"] = f"Playing shloka {chapter}.{verse}"
                response["payload"]["google"]["richResponse"]["items"].append({
                    "mediaResponse": {
                        "mediaType": "AUDIO",
                        "mediaObjects": [{
                            "contentUrl": f"{base_url}{entry['quarter']}",
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
