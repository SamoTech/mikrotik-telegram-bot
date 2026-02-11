from flask import Flask, request, jsonify
import requests, os, re
from routeros_api import RouterOsApiPool

app = Flask(__name__)
BOT_TOKEN = os.getenv('BOT_TOKEN')
ROUTER_HOST = os.getenv('ROUTER_HOST')
ROUTER_PORT = int(os.getenv('ROUTER_PORT', '8728'))
ROUTER_USER = os.getenv('ROUTER_USER')
ROUTER_PASS = os.getenv('ROUTER_PASS')

pool = RouterOsApiPool(ROUTER_HOST, username=ROUTER_USER, password=ROUTER_PASS, port=ROUTER_PORT, use_ssl=False, plaintext_login=True)

KEYBOARD = {'keyboard': [[{'text': 'السرعات'}, {'text': 'الأجهزة'}], [{'text': 'الحالة'}, {'text': 'الأعلى'}], [{'text': 'Scripts'}, {'text': 'Backup'}]], 'resize_keyboard': True}

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    chat_id = update['message']['chat']['id']
    text = update['message']['text'].strip()
    try:
        api = pool.get_api()
        msg = ""
        if text in ['السرعات', '/b']:
            queues = api.get_resource('/queue/simple').call('print')
            msg = "السرعات الحالية:

"
            for q in queues[:10]:
                msg += q.get('name', '?') + ": " + q.get('rate', '0/0') + "
"
        elif text in ['الأجهزة', '/d']:
            leases = api.get_resource('/ip/dhcp-server/lease').call('print')
            active = [l for l in leases if l.get('status') == 'bound'][:15]
            msg = "الأجهزة المتصلة:

"
            for l in active:
                msg += l.get('mac-address', '?')[:17] + " -> " + l.get('address', '?') + "
"
        elif text in ['الحالة', '/s']:
            res = api.get_resource('/system/resource').call('print')[0]
            msg = "حالة الراوتر:
CPU: " + str(res.get('cpu-load', '?')) + "%
Uptime: " + str(res.get('uptime', '?'))
        elif text in ['الأعلى', '/top']:
            queues = api.get_resource('/queue/simple').call('print')
            top = []
            for q in queues:
                try:
                    down = int(q.get('bytes', '0/0').split('/')[1])
                    top.append((q.get('name', '?'), down))
                except:
                    pass
            top.sort(key=lambda x: x[1], reverse=True)
            msg = "أعلى 5 استهلاك:

"
            for i, (name, b) in enumerate(top[:5], 1):
                msg += str(i) + ". " + name + ": " + str(b//(1024*1024)) + "MB
"
        elif text == '/run_auto':
            api.get_resource('/system/script').call('run', {'number': 'auto-queue-dhcp'})
            msg = "تم تشغيل auto-queue"
        elif text == '/logs':
            logs = api.get_resource('/log').call('print')
            msg = "آخر 5 logs:

"
            for log in logs[-5:]:
                msg += log.get('time', '?') + ": " + log.get('message', '?')[:40] + "
"
        elif text == 'Backup':
            import time
            name = "bot-" + str(int(time.time()))
            api.get_resource('/system/backup').call('save', {'name': name})
            msg = "Backup تم: " + name + ".backup"
        elif text.startswith('block '):
            ip = text.split('block ')[1]
            api.get_resource('/ip/firewall/address-list').call('add', {'list': 'blocked', 'address': ip})
            msg = "تم حظر " + ip
        else:
            msg = "البوت جاهز!

السرعات - Bandwidth
الأجهزة - Devices
الحالة - Status
الأعلى - Top 5
Backup - نسخ احتياطي

أوامر: /logs /run_auto
block IP - حظر"
    except Exception as e:
        msg = "خطأ: " + str(e)
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={'chat_id': chat_id, 'text': msg, 'reply_markup': KEYBOARD})
    return jsonify(ok=True)

if __name__ == '__main__':
    print("Bot started")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
