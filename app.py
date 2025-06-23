import os
import json
import random
from flask import Flask, request, jsonify
from google.cloud import dialogflow_v2 as dialogflow

app = Flask(__name__)

# Load audio index
try:
    with open('gita_audio_index.json', 'r') as f:
        audio_index = json.load(f)
except FileNotFoundError:
    print("Error: gita_audio_index.json not found")
    audio_index = {}

# Base URL for audio files (replace with your bucket URL)
AUDIO_BASE_URL = "https://raw.githubusercontent.com/pubsaroja/bhagavad-gita-bot/main/"

def get_max_verses(chapter):
    """Calculate max verses for a chapter from audio_index."""
    chapter_str = str(chapter)
    verses = [int(key.split('.')[1]) for key in audio_index if key.startswith(chapter_str + '.')]
    return max(verses) if verses else 1

def get_audio_url(chapter, verse, quarter=None, style=None):
    key = f"{chapter}.{verse}"
    if key not in audio_index:
        print(f"Error: No audio entry for {key}")
        return None
    
    entry = audio_index[key]
    if quarter:
        if quarter == 'pada1':
            return f"{AUDIO_BASE_URL}{entry['quarter']}"
        elif quarter == 'pada3':
            # Assume third quarter is same as first with '3' suffix
            quarter_path = entry['quarter'].replace('.mp3', '3.mp3')
            return f"{AUDIO_BASE_URL}{quarter_path}"
    elif style:
        if style == 'gurudatta':
            return f"{AUDIO_BASE_URL}{entry['full']}"
        elif style == 'sringeri':
            # Assume Sringeri style replaces .mp3 with .mp4
            sringeri_path = entry['full'].replace('.mp3', '.mp4').replace('AudioFull', 'AudioFullSringeri')
            return f"{AUDIO_BASE_URL}{sringeri_path}"
    return None

@app.route('/webhook', methods=['POST'])
def webhook():
    req = request.get_json(silent=True, force=True)
    intent_name = req.get('queryResult', {}).get('intent', {}).get('displayName', '')
    parameters = req.get('queryResult', {}).get('parameters', {})
    session = req.get('session', '')

    response = {'fulfillmentText': 'Processing request...'}

    # Handle ZeroIntent (Get Random Shloka Q1 or Q1/Q3)
    if intent_name == 'ZeroIntent':
        quarter = parameters.get('quarter', 'pada1')
        if quarter == 'pada1_or_pada3':
            quarter = random.choice(['pada1', 'pada3'])
        
        chapter = random.randint(1, 18)
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
                        'chapter': chapter,
                        'verse': verse,
                        'quarter': quarter
                    }
                }
            ]
        else:
            response['fulfillmentText'] = f"Sorry, audio not found for Chapter {chapter}, Verse {verse}."

    # Handle FullIntent (Get Full Shloka)
    elif intent_name == 'FullIntent':
        style = parameters.get('style', 'gurudatta')
        context = next((ctx for ctx in req.get('queryResult', {}).get('outputContexts', []) if 'shloka-context' in ctx.get('name', '')), None)
        context_params = context.get('parameters', {}) if context else {}
        
        if not context_params or not context_params.get('chapter') or not context_params.get('verse'):
            response['fulfillmentText'] = "Please select a shloka first"
        else:
            current_chapter = int(context_params['chapter'])
            current_verse = int(context_params['verse'])
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
                            'chapter': current_chapter,
                            'verse': current_verse,
                            'style': style
                        }
                    }
                ]
            else:
                response['fulfillmentText'] = f"Sorry, full shloka audio not found for Chapter {current_chapter}, Verse {current_verse}."

    # Handle NextIntent (Get Next Shloka)
    elif intent_name == 'NextIntent':
        context = next((ctx for ctx in req.get('queryResult', {}).get('outputContexts', []) if 'shloka-context' in ctx.get('name', '')), None)
        context_params = context.get('parameters', {}) if context else {}
        
        if not context_params or not context_params.get('chapter') or not context_params.get('verse'):
            response['fulfillmentText'] = "Please select a shloka first"
        else:
            current_chapter = int(context_params['chapter'])
            current_verse = int(context_params['verse'])
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
                            'chapter': next_chapter,
                            'verse': next_verse,
                            'quarter': current_quarter
                        }
                    }
                ]
            else:
                response['fulfillmentText'] = f"Sorry, next shloka audio not found for Chapter {next_chapter}, Verse {next_verse}."

    # Handle ChapterIntent (Select Chapter)
    elif intent_name == 'ChapterIntent':
        chapter = int(parameters.get('chapter', 1))
        pada = parameters.get('pada', 'first')
        quarter = 'pada1' if pada == 'first' else pada
        
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
                        'chapter': chapter,
                        'verse': verse,
                        'quarter': quarter
                    }
                }
            ]
        else:
            response['fulfillmentText'] = f"Sorry, audio not found for Chapter {chapter}, Verse {verse}."

    return jsonify(response)

if __name__ == '__main__':
    print(f"Starting Flask on port {os.environ.get('PORT', 8080)}")
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 8080)))

