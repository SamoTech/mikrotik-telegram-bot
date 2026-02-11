from flask import Flask, request, jsonify
import requests, os, re
from routeros_api import RouterOsApiPool
from telegram import ReplyKeyboardMarkup  # pip install python-telegram-bot

app = Flask(__name__)
BOT_TOKEN = os.getenv('BOT_TOKEN')
ROUTER_HOST = os.getenv('ROUTER_HOST')
ROUTER_PORT = int(os.getenv('ROUTER_PORT', '8728'))
ROUTER_USER = os.getenv('ROUTER_USER')
ROUTER_PASS = os.getenv('ROUTER_PASS')

pool = RouterOsApiPool(ROUTER_HOST, username=ROUTER_USER, password=ROUTER_PASS,
                       port=ROUTER_PORT, use_ssl=False, plaintext_login=True)

KEYBOARD = ReplyKeyboardMarkup([
    ['📊 /bandwidth', '📱 /devices'],
    ['💻 /status', '🔄 /reboot'],
    ['🚫 /block IP', '✅ /unblock IP']
], resize_keyboard=True, one_time_keyboard=False)

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    chat_id = update['message']['chat']['id']
    text = update['message']['text'].strip()
    
    try:
        api = pool.get_api()
        msg = ""
        reply_markup = KEYBOARD
        
        if text in ['/bandwidth', '📊 /bandwidth', '/b']:
            queues = api.get_resource('/queue/simple').call('print')
            msg = "📊 السرعات الحالية:\n\n"
            for q in queues[:10]:
                msg += f"{q.get('name', '?')}: {q.get('rate', '0/0')}\n"
                
        elif text in ['/devices', '📱 /devices', '/d']:
            all_leases = api.get_resource('/ip/dhcp-server/lease').call('print')
            active = [l for l in all_leases if l.get('status') == 'bound'][:15]
            msg = "📱 الأجهزة المتصلة:\n\n"
            for l in active:
                ip, mac = l.get('address', '?'), l.get('mac-address', '?')[:17]
                msg += f"🟢 {mac} → {ip}\n"
                
        elif text in ['/status', '💻 /status', '/s']:
            res = api.get_resource('/system/resource').call('print')[0]
            msg = f"💻 الحالة:\nCPU: {res.get('cpu-load', '?')}%\nUptime: {res.get('uptime', '?')}\nFree: {res.get('free-hdd-space', '?')}MB"
            
        elif text == '🔄 /reboot':
            api.get_resource('/system/reboot').call('reboot')
            msg = "🔄 الراوتر بيعمل reboot... (5 دقايق)"
            
        elif text.startswith('🚫 /block') or text.startswith('/block'):
            ip = re.search(r'(\d+\.\d+\.\d+\.\d+)', text)
            if ip:
                api.get_resource('/ip/firewall/address-list').call('add', 
                    {'list': 'telegram-blocked', 'address': ip.group(1)})
                msg = f"🚫 {ip.group(1)} محظور!"
            else:
                msg = "❌ اكتب: 🚫 /block 192.168.1.XXX"
                
        elif text.startswith('✅ /unblock') or text.startswith('/unblock'):
            ip = re.search(r'(\d+\.\d+\.\d+\.\d+)', text)
            if ip:
                api.get_resource('/ip/firewall/address-list').call('remove', 
                    {'.id': '*'+ip.group(1)})
                msg = f"✅ {ip.group(1)} مفك حظره!"
            else:
                msg = "❌ اكتب: ✅ /unblock 192.168.1.XXX"
                
        else:
            msg = "👋 البوت جاهز!\nاضغط أي زر تحت 👇"
            
    except Exception as e:
        msg = f"❌ خطأ: {str(e)}"
        reply_markup = None
    
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                  json={'chat_id': chat_id, 'text': msg, 'reply_markup': reply_markup})
    return jsonify(ok=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
