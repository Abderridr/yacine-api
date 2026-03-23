from flask import Flask, jsonify
import base64
import json
import requests
from datetime import datetime, timezone, timedelta
import time

app = Flask(__name__)

BASE_KEY = "c!xZj+N9&G@Ev@vw"
HEADERS = {"User-Agent": "okhttp/4.12.0"}

cache = {}
CACHE_TTL = 300  # 5 minutes

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
    now = time.time()
    if url in cache and now - cache[url]['time'] < CACHE_TTL:
        return cache[url]['data']
    r = requests.get(url, headers=HEADERS)
    timestamp = r.headers.get("t", "")
    full_key = BASE_KEY + timestamp
    decrypted = decrypt(r.text, full_key)
    if decrypted:
        result = json.loads(decrypted)
        cache[url] = {'data': result, 'time': now}
        return result
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
    # Don't cache streams — tokens expire quickly
    r = requests.get(f"http://a2.apk-api.com/api/channel/{channel_id}", headers=HEADERS)
    timestamp = r.headers.get("t", "")
    full_key = BASE_KEY + timestamp
    decrypted = decrypt(r.text, full_key)
    if decrypted:
        result = json.loads(decrypted)
        return jsonify(result.get("data", []))
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

@app.route('/config')
def get_config():
    return jsonify({
        "mode": "scores",  # change to "scores" to disable streaming
        "show_ads": True,
        "maintenance": True,
        "maintenance_message": "التطبيق تحت الصيانة، نعود قريباً",
        "latest_version": "1.0.0",
        "update_url": "https://github.com/abderridr/ursport-app/releases/download/v1.0.0/app-arm64-v8a-release.apk",
        "update_required": False
    })

@app.route('/matches/today')
def get_today_matches():
    data = fetch_and_decrypt("http://a2.apk-api.com/api/events")
    if not data:
        return jsonify({"error": "Failed"}), 500
    events = data.get("data", [])
    today = datetime.now(timezone.utc).date()
    today_matches = [e for e in events if datetime.fromtimestamp(e.get("start_time", 0), tz=timezone.utc).date() == today]
    if not today_matches:
        today_matches = sorted(events, key=lambda x: x.get("start_time", 0), reverse=True)
    return jsonify(today_matches)

@app.route('/matches/tomorrow')
def get_tomorrow_matches():
    data = fetch_and_decrypt("http://a2.apk-api.com/api/events")
    if not data:
        return jsonify({"error": "Failed"}), 500
    events = data.get("data", [])
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()
    tomorrow_matches = [e for e in events if datetime.fromtimestamp(e.get("start_time", 0), tz=timezone.utc).date() == tomorrow]
    return jsonify(tomorrow_matches)

@app.route('/debug/events')
def debug_events():
    data = fetch_and_decrypt("http://a2.apk-api.com/api/events")
    if not data:
        return jsonify({"error": "Failed"}), 500
    events = data.get("data", [])
    debug = []
    for event in events:
        start_time = event.get("start_time", 0)
        if start_time:
            dt = datetime.fromtimestamp(start_time, tz=timezone.utc)
            debug.append({
                "name": f"{event.get('team_1', {}).get('name')} vs {event.get('team_2', {}).get('name')}",
                "start_time_raw": start_time,
                "date_utc": dt.strftime("%Y-%m-%d"),
                "time_utc": dt.strftime("%H:%M")
            })
    return jsonify({
        "server_today_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d"),
        "events": debug
    })

@app.route('/verify/<int:channel_id>')
def verify_stream(channel_id):
    r = requests.get(f"http://a2.apk-api.com/api/channel/{channel_id}", headers=HEADERS)
    timestamp = r.headers.get("t", "")
    full_key = BASE_KEY + timestamp
    decrypted = decrypt(r.text, full_key)
    if not decrypted:
        return jsonify({"error": "Failed"}), 500
    streams = json.loads(decrypted).get("data", [])
    results = []
    for s in streams:
        url = s.get("url", "")
        try:
            r2 = requests.head(url, headers={
                "Referer": "https://x.com/",
                "User-Agent": s.get("user_agent", "")
            }, timeout=5, allow_redirects=True)
            results.append({"name": s.get("name"), "url": url, "status": r2.status_code})
        except Exception as e:
            results.append({"name": s.get("name"), "url": url, "status": str(e)})
    return jsonify(results)

@app.route('/test')
def test():
    return jsonify({"status": "ok", "message": "Yacine API running"})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
