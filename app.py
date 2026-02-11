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

@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    update = request.get_json()
    chat_id = update['message']['chat']['id']
    text = update['message']['text'].lower().strip()
    
    try:
        api = pool.get_api()
        
        # 1. الأجهزة المتصلة
        if text in ['/devices', '/d', '/الاجهزه']:
            leases = api.get_resource('/ip/dhcp-server/lease').call('print', where=[['status', '=', 'bound']])
            blocked = api.get_resource('/ip/firewall/address-list').call('print', where=[['list', '=', 'blocked']])
            blocked_ips = {b.get('address', '') for b in blocked}
            msg = "📱 الأجهزة المتصلة (20):\n\n"
            for l in sorted(leases[:20], key=lambda x: x.get('mac-address', '')):
                ip = l.get('address', '?')
                mac = l.get('mac-address', '?')[:17]
                status = "🚫" if ip in blocked_ips else "🟢"
                msg += f"{status} {mac} → {ip}\n"
                
        # 2. أكثر الأجهزة استهلاك
        elif text in ['/top', '/top5', '/اكثر']:
            queues = api.get_resource('/queue/simple').call('print')
            top = sorted([q for q in queues if q.get('bytes', '0') != '0'], 
                        key=lambda x: int(x.get('bytes', 0).split('/')[0]), reverse=True)[:5]
            msg = "🔥 أكثر 5 أجهزة استهلاك (Bytes):\n\n"
            for i, q in enumerate(top, 1):
                msg += f"{i}. {q.get('name', '?')}: {q.get('bytes', '0')} ({q.get('rate', '0/0')})\n"
                
        # 3. حظر جهاز
        elif text.startswith('/block ') or '/حظر ' in text:
            ip_match = re.search(r'(?:/block |/حظر )(\S+)', text)
            if ip_match:
                ip = ip_match.group(1)
                api.get_resource('/ip/firewall/address-list').call('add', 
                    {'list': 'blocked-telegram', 'address': ip, 'comment': 'Bot Block'})
                msg = f"🚫 {ip} محظور (address-list=blocked-telegram)"
            else:
                msg = "❌ /block 192.168.1.187  أو /حظر 192.168.1.187"
                
        # 4. فك حظر جهاز
        elif text.startswith('/unblock ') or '/فك ' in text:
            ip_match = re.search(r'(?:/unblock |/فك )(\S+)', text)
            if ip_match:
                ip = ip_match.group(1)
                api.get_resource('/ip/firewall/address-list').call('remove', 
                    {'.id': '*'+ip+'*blocked-telegram'})
                msg = f"🟢 {ip} مفك حظره"
            else:
                msg = "❌ /unblock 192.168.1.187  أو /فك 192.168.1.187"
                
        # 5. اقتراح الحظر (أعلى 3 + block suggestion)
        elif text in ['/suggest', '/اقترح', '/اقتراح']:
            queues = api.get_resource('/queue/simple').call('print')
            top3 = sorted([q for q in queues if q.get('bytes', '0') != '0'], 
                         key=lambda x: int(x.get('bytes', 0).split('/')[0]), reverse=True)[:3]
            msg = "💡 اقتراح حظر (أعلى 3):\n\n"
            for i, q in enumerate(top3, 1):
                ip = q.get('target', '?')
                msg += f"{i}. {q.get('name', '?')} ({q.get('bytes', '0')})\n"
                msg += f"   👉 /block {ip}\n"
                
        else:
            msg = """🚀 البوت جاهز!
📱 /devices - الأجهزة المتصلة
🔥 /top - أكثر استهلاك
🚫 /block IP - حظر
🟢 /unblock IP - فك حظر
💡 /اقتراح - اقتراح حظر
/s - Status"""
            
    except Exception as e:
        msg = f"❌ خطأ: {str(e)}"
    
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                  json={'chat_id': chat_id, 'text': msg, 'parse_mode': 'HTML'})
    return jsonify(ok=True)

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
