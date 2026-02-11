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

KB = {'keyboard': [[{'text': 'Speed'}, {'text': 'Devices'}], [{'text': 'Status'}, {'text': 'Top5'}], [{'text': 'Backup'}, {'text': 'Logs'}]], 'resize_keyboard': True}

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    chat_id = update['message']['chat']['id']
    text = update['message']['text'].strip()
    try:
        api = pool.get_api()
        msg = ""
        if text in ['Speed', '/b']:
            q = api.get_resource('/queue/simple').call('print')
            msg = "Current Speed:

" + "
".join([f"{i.get('name','?')}: {i.get('rate','0/0')}" for i in q[:10]])
        elif text in ['Devices', '/d']:
            l = api.get_resource('/ip/dhcp-server/lease').call('print')
            a = [i for i in l if i.get('status')=='bound'][:15]
            msg = "Connected Devices:

" + "
".join([f"{i.get('mac-address','?')[:17]} -> {i.get('address','?')}" for i in a])
        elif text in ['Status', '/s']:
            r = api.get_resource('/system/resource').call('print')[0]
            msg = f"Router Status:
CPU: {r.get('cpu-load','?')}%
Uptime: {r.get('uptime','?')}"
        elif text in ['Top5', '/top']:
            q = api.get_resource('/queue/simple').call('print')
            t = []
            for i in q:
                try:
                    b = int(i.get('bytes','0/0').split('/')[1])
                    t.append((i.get('name','?'), b))
                except:
                    pass
            t.sort(key=lambda x:x[1], reverse=True)
            msg = "Top 5 Usage:

" + "
".join([f"{idx}. {n}: {b//(1024*1024)}MB" for idx,(n,b) in enumerate(t[:5],1)])
        elif text in ['Backup', '/backup']:
            import time
            n = f"bot-{int(time.time())}"
            api.get_resource('/system/backup').call('save', {'name': n})
            msg = f"Backup done: {n}.backup"
        elif text in ['Logs', '/logs']:
            lg = api.get_resource('/log').call('print')
            msg = "Last 5 logs:

" + "
".join([f"{i.get('time','?')}: {i.get('message','?')[:40]}" for i in lg[-5:]])
        elif text.startswith('block '):
            ip = text.split('block ')[1]
            api.get_resource('/ip/firewall/address-list').call('add', {'list':'blocked','address':ip})
            msg = f"Blocked {ip}"
        else:
            msg = "MikroTik Bot Ready!

Speed - Bandwidth
Devices - DHCP List
Status - Router Info
Top5 - Top Consumers
Backup - Save Config
Logs - View Logs

Commands:
block IP - Block device"
    except Exception as e:
        msg = f"Error: {str(e)}"
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", json={'chat_id':chat_id,'text':msg,'reply_markup':KB})
    return jsonify(ok=True)

if __name__ == '__main__':
    print("MikroTik Bot Started")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT',10000)))
