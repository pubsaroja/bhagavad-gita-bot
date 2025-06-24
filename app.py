import os
import json
import random
import logging
from flask import Flask, request, jsonify
from flask_cors import CORS

app = Flask(__name__)
CORS(app, resources={r"/webhook": {"origins": "https://pubsaroja.github.io"}})

# Set up logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

# Load audio index
try:
    with open('gita_audio_index.json', 'r') as f:
        audio_index = json.load(f)
    logger.info("gita_audio_index.json loaded successfully")
except FileNotFoundError:
    logger.error("gita_audio_index.json not found")
    audio_index = {}

# Base URL for audio files
AUDIO_BASE_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/"

def get_max_verses(chapter):
    """Calculate max verses for a chapter from audio_index."""
    chapter_str = str(chapter)
    verses = [int(key.split('.')[1]) for key in audio_index if key.startswith(chapter_str + '.')]
    return max(verses) if verses else 1

def get_audio_url(chapter, verse, quarter=None, style=None):
    key = f"{chapter}.{verse}"
    if key not in audio_index:
        logger.error(f"No audio entry for {key}")
        return None
    
    entry = audio_index[key]
    if quarter:
        if quarter == 'pada1':
            url = f"{AUDIO_BASE_URL}{entry['quarter']}"
            logger.debug(f"Pada1 URL: {url}")
            return url
        elif quarter == 'pada3':
            quarter_path = entry.get('quarter3', entry['quarter'].replace('.mp3', '3.mp3'))
            url = f"{AUDIO_BASE_URL}{quarter_path}"
            logger.debug(f"Pada3 URL: {url}")
            return url
    elif style:
        if style == 'gurudatta':
            url = f"{AUDIO_BASE_URL}{entry['full']}"
            logger.debug(f"Gurudatta URL: {url}")
            return url
        elif style == 'sringeri':
            sringeri_path = entry.get('sringeri', entry['full'].replace('AudioFull', 'AudioFullSringeri'))
            url = f"{AUDIO_BASE_URL}{sringeri_path}"
            logger.debug(f"Sringeri URL: {url}")
            return url
    logger.error(f"Invalid quarter or style for {key}")
    return None

@app.route('/webhook', methods=['POST'])
def webhook():
    try:
        req = request.get_json(silent=True, force=True)
        logger.debug(f"Request payload: {req}")
        intent_name = req.get('queryResult', {}).get('intent', {}).get('displayName', '')
        parameters = req.get('queryResult', {}).get('parameters', {})
        session = req.get('session', '') or 'default-session'
        output_contexts = req.get('queryResult', {}).get('outputContexts', [])
        logger.info(f"Processing intent: {intent_name}, session: {session}")

        response = {'fulfillmentText': 'Processing request...'}

        # Find shloka-context
        context = next((ctx for ctx in output_contexts if 'shloka-context' in ctx.get('name', '')), None)
        context_params = context.get('parameters', {}) if context else {}
        logger.debug(f"Current context: {context_params}")

        # Handle ZeroIntent (Get Random Shloka Q1 or Q1/Q3)
        if intent_name == 'ZeroIntent':
            quarter = parameters.get('quarter', 'pada1')
            if quarter == 'pada1_or_pada3':
                quarter = random.choice(['pada1', 'pada3'])
            logger.debug(f"Selected quarter: {quarter}")
            
            chapter = random.randint(1, 18)
            max_verses = get_max_verses(chapter)
            verse = random.randint(1, max_verses)
            logger.debug(f"Selected chapter: {chapter}, verse: {verse}")
            
            audio_url = get_audio_url(chapter, verse, quarter)
            if audio_url:
                response['fulfillmentText'] = f"Playing {quarter} of Chapter {chapter}, Verse {verse}"
                response['payload'] = {
                    'google': {
                        'expectUserResponse': True,
                        'richResponse': {
                            'items': [
                                {
                                    'mediaResponse': {
                                        'mediaType': 'AUDIO',
                                        'mediaObjects': [
                                            {
                                                'name': f"Chapter {chapter} Verse {verse} {quarter}",
                                                'description': f"{quarter} of Gita Shloka",
                                                'contentUrl': audio_url
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
                response['outputContexts'] = [
                    {
                        'name': f"{session}/contexts/shloka-context",
                        'lifespanCount': 5,
                        'parameters': {
                            'chapter': float(chapter),
                            'verse': float(verse),
                            'quarter': quarter
                        }
                    }
                ]
                logger.info(f"Response prepared for {quarter} of {chapter}.{verse}")
            else:
                response['fulfillmentText'] = f"Sorry, audio not found for Chapter {chapter}, Verse {verse}."
                logger.error(f"Audio not found for {chapter}.{verse}, quarter: {quarter}")

        # Handle FullIntent (Get Full Shloka)
        elif intent_name == 'FullIntent':
            style = parameters.get('style', 'gurudatta')
            if not context_params or not context_params.get('chapter') or not context_params.get('verse'):
                response['fulfillmentText'] = "Please select a shloka first"
                logger.warning("No shloka-context found")
            else:
                current_chapter = int(float(context_params['chapter']))
                current_verse = int(float(context_params['verse']))
                audio_url = get_audio_url(current_chapter, current_verse, style=style)
                if audio_url:
                    response['fulfillmentText'] = f"Playing full shloka of Chapter {current_chapter}, Verse {current_verse} in {style} style"
                    response['payload'] = {
                        'google': {
                            'expectUserResponse': True,
                            'richResponse': {
                                'items': [
                                    {
                                        'mediaResponse': {
                                            'mediaType': 'AUDIO',
                                            'mediaObjects': [
                                                {
                                                    'name': f"Chapter {current_chapter} Verse {current_verse} Full",
                                                    'description': f"Full Shloka in {style} style",
                                                    'contentUrl': audio_url
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    }
                    response['outputContexts'] = [
                        {
                            'name': f"{session}/contexts/shloka-context",
                            'lifespanCount': 5,
                            'parameters': {
                                'chapter': float(current_chapter),
                                'verse': float(current_verse),
                                'style': style
                            }
                        }
                    ]
                    logger.info(f"Response prepared for full shloka {current_chapter}.{current_verse}, style: {style}")
                else:
                    response['fulfillmentText'] = f"Sorry, full shloka audio not found for Chapter {current_chapter}, Verse {current_verse}."
                    logger.error(f"Full shloka audio not found for {current_chapter}.{current_verse}, style: {style}")

        # Handle NextIntent (Get Next Shloka)
        elif intent_name == 'NextIntent':
            if not context_params or not context_params.get('chapter') or not context_params.get('verse'):
                response['fulfillmentText'] = "Please select a shloka first"
                logger.warning("No shloka-context found")
            else:
                current_chapter = int(float(context_params['chapter']))
                current_verse = int(float(context_params['verse']))
                current_quarter = context_params.get('quarter', 'pada1')
                
                max_verses = get_max_verses(current_chapter)
                next_verse = current_verse + 1
                next_chapter = current_chapter
                
                if next_verse > max_verses:
                    next_verse = 1
                    next_chapter = current_chapter % 18 + 1
                    max_verses = get_max_verses(next_chapter)
                    if next_verse > max_verses:
                        next_verse = 1
                
                audio_url = get_audio_url(next_chapter, next_verse, current_quarter)
                if audio_url:
                    response['fulfillmentText'] = f"Playing {current_quarter} of Chapter {next_chapter}, Verse {next_verse}"
                    response['payload'] = {
                        'google': {
                            'expectUserResponse': True,
                            'richResponse': {
                                'items': [
                                    {
                                        'mediaResponse': {
                                            'mediaType': 'AUDIO',
                                            'mediaObjects': [
                                                {
                                                    'name': f"Chapter {next_chapter} Verse {next_verse} {current_quarter}",
                                                    'description': f"{current_quarter} of Gita Shloka",
                                                    'contentUrl': audio_url
                                                }
                                            ]
                                        }
                                    }
                                ]
                            }
                        }
                    }
                    response['outputContexts'] = [
                        {
                            'name': f"{session}/contexts/shloka-context",
                            'lifespanCount': 5,
                            'parameters': {
                                'chapter': float(next_chapter),
                                'verse': float(next_verse),
                                'quarter': current_quarter
                            }
                        }
                    ]
                    logger.info(f"Response prepared for next shloka {next_chapter}.{current_verse}, quarter: {current_quarter}")
                else:
                    response['fulfillmentText'] = f"Sorry, next shloka audio not found for Chapter {next_chapter}, Verse {next_verse}."
                    logger.error(f"Next shloka audio not found for {next_chapter}.{next_verse}, quarter: {current_quarter}")

        # Handle ChapterIntent (Select Chapter)
        elif intent_name == 'ChapterIntent':
            chapter = int(float(parameters.get('chapter', 1)))
            pada = parameters.get('pada', 'pada1')
            quarter = 'pada1' if pada == 'first' else pada
            logger.debug(f"ChapterIntent: chapter={chapter}, quarter={quarter}")
            
            max_verses = get_max_verses(chapter)
            verse = random.randint(1, max_verses)
            
            audio_url = get_audio_url(chapter, verse, quarter)
            if audio_url:
                response['fulfillmentText'] = f"Playing {quarter} of Chapter {chapter}, Verse {verse}"
                response['payload'] = {
                    'google': {
                        'expectUserResponse': True,
                        'richResponse': {
                            'items': [
                                {
                                    'mediaResponse': {
                                        'mediaType': 'AUDIO',
                                        'mediaObjects': [
                                            {
                                                'name': f"Chapter {chapter} Verse {verse} {quarter}",
                                                'description': f"{quarter} of Gita Shloka",
                                                'contentUrl': audio_url
                                            }
                                        ]
                                    }
                                }
                            ]
                        }
                    }
                }
                response['outputContexts'] = [
                    {
                        'name': f"{session}/contexts/shloka-context",
                        'lifespanCount': 5,
                        'parameters': {
                            'chapter': float(chapter),
                            'verse': float(verse),
                            'quarter': quarter
                        }
                    }
                ]
                logger.info(f"Response prepared for {quarter} of {chapter}.{verse}")
            else:
                response['fulfillmentText'] = f"Sorry, audio not found for Chapter {chapter}, Verse {verse}."
                logger.error(f"Audio not found for {chapter}.{verse}, quarter: {quarter}")

        logger.debug(f"Response: {response}")
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error processing webhook: {str(e)}")
        return jsonify({'fulfillmentText': f"Server error: {str(e)}"}), 500

if __name__ == '__main__':
    print(f"Starting Flask on port {os.environ.get('PORT', 8080)}")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))
