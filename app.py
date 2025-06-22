from flask import Flask, request, jsonify
from flask_cors import CORS
import json
import random
import os
import urllib.parse
import logging

app = Flask(__name__)
CORS(app, resources={r"/webhook": {"origins": [
    "http://localhost:8000",
    "http://localhost:5000",  # Allow local testing
    "https://gita-voice-bot-504694669439.us-central1.run.app",
    "https://pubsaroja.github.io"  # Add GitHub Pages origin
]}})

# Setup logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)

# Base URL for audio files hosted on GitHub
AUDIO_BASE_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/"

# Load audio index
try:
    with open('gita_audio_index.json', 'r') as f:
        audio_index = json.load(f)
    logger.debug(f"Loaded audio index with {len(audio_index)} entries")
except FileNotFoundError:
    logger.error("gita_audio_index.json not found")
    audio_index = {}

def get_audio_url(chapter, verse, quarter='all'):
    key = f"{chapter}.{verse}"
    if key in audio_index:
        field = 'full' if quarter == 'full' else 'quarter'
        audio_path = audio_index[key].get(field, '')
        if audio_path:
            encoded_path = urllib.parse.quote(audio_path)
            audio_url = AUDIO_BASE_URL + encoded_path
            logger.debug(f"Generated audio URL for {key}, {field}: {audio_url}")
            return audio_url
        logger.warning(f"No {field} path found for {key}")
    logger.warning(f"No audio path found for {key}, quarter: {quarter}")
    return ''

@app.route('/webhook', methods=['POST', 'OPTIONS'])
def webhook():
    if request.method == 'OPTIONS':
        logger.debug("Handling OPTIONS request")
        return jsonify({}), 200
    
    req = request.get_json(silent=True)
    if not req:
        logger.error("Invalid request: No JSON data")
        return jsonify({'fulfillmentText': 'Invalid request'}), 400

    logger.debug(f"Received request: {json.dumps(req, indent=2)}")
    intent = req.get('queryResult', {}).get('intent', {}).get('displayName', '')
    parameters = req.get('queryResult', {}).get('parameters', {})
    output_contexts = req.get('queryResult', {}).get('outputContexts', [])

    logger.debug(f"Intent: {intent}, Parameters: {parameters}, Contexts: {output_contexts}")
    response = {'fulfillmentText': '', 'outputContexts': []}
    session = req.get('session', 'default-session')
    
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
                        'name': f"{session}/contexts/shloka-context",
                        'lifespanCount': 5,
                        'parameters': {'chapter': float(chapter), 'verse': float(verse)}
                    }]
                else:
                    response['fulfillmentText'] = 'Audio not found for random shloka'
    
    elif intent == 'ChapterIntent':
        chapter = int(parameters.get('chapter', 0))
        logger.debug(f"ChapterIntent: chapter={chapter}")
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
                        'name': f"{session}/contexts/shloka-context",
                        'lifespanCount': 5,
                        'parameters': {'chapter': float(chapter), 'verse': float(verse)}
                    }]
                else:
                    response['fulfillmentText'] = f'No audio found for chapter {chapter}'
    
    elif intent in ['FullIntent', 'NextIntent']:
        logger.debug(f"{intent}: outputContexts={output_contexts}")
        context = next((c for c in output_contexts if 'shloka-context' in c.get('name', '')), None)
        if not context:
            response['fulfillmentText'] = 'Please select a shloka first'
            logger.warning(f"No shloka-context found for {intent}")
        elif not audio_index:
            response['fulfillmentText'] = 'Audio index not loaded'
        else:
            chapter = int(float(context.get('parameters', {}).get('chapter', 0)))
            verse = int(float(context.get('parameters', {}).get('verse', 0)))
            logger.debug(f"{intent}: chapter={chapter}, verse={verse}")
            if intent == 'NextIntent':
                verse += 1
                verse_keys = [k for k in audio_index.keys() if k.startswith(f'{chapter}.')]
                if f"{chapter}.{verse}" not in audio_index:
                    verse = 1
                    chapter = (chapter % 18) + 1
                    verse_keys = [k for k in audio_index.keys() if k.startswith(f'{chapter}.')]
                if not verse_keys:
                    response['fulfillmentText'] = f'No verses found for chapter {chapter}'
                    return jsonify(response)
            audio_url = get_audio_url(chapter, verse, quarter='full' if intent == 'FullIntent' else 'all')
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
                    'name': f"{session}/contexts/shloka-context",
                    'lifespanCount': 5,
                    'parameters': {'chapter': float(chapter), 'verse': float(verse)}
                }]
            else:
                response['fulfillmentText'] = f'No audio found for shloka {chapter}.{verse}'
    
    else:
        response['fulfillmentText'] = 'Unknown intent'

    logger.debug(f"Response: {json.dumps(response, indent=2)}")
    return jsonify(response)

if __name__ == '__main__':
    port = int(os.environ.get('PORT', 5000))
    app.run(host='0.0.0.0', port=port, debug=True)
