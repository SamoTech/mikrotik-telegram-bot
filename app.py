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

# Keyboard شامل
KEYBOARD = {
    'keyboard': [
        [{'text': '📊 السرعات'}, {'text': '📱 الأجهزة'}],
        [{'text': '💻 الحالة'}, {'text': '🔥 الأعلى'}],
        [{'text': '📜 Scripts'}, {'text': '🔐 الأمان'}],
        [{'text': '💾 Backup'}, {'text': '🚫 حظر'}]
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
        
        # 1. السرعات (bandwidth-monitor)
        if text in ['📊 السرعات', '/bandwidth', '/b']:
            queues = api.get_resource('/queue/simple').call('print', {'?parent': 'WiFi-Parent'})
            msg = "📊 مراقبة السرعات:

"
            for q in queues[:10]:
                name = q.get('name', '?')
                rate = q.get('rate', '0/0')
                msg += f"{name}: {rate}
"
                
        # 2. الأجهزة (show-all-devices)
        elif text in ['📱 الأجهزة', '/devices', '/d']:
            leases = api.get_resource('/ip/dhcp-server/lease').call('print', {'?status': 'bound'})
            msg = "📱 الأجهزة المتصلة:

"
            for l in leases[:20]:
                ip = l.get('address', '?')
                mac = l.get('mac-address', '?')[:17]
                hostname = l.get('host-name', 'Unknown')
                msg += f"🟢 {mac}
   IP: {ip}
   Name: {hostname}

"
                
        # 3. الحالة (system resource)
        elif text in ['💻 الحالة', '/status', '/s']:
            res = api.get_resource('/system/resource').call('print')[0]
            uptime = res.get('uptime', '?')
            cpu = res.get('cpu-load', '?')
            mem_total = res.get('total-memory', 0)
            mem_free = res.get('free-memory', 0)
            mem_used = int(mem_total) - int(mem_free) if mem_total and mem_free else 0
            hdd = res.get('free-hdd-space', '?')
            msg = f"💻 حالة الراوتر:

CPU: {cpu}%
Uptime: {uptime}
RAM Used: {mem_used//1024}MB
HDD Free: {hdd}"
                
        # 4. الأعلى استهلاك
        elif text in ['🔥 الأعلى', '/top']:
            queues = api.get_resource('/queue/simple').call('print')
            # Sort بـ bytes downloaded
            top = []
            for q in queues:
                bytes_str = q.get('bytes', '0/0')
                try:
                    down_bytes = int(bytes_str.split('/')[1])
                    top.append((q.get('name', '?'), down_bytes, q.get('rate', '0/0')))
                except:
                    pass
            top.sort(key=lambda x: x[1], reverse=True)
            msg = "🔥 أعلى 5 استهلاك:

"
            for i, (name, bytes_val, rate) in enumerate(top[:5], 1):
                mb = bytes_val / (1024*1024)
                msg += f"{i}. {name}
   {mb:.1f}MB | {rate}

"
                
        # 5. Scripts Menu
        elif text in ['📜 Scripts', '/scripts']:
            msg = """📜 Scripts المتاحة:

/run_bandwidth - مراقبة لايف
/run_auto_queue - إنشاء queues تلقائي
/run_cleanup - حذف queues القديمة
/scheduler - حالة المجدولات
/logs - آخر 10 logs"""
            
        # 6. Run bandwidth-monitor
        elif text == '/run_bandwidth':
            api.get_resource('/system/script').call('run', {'number': 'bandwidth-monitor'})
            msg = "✅ تم تشغيل bandwidth-monitor!
استخدم 📊 السرعات لعرض النتيجة"
            
        # 7. Run auto-queue
        elif text == '/run_auto_queue':
            api.get_resource('/system/script').call('run', {'number': 'auto-queue-dhcp'})
            msg = "✅ تم تشغيل auto-queue-dhcp!
جارٍ إنشاء queues للأجهزة الجديدة..."
            
        # 8. Run cleanup
        elif text == '/run_cleanup':
            api.get_resource('/system/script').call('run', {'number': 'cleanup-old-queues'})
            msg = "✅ تم تشغيل cleanup!
تم حذف queues الأجهزة غير المتصلة"
            
        # 9. Scheduler Status
        elif text == '/scheduler':
            schedulers = api.get_resource('/system/scheduler').call('print')
            msg = "⏰ المجدولات:

"
            for s in schedulers:
                name = s.get('name', '?')
                interval = s.get('interval', '?')
                start = s.get('start-time', '?')
                msg += f"▪️ {name}
  كل {interval} | بدء {start}

"
                
        # 10. Logs
        elif text == '/logs':
            logs = api.get_resource('/log').call('print')
            msg = "📋 آخر 10 logs:

"
            for log in logs[-10:]:
                time = log.get('time', '?')
                message = log.get('message', '?')[:50]
                msg += f"{time}: {message}
"
                
        # 11. الأمان (Firewall)
        elif text in ['🔐 الأمان', '/security']:
            filters = api.get_resource('/ip/firewall/filter').call('print', {'?chain': 'input'})
            msg = "🔐 قواعد الأمان:

"
            for f in filters[:10]:
                chain = f.get('chain', '?')
                action = f.get('action', '?')
                port = f.get('dst-port', 'any')
                comment = f.get('comment', '')
                msg += f"▪️ {action.upper()} port {port}
  {comment}

"
                
        # 12. Backup
        elif text in ['💾 Backup', '/backup']:
            import time
            backup_name = f"telegram-{int(time.time())}"
            api.get_resource('/system/backup').call('save', {'name': backup_name})
            msg = f"💾 Backup تم!

الاسم: {backup_name}.backup
حمّله من: WinBox → Files"
            
        # 13. حظر جهاز
        elif text in ['🚫 حظر', '/block']:
            msg = """🚫 لحظر جهاز:

أرسل: block 192.168.1.XXX

مثال:
block 192.168.1.187

أو استخدم 📱 الأجهزة لرؤية IPs"""
            
        elif text.startswith('block '):
            ip = text.split('block ')[1].strip()
            if re.match(r'^d+.d+.d+.d+$', ip):
                api.get_resource('/ip/firewall/address-list').call('add', 
                    {'list': 'telegram-blocked', 'address': ip, 'comment': 'Bot block'})
                msg = f"🚫 تم حظر {ip}!"
            else:
                msg = "❌ IP غير صحيح"
                
        # 14. فك حظر
        elif text.startswith('unblock '):
            ip = text.split('unblock ')[1].strip()
            blocked = api.get_resource('/ip/firewall/address-list').call('print', 
                {'?list': 'telegram-blocked', '?address': ip})
            if blocked:
                api.get_resource('/ip/firewall/address-list').call('remove', {'.id': blocked[0]['.id']})
                msg = f"✅ تم فك حظر {ip}!"
            else:
                msg = f"❌ {ip} غير محظور"
                
        # 15. Export Config
        elif text == '/export':
            msg = """📤 لتصدير الإعداد:

1. SSH: ssh admin@192.168.1.1
2. أمر: /export file=config-backup
3. حمّل: WinBox → Files

أو استخدم /backup للنسخ الاحتياطي"""
            
        # 16. Help/Start
        else:
            msg = """👋 بوت MikroTik جاهز!

📊 السرعات - مراقبة Bandwidth
📱 الأجهزة - كل الأجهزة المتصلة
💻 الحالة - حالة الراوتر
🔥 الأعلى - أكثر استهلاك
📜 Scripts - تشغيل Scripts
🔐 الأمان - Firewall Rules
💾 Backup - نسخ احتياطي
🚫 حظر - حظر/فك حظر

أوامر سريعة:
/logs - عرض Logs
/scheduler - المجدولات
/export - تصدير Config"""
            
    except Exception as e:
        msg = f"❌ خطأ: {str(e)}

تأكد من:
- API port 8728 مفتوح
- Scripts موجودة بالراوتر"
    
    # إرسال الرد
    requests.post(f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage", 
                  json={'chat_id': chat_id, 'text': msg, 'reply_markup': KEYBOARD})
    return jsonify(ok=True)

if __name__ == '__main__':
    print("🚀 MikroTik Bot started - Full version")
    app.run(host='0.0.0.0', port=int(os.getenv('PORT', 10000)))
