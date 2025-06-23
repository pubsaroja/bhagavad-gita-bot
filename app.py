import json
import random
from flask import Flask, request, jsonify
from google.cloud import dialogflow_v2 as dialogflow
import os

app = Flask(__name__)

# Load audio index
with open('gita_audio_index.json') as f:
    audio_index = json.load(f)

# Initialize Dialogflow session client
session_client = dialogflow.SessionsClient()
PROJECT_ID = "gita-voice-bot"

def get_audio_url(chapter, verse, quarter=None, style='gurudatta'):
    base_url = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main"
    chapter = int(chapter)
    verse = int(verse)
    if quarter in ['pada1', 'first']:
        return f"{base_url}/AudioQuarterAll/Chapter {chapter}/{chapter}.{verse}.mp3"
    elif quarter in ['pada3', 'third']:
        return f"{base_url}/AudioQuarterAll/Chapter {chapter}/{chapter}.{verse}3.mp3"
    elif style == 'sringeri':
        return f"{base_url}/AudioFullSringeri/{chapter}.{verse}.mp4"
    else:
        return f"{base_url}/AudioFull/{chapter}.{verse}.mp3"

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    intent = req.get('queryResult', {}).get('intent', {}).get('displayName', '')
    parameters = req.get('queryResult', {}).get('parameters', {})
    session = req.get('session', f"projects/{PROJECT_ID}/agent/sessions/default-session")

    # Get context
    contexts = req.get('queryResult', {}).get('outputContexts', [])
    shloka_context = next((c for c in contexts if c['name'].endswith('shloka-context')), {})
    context_params = shloka_context.get('parameters', {})
    current_chapter = int(context_params.get('chapter', 1))
    current_verse = int(context_params.get('verse', 1))
    current_quarter = context_params.get('quarter', 'pada1')

    response = {
        "fulfillmentText": "",
        "payload": {
            "google": {
                "expectUserResponse": True,
                "richResponse": {
                    "items": []
                }
            }
        },
        "outputContexts": []
    }

    if intent == 'ZeroIntent':
        quarter = parameters.get('quarter', 'pada1')
        chapter = random.randint(1, 18)
        verse = random.randint(1, audio_index[str(chapter)]['verses'])
        if quarter == 'pada1_or_pada3':
            quarter = random.choice(['pada1', 'pada3'])
        audio_url = get_audio_url(chapter, verse, quarter)
        response['fulfillmentText'] = f"Playing {'first' if quarter == 'pada1' else 'third'} quarter of shloka {chapter}.{verse}"
        response['payload']['google']['richResponse']['items'].append({
            "mediaResponse": {
                "mediaType": "AUDIO",
                "mediaObjects": [{
                    "contentUrl": audio_url,
                    "name": f"Shloka {chapter}.{verse} ({'first' if quarter == 'pada1' else 'third'} quarter)"
                }]
            }
        })
        response['outputContexts'].append({
            "name": f"{session}/contexts/shloka-context",
            "lifespanCount": 5,
            "parameters": {
                "chapter": float(chapter),
                "verse": float(verse),
                "quarter": quarter
            }
        })

    elif intent == 'FullIntent':
        style = parameters.get('style', 'gurudatta')
        if not context_params or not context_params.get('chapter') or not context_params.get('verse'):
            response['fulfillmentText'] = "Please select a shloka first"
            response['outputContexts'].append({
                "name": f"{session}/contexts/shloka-context",
                "lifespanCount": 5,
                "parameters": context_params
            })
        else:
            audio_url = get_audio_url(current_chapter, current_verse, style=style)
            response['fulfillmentText'] = f"Playing full shloka {current_chapter}.{current_verse} in {style} style"
            response['payload']['google']['richResponse']['items'].append({
                "mediaResponse": {
                    "mediaType": "AUDIO",
                    "mediaObjects": [{
                        "contentUrl": audio_url,
                        "name": f"Shloka {current_chapter}.{current_verse} (full)"
                    }]
                }
            })
            response['outputContexts'].append({
                "name": f"{session}/contexts/shloka-context",
                "lifespanCount": 5,
                "parameters": {
                    "chapter": float(current_chapter),
                    "verse": float(current_verse),
                    "quarter": current_quarter
                }
            })

    elif intent == 'NextIntent':
        if not context_params or not context_params.get('chapter') or not context_params.get('verse'):
            response['fulfillmentText'] = "Please select a shloka first"
            response['outputContexts'].append({
                "name": f"{session}/contexts/shloka-context",
                "lifespanCount": 5,
                "parameters": context_params
            })
        else:
            max_verses = audio_index[str(current_chapter)]['verses']
            next_verse = current_verse + 1
            next_chapter = current_chapter
            if next_verse > max_verses:
                next_verse = 1
                next_chapter = current_chapter % 18 + 1
            audio_url = get_audio_url(next_chapter, next_verse, current_quarter)
            response['fulfillmentText'] = f"Playing {'first' if current_quarter == 'pada1' else 'third'} quarter of shloka {next_chapter}.{next_verse}"
            response['payload']['google']['richResponse']['items'].append({
                "mediaResponse": {
                    "mediaType": "AUDIO",
                    "mediaObjects": [{
                        "contentUrl": audio_url,
                        "name": f"Shloka {next_chapter}.{next_verse} ({'first' if current_quarter == 'pada1' else 'third'} quarter)"
                    }]
                }
            })
            response['outputContexts'].append({
                "name": f"{session}/contexts/shloka-context",
                "lifespanCount": 5,
                "parameters": {
                    "chapter": float(next_chapter),
                    "verse": float(next_verse),
                    "quarter": current_quarter
                }
            })

    elif intent == 'ChapterIntent':
        chapter = int(parameters.get('chapter', 1))
        pada = parameters.get('pada', 'first')
        verse = random.randint(1, audio_index[str(chapter)]['verses'])
        quarter = 'pada1' if pada == 'first' else 'pada3'
        audio_url = get_audio_url(chapter, verse, quarter)
        response['fulfillmentText'] = f"Playing {'first' if quarter == 'pada1' else 'third'} quarter of shloka {chapter}.{verse}"
        response['payload']['google']['richResponse']['items'].append({
            "mediaResponse": {
                "mediaType": "AUDIO",
                "mediaObjects": [{
                    "contentUrl": audio_url,
                    "name": f"Shloka {chapter}.{verse} ({'first' if quarter == 'pada1' else 'third'} quarter)"
                }]
            }
        })
        response['outputContexts'].append({
            "name": f"{session}/contexts/shloka-context",
            "lifespanCount": 5,
            "parameters": {
                "chapter": float(chapter),
                "verse": float(verse),
                "quarter": quarter
            }
        })

    return jsonify(response)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
