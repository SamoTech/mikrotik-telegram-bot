from flask import Flask, request, jsonify
import requests, os
try:
    from routeros_api import RouterOsApiPool
except ImportError:
    RouterOsApiPool = None

app = Flask(__name__)

BOT_TOKEN = os.getenv('BOT_TOKEN')
ROUTER_HOST = os.getenv('ROUTER_HOST', 'hcr080ahqtv.sn.mynetname.net')
ROUTER_PORT = int(os.getenv('ROUTER_PORT', '8728'))
ROUTER_USER = os.getenv('ROUTER_USER', 'admin')
ROUTER_PASS = os.getenv('ROUTER_PASS')

if not BOT_TOKEN or not RouterOsApiPool:
    @app.route('/')
    def home(): return "Bot ready - check logs", 200
else:
    pool = RouterOsApiPool(ROUTER_HOST, username=ROUTER_USER, password=ROUTER_PASS,
                           port=ROUTER_PORT, use_ssl=False, plaintext_login=True)

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    chat_id = update['message']['chat']['id']
    text = update['message']['text'].lower()
    
    try:
        if not RouterOsApiPool:
            msg = "❌ Install routeros-api==0.21.0"
        else:
            api = pool.get_api()
            if '/bandwidth' in text or text == '/b':
                queues = api.get_resource('/queue/simple').call('print')
                msg = "🏆 Bandwidth:\n" + "\n".join([f"{q.get('name','?')}: {q.get('rate','0/0')}" for q in queues[:10]])
            elif '/devices' in text or text == '/d':
                leases = api.get_resource('/ip/dhcp-server/lease').call('print', where=[['status', '=', 'bound']])
                msg = "📱 Devices:\n" + "\n".join([f"{l.get('mac-address','?')}: {l.get('address','?')}" for l in leases[:12]])
            elif '/status' in text or text == '/s':
                res = api.get_resource('/system/resource').call('print')[0]
                msg = f"✅ CPU: {res.get('cpu-load','?')}%\nUptime: {res.get('uptime','?')}\nFree: {res.get('free-hdd-space','?')}MB"
            elif '/cloud' in text:
                cloud = api.get_resource('/ip/cloud').call('print')[0]
                msg = f"🌥️ {cloud.get('status','?')} | IP: {cloud.get('public-address','?')}"
            else:
                msg = "/b /d /s /cloud"
    except Exception as e:
        msg = f"❌ {str(e)}"
    
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage",
                  json={'chat_id': chat_id, 'text': msg})
    return jsonify(ok=True)

if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    print(f"🚀 Listening on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
