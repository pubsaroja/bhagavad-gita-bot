from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import random
import os

app = Flask(__name__)
CORS(app, resources={r"/webhook": {"origins": ["http://localhost:8000", "https://gita-voice-bot-504694669439.us-central1.run.app"]}})

# Load audio index
try:
    with open('gita_audio_index.json', 'r') as f:
        audio_index = json.load(f)
    # Convert list to dictionary if necessary
    if isinstance(audio_index, list):
        audio_index = {f"{entry['chapter']}.{entry['verse']}": entry for entry in audio_index if 'chapter' in entry and 'verse' in entry}
except FileNotFoundError:
    print("Error: gita_audio_index.json not found")
    audio_index = {}

def get_audio_url(chapter, verse, quarter='all'):
    key = f"{chapter}.{verse}"
    if key in audio_index:
        return audio_index[key].get(f'quarter_{quarter}', '')
    return ''

@app.route('/webhook', methods=['POST', 'OPTIONS'])
def webhook():
    if request.method == 'OPTIONS':
        return jsonify({}), 200
    
    req = request.get_json(silent=True)
    if not req:
        return jsonify({'fulfillmentText': 'Invalid request'}), 400

    intent = req.get('queryResult', {}).get('intent', {}).get('displayName', '')
    parameters = req.get('queryResult', {}).get('parameters', {})
    output_contexts = req.get('queryResult', {}).get('outputContexts', [])

    response = {'fulfillmentText': '', 'outputContexts': []}
    
    if intent == 'ZeroIntent':
        if not audio_index:
            response['fulfillmentText'] = 'Audio index not loaded'
        else:
            chapter = random.randint(1, 18)
            verse_keys = [k for k in audio_index.keys() if k.startswith(f'{chapter}.')]
            if not verse_keys:
                response['fulfillmentText'] = f'No verses found for chapter {chapter}'
            else:
                verse = random.randint(1, max([int(k.split('.')[1]) for k in verse_keys]))
                audio_url = get_audio_url(chapter, verse)
                if audio_url:
                    response['fulfillmentText'] = f'Playing random shloka {chapter}.{verse}'
                    response['payload'] = {
                        'google': {
                            'richResponse': {
                                'items': [{
                                    'mediaResponse': {
                                        'mediaType': 'AUDIO',
                                        'mediaObjects': [{
                                            'contentUrl': audio_url,
                                            'name': f'Shloka {chapter}.{verse}'
                                        }]
                                    }
                                }]
                            }
                        }
                    }
                    response['outputContexts'] = [{
                        'name': f"{req.get('session')}/contexts/shloka-context",
                        'lifespanCount': 5,
                        'parameters': {'chapter': chapter, 'verse': verse}
                    }]
                else:
                    response['fulfillmentText'] = 'Audio not found for random shloka'
    
    elif intent == 'ChapterIntent':
        chapter = int(parameters.get('chapter', 0))
        if chapter < 1 or chapter > 18:
            response['fulfillmentText'] = 'Invalid chapter number'
        elif not audio_index:
            response['fulfillmentText'] = 'Audio index not loaded'
        else:
            verse_keys = [k for k in audio_index.keys() if k.startswith(f'{chapter}.')]
            if not verse_keys:
                response['fulfillmentText'] = f'No verses found for chapter {chapter}'
            else:
                verse = random.randint(1, max([int(k.split('.')[1]) for k in verse_keys]))
                audio_url = get_audio_url(chapter, verse)
                if audio_url:
                    response['fulfillmentText'] = f'Playing shloka {chapter}.{verse} from chapter {chapter}'
                    response['payload'] = {
                        'google': {
                            'richResponse': {
                                'items': [{
                                    'mediaResponse': {
                                        'mediaType': 'AUDIO',
                                        'mediaObjects': [{
                                            'contentUrl': audio_url,
                                            'name': f'Shloka {chapter}.{verse}'
                                        }]
                                    }
                                }]
                            }
                        }
                    }
                    response['outputContexts'] = [{
                        'name': f"{req.get('session')}/contexts/shloka-context",
                        'lifespanCount': 5,
                        'parameters': {'chapter': chapter, 'verse': verse}
                    }]
                else:
                    response['fulfillmentText'] = f'No audio found for chapter {chapter}'
    
    elif intent == 'FullIntent' or intent == 'NextIntent':
        context = next((c for c in output_contexts if c.get('name', '').endswith('shloka-context')), None)
        if not context:
            response['fulfillmentText'] = 'Please select a shloka first'
        elif not audio_index:
            response['fulfillmentText'] = 'Audio index not loaded'
        else:
            chapter = int(context.get('parameters', {}).get('chapter', 0))
            verse = int(context.get('parameters', {}).get('verse', 0))
            if intent == 'NextIntent':
                verse += 1
                verse_keys = [k for k in audio_index.keys() if k.startswith(f'{chapter}.')]
                if f"{chapter}.{verse}" not in audio_index:
                    verse = 1
                    chapter = chapter % 18 + 1
                    verse_keys = [k for k in audio_index.keys() if k.startswith(f'{chapter}.')]
                if not verse_keys:
                    response['fulfillmentText'] = f'No verses found for chapter {chapter}'
                    return jsonify(response)
            audio_url = get_audio_url(chapter, verse)
            if audio_url:
                response['fulfillmentText'] = f'Playing shloka {chapter}.{verse}'
                response['payload'] = {
                    'google': {
                        'richResponse': {
                            'items': [{
                                'mediaResponse': {
                                    'mediaType': 'AUDIO',
                                    'mediaObjects': [{
                                        'contentUrl': audio_url,
                                        'name': f'Shloka {chapter}.{verse}'
                                    }]
                                }
                            }]
                        }
                    }
                }
                response['outputContexts'] = [{
                    'name': f"{req.get('session')}/contexts/shloka-context",
                    'lifespanCount': 5,
                    'parameters': {'chapter': chapter, 'verse': verse}
                }]
            else:
                response['fulfillmentText'] = f'No audio found for shloka {chapter}.{verse}'
    
    else:
        response['fulfillmentText'] = 'Unknown intent'

    return jsonify(response)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 8080))
    app.run(host='0.0.0.0', port=port, debug=True)
