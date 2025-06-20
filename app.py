# ─── app.py ─────────────────────────────────────────────────────────────
from flask import Flask, request, jsonify
from flask_cors import CORS
import json, random, re, os, sys

app = Flask(__name__)
CORS(app)                                       # allow calls from any origin

# ── Load index and tag quarter number (1‑4) ─────────────────────────────
try:
    with open("gita_audio_index.json", encoding="utf-8") as f:
        index = json.load(f)
except FileNotFoundError:
    sys.exit("❌ gita_audio_index.json not found; aborting.")

def qnum(path: str) -> int:
    """
    Extract quarter number (1‑4) regardless of OS path style.
    Example “…/Chapter 5/27.3.mp3” → 3
    """
    m = re.search(r"[./]([1-4])\.mp3$", path)
    return int(m.group(1)) if m else 1

for e in index:
    e["qnum"] = qnum(e["quarter"])

quarter_13 = [e for e in index if e["qnum"] in (1, 3)]
full_lookup = {(e["chapter"], e["verse"]): e for e in index}

def next_full(ch: int, vs: int):
    """Return the next verse (full) looping ch=18→1"""
    while True:
        vs += 1
        if (ch, vs) in full_lookup:
            return full_lookup[(ch, vs)]
        # reached end of chapter – wrap
        ch, vs = (ch + 1, 0) if ch < 18 else (1, 0)

# ── Webhook route ───────────────────────────────────────────────────────
@app.route("/webhook", methods=["POST"])
def webhook():
    req = request.get_json(force=True)
    intent = req["queryResult"]["intent"]["displayName"]

    # Pull last context (chapter+verse)
    ctxs = {c["name"].split("/")[-1]: c for c in
            req["queryResult"].get("outputContexts", [])}
    last = ctxs.get("lastshloka", {}).get("parameters", {})

    if intent == "ZeroIntent":
        entry = random.choice(quarter_13)

    elif intent == "ChapterIntent":
        chap = int(req["queryResult"]["parameters"].get("chapter", 1))
        cand = [e for e in quarter_13 if e["chapter"] == chap] or quarter_13
        entry = random.choice(cand)

    elif intent == "FullIntent":
        chap = int(last.get("chapter", 1))
        vs   = int(last.get("verse",   1))
        entry = full_lookup.get((chap, vs), random.choice(index))
        return respond(entry, entry["full"])

    elif intent == "NextIntent":
        chap = int(last.get("chapter", 1))
        vs   = int(last.get("verse",   1))
        entry = next_full(chap, vs)
        return respond(entry, entry["full"])

    else:
        return jsonify({"fulfillmentText": "Sorry, I didn’t understand."})

    return respond(entry, entry["quarter"])   # default = pada 1/3

# ── Common response helper ──────────────────────────────────────────────
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
                        {"mediaResponse": {
                             "mediaType": "AUDIO",
                             "mediaObjects": [{
                                 "name": text,
                                 "contentUrl": audio_url
                             }]
                        }}
                    ]
                }
            }
        },
        "outputContexts": [{
            "name": f"{request.json['session']}/contexts/lastshloka",
            "lifespanCount": 5,
            "parameters": {"chapter": entry["chapter"], "verse": entry["verse"]}
        }]
    })

if __name__ == "__main__":
    port = int(os.environ.get("PORT", 8080))
    app.run(host="0.0.0.0", port=port)
