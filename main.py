from flask import Flask, jsonify
import base64
import json
import requests

app = Flask(__name__)

BASE_KEY = "c!xZj+N9&G@Ev@vw"
HEADERS = {"User-Agent": "okhttp/4.12.0"}

def decrypt(enc, key):
    try:
        decoded = base64.b64decode(enc).decode("ascii")
        result = ""
        for i in range(len(decoded)):
            result += chr(ord(decoded[i]) ^ ord(key[i % len(key)]))
        return result
    except:
        return None

def fetch_and_decrypt(url):
    r = requests.get(url, headers=HEADERS)
    timestamp = r.headers.get("t", "")
    full_key = BASE_KEY + timestamp
    decrypted = decrypt(r.text, full_key)
    if decrypted:
        return json.loads(decrypted)
    return None

@app.route('/categories')
def get_categories():
    data = fetch_and_decrypt("http://a2.apk-api.com/api/categories")
    if data:
        return jsonify(data.get("data", []))
    return jsonify({"error": "Failed"}), 500

@app.route('/channels/<int:cat_id>')
def get_channels(cat_id):
    data = fetch_and_decrypt(f"http://a2.apk-api.com/api/categories/{cat_id}/channels")
    if data:
        return jsonify(data.get("data", []))
    return jsonify({"error": "Failed"}), 500

@app.route('/stream/<int:channel_id>')
def get_stream(channel_id):
    data = fetch_and_decrypt(f"http://a2.apk-api.com/api/channel/{channel_id}")
    if data:
        return jsonify(data.get("data", []))
    return jsonify({"error": "Failed"}), 500

@app.route('/events')
def get_events():
    data = fetch_and_decrypt("http://a2.apk-api.com/api/events")
    if data:
        return jsonify(data.get("data", []))
    return jsonify({"error": "Failed"}), 500

@app.route('/event/<int:event_id>')
def get_event(event_id):
    data = fetch_and_decrypt(f"http://a2.apk-api.com/api/event/{event_id}")
    if data:
        return jsonify(data.get("data", []))
    return jsonify({"error": "Failed"}), 500

@app.route('/verify/<int:channel_id>')
def verify_stream(channel_id):
    data = fetch_and_decrypt(f"http://a2.apk-api.com/api/channel/{channel_id}")
    if not data:
        return jsonify({"error": "Failed"}), 500
    streams = data.get("data", [])
    results = []
    for s in streams:
        url = s.get("url", "")
        try:
            r = requests.head(url, headers={
                "Referer": "https://x.com/",
                "User-Agent": s.get("user_agent", "")
            }, timeout=5)
            results.append({"name": s.get("name"), "url": url, "status": r.status_code})
        except Exception as e:
            results.append({"name": s.get("name"), "url": url, "status": str(e)})
    return jsonify(results)

@app.route('/test')
def test():
    return jsonify({"status": "ok", "message": "Yacine API running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
