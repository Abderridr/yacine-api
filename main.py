from flask import Flask, jsonify
import base64
import json
import requests
from datetime import datetime, timezone, timedelta
import time
import logging

app = Flask(__name__)
logging.basicConfig(level=logging.INFO)

BASE_KEY = "c!xZj+N9&G@Ev@vw"
HEADERS = {"User-Agent": "okhttp/4.12.0"}

cache = {}
CACHE_TTL = 300  # 5 minutes

def decrypt(enc, key):
    try:
        decoded = base64.b64decode(enc).decode("ascii")
        result = []
        key_len = len(key)
        for i, char in enumerate(decoded):
            result.append(chr(ord(char) ^ ord(key[i % key_len])))
        return "".join(result)
    except Exception as e:
        logging.error(f"Decryption failed: {e}")
        return None

def fetch_and_decrypt(url, use_cache=True):
    now = time.time()
    
    if use_cache and url in cache and now - cache[url]['time'] < CACHE_TTL:
        return cache[url]['data']
    
    try:
        r = requests.get(url, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        logging.error(f"Request failed for {url}: {e}")
        return None
    
    timestamp = r.headers.get("t", "")
    full_key = BASE_KEY + timestamp
    decrypted = decrypt(r.text, full_key)
    
    if not decrypted:
        return None
    
    try:
        result = json.loads(decrypted)
    except json.JSONDecodeError as e:
        logging.error(f"JSON parse failed: {e}")
        return None
    
    if use_cache:
        cache[url] = {'data': result, 'time': now}
    
    return result

@app.route('/categories')
def get_categories():
    data = fetch_and_decrypt("http://a2.apk-api.com/api/categories")
    if data:
        return jsonify(data.get("data", []))
    return jsonify({"error": "Failed to fetch categories"}), 500

@app.route('/channels/<int:cat_id>')
def get_channels(cat_id):
    data = fetch_and_decrypt(f"http://a2.apk-api.com/api/categories/{cat_id}/channels")
    if data:
        return jsonify(data.get("data", []))
    return jsonify({"error": "Failed to fetch channels"}), 500

@app.route('/stream/<int:channel_id>')
def get_stream(channel_id):
    # Don't cache streams — tokens expire quickly
    r = requests.get(f"http://a2.apk-api.com/api/channel/{channel_id}", headers=HEADERS, timeout=10)
    timestamp = r.headers.get("t", "")
    full_key = BASE_KEY + timestamp
    decrypted = decrypt(r.text, full_key)
    
    if decrypted:
        try:
            result = json.loads(decrypted)
            return jsonify(result.get("data", []))
        except json.JSONDecodeError:
            return jsonify({"error": "Invalid stream data"}), 500
    
    return jsonify({"error": "Failed to fetch stream"}), 500

@app.route('/events')
def get_events():
    data = fetch_and_decrypt("http://a2.apk-api.com/api/events")
    if data:
        return jsonify(data.get("data", []))
    return jsonify({"error": "Failed to fetch events"}), 500

@app.route('/event/<int:event_id>')
def get_event(event_id):
    data = fetch_and_decrypt(f"http://a2.apk-api.com/api/event/{event_id}")
    if data:
        return jsonify(data.get("data", []))
    return jsonify({"error": "Failed to fetch event"}), 500

@app.route('/config')
def get_config():
    return jsonify({
        "mode": "streaming",
        "show_ads": True,
        "maintenance": False,
        "maintenance_message": "التطبيق تحت الصيانة، نعود قريباً",
        "latest_version": "1.0.0",
        "update_url": "https://github.com/abderridr/ursport-app/releases/download/v1.0.0/app-arm64-v8a-release.apk",
        "update_required": False
    })

@app.route('/matches/today')
def get_today_matches():
    data = fetch_and_decrypt("http://a2.apk-api.com/api/events")
    if not data:
        return jsonify({"error": "Failed to fetch matches"}), 500
    
    events = data.get("data", [])
    today = datetime.now(timezone.utc).date()
    today_matches = [
        e for e in events 
        if datetime.fromtimestamp(e.get("start_time", 0), tz=timezone.utc).date() == today
    ]
    
    if not today_matches:
        today_matches = sorted(events, key=lambda x: x.get("start_time", 0), reverse=True)
    
    return jsonify(today_matches)

@app.route('/matches/tomorrow')
def get_tomorrow_matches():
    data = fetch_and_decrypt("http://a2.apk-api.com/api/events")
    if not data:
        return jsonify({"error": "Failed to fetch matches"}), 500
    
    events = data.get("data", [])
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).date()
    tomorrow_matches = [
        e for e in events 
        if datetime.fromtimestamp(e.get("start_time", 0), tz=timezone.utc).date() == tomorrow
    ]
    
    return jsonify(tomorrow_matches)

@app.route('/debug/events')
def debug_events():
    data = fetch_and_decrypt("http://a2.apk-api.com/api/events")
    if not data:
        return jsonify({"error": "Failed to fetch events"}), 500
    
    events = data.get("data", [])
    debug = []
    
    for event in events:
        start_time = event.get("start_time", 0)
        if start_time:
            dt = datetime.fromtimestamp(start_time, tz=timezone.utc)
            debug.append({
                "name": f"{event.get('team_1', {}).get('name', 'Unknown')} vs {event.get('team_2', {}).get('name', 'Unknown')}",
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
    r = requests.get(f"http://a2.apk-api.com/api/channel/{channel_id}", headers=HEADERS, timeout=10)
    timestamp = r.headers.get("t", "")
    full_key = BASE_KEY + timestamp
    decrypted = decrypt(r.text, full_key)
    
    if not decrypted:
        return jsonify({"error": "Failed to decrypt stream data"}), 500
    
    try:
        streams = json.loads(decrypted).get("data", [])
    except json.JSONDecodeError:
        return jsonify({"error": "Invalid stream data"}), 500
    
    results = []
    for s in streams:
        url = s.get("url", "")
        if not url:
            continue
            
        try:
            r2 = requests.head(url, headers={
                "Referer": "https://x.com/",
                "User-Agent": s.get("user_agent", HEADERS["User-Agent"])
            }, timeout=5, allow_redirects=True)
            results.append({
                "name": s.get("name", "Unknown"),
                "url": url,
                "status": r2.status_code,
                "ok": r2.status_code < 400
            })
        except Exception as e:
            results.append({
                "name": s.get("name", "Unknown"),
                "url": url,
                "status": str(e),
                "ok": False
            })
    
    return jsonify(results)

@app.route('/test')
def test():
    return jsonify({
        "status": "ok",
        "message": "Yacine API running",
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

@app.route('/health')
def health():
    return jsonify({
        "status": "healthy",
        "cache_entries": len(cache),
        "timestamp": datetime.now(timezone.utc).isoformat()
    })

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
