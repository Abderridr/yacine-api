from flask import Flask, jsonify
import requests

app = Flask(__name__)

HEADERS = {
    'Accept': 'application/json',
    'Connection': 'Keep-Alive',
    'Accept-Encoding': 'gzip',
    'User-Agent': 'okhttp/4.12.0'
}

@app.route('/event/<event_id>')
def get_event(event_id):
    url = f'http://a2.apk-api.com/api/event/{event_id}'
    res = requests.get(url, headers=HEADERS)
    try:
        return jsonify(res.json())
    except:
        return jsonify({'raw': res.text, 'status': res.status_code})

@app.route('/config')
def get_config():
    url = 'http://a2.apk-api.com/api/config/player'
    res = requests.get(url, headers=HEADERS)
    try:
        return jsonify(res.json())
    except:
        return jsonify({'raw': res.text, 'status': res.status_code})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=3000)
