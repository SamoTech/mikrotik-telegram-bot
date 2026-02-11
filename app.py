from flask import Flask, request, jsonify
import requests, os, re
from routeros_api import RouterOsApiPool

app = Flask(__name__)
BOT_TOKEN = os.getenv('BOT_TOKEN')
ROUTER_HOST = os.getenv('ROUTER_HOST')
ROUTER_PORT = int(os.getenv('ROUTER_PORT', '8728'))
ROUTER_USER = os.getenv('ROUTER_USER')
ROUTER_PASS = os.getenv('ROUTER_PASS')

pool = RouterOsApiPool(ROUTER_HOST, username=ROUTER_USER, password=ROUTER_PASS,
                       port=ROUTER_PORT, use_ssl=False, plaintext_login=True)

# Keyboard بصيغة JSON نظيفة
KEYBOARD = {
    'keyboard': [
        [{'text': '📊 السرعات'}, {'text': '📱 الأجهزة'}],
        [{'text': '💻 الحالة'}, {'text': '🔥 الأعلى'}],
        [{'text': '🚫 حظر'}, {'text': '✅ فك حظر'}]
    ],
    'resize_keyboard': True,
    'one_time_keyboard': False
}

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    chat_id = update['message']['chat']['id']
    text = update['message']['text'].strip()
    
    try:
        api = pool.get_api()
        msg = ""
        
        if text in ['📊 السرعات', '/bandwidth', '/b']:
            queues = api.get_resource('/queue/simple').call('print')
            msg = "📊 السرعات الحالية:\n\n"
            for q in queues[:10]:
                msg += f"{q.get('name', '?')}: {q.get('rate', '0/0')}\n"
                
        elif text in ['📱 الأجهزة', '/devices', '/d']:
            all_leases = api.get_resource('/ip/dhcp-server/lease').call('print')
            active = [l for l in all_leases if l.get('status') == 'bound'][:15]
            msg = "📱 الأجهزة المتصلة:\n\n"
            for l in active:
                ip = l.get('address', '?')
                mac = l.get('mac-address', '?')[:17]
                msg += f"🟢 {mac} → {ip}\n"
                
        elif text in ['💻 الحالة', '/status', '/s']:
            res = api.get_resource('/system/resource').call('print')[0]
            msg = f"💻 الحالة:\nCPU: {res.get('cpu-load', '?')}%\nUptime: {res.get('uptime', '?')}\nFree: {res.get('free-hdd-space', '?')}MB"
            
        elif text in ['🔥 الأعلى', '/top']:
            queues = api.get_resource('/queue/simple').call('print')
            top = sorted([q for q in queues if q.get('bytes', '0') != '0'], 
                        key=lambda x: int(x.get('bytes', '0').split('/')[0] or 0), reverse=True)[:5]
            msg = "🔥 أكثر 5 استهلاك:\n\n"
            for i, q in enumerate(top, 1):
                msg += f"{i}. {q.get('name', '?')}: {q.get('bytes', '0')}\n"
                
        elif text.startswith('🚫 حظر') or text.startswith('/block'):
            ip = re.search(r'(\d+\.\d+\.\d+\.\d+)', text)
            if ip:
                api.get_resource('/ip/firewall/address-list').call('add', 
                    {'list': 'telegram-blocked', 'address': ip.group(1)})
                msg = f"🚫 {ip.group(1)} محظور!"
            else:
                msg = "❌ مثال: 🚫 حظر 192.168.1.187"
                
        elif text.startswith('✅ فك') or text.startswith('/unblock'):
            ip = re.search(r'(\d+\.\d+\.\d+\.\d+)', text)
            if ip:
                blocked = api.get_resource('/ip/firewall/address-list').call('print', 
                    {'?list': 'telegram-blocked', '?address': ip.group(1)})
                if blocked:
                    api.get_resource('/ip/firewall/address-list').call('remove', {'.id': blocked[0]['.id']})
                    msg = f"✅ {ip.group(1)} مفك حظره!"
                else:
                    msg = f"❌ {ip.group(1)} مش محظور أصلاً"
            else:
                msg = "❌ مثال: ✅ فك 192.168.1.187"
                
        else:
            msg = "👋 مرحباً! اختر من الأزرار 👇"
            
    except Exception as e:
        msg = f"❌ خطأ: {str(e)}"
    
    # Send مع keyboard
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                  json={'chat_id': chat_id, 'text': msg, 'reply_markup': KEYBOARD})
    return jsonify(ok=True)

if __name__ == '__main__':
    print("🚀 Bot starting...")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
