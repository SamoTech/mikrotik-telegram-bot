"""
MikroTik Router Telegram Bot - Render.com Optimized
Webhook-based Flask bot for managing MikroTik RouterOS
"""

from flask import Flask, request, jsonify
import requests
import os
import logging
from routeros_api import RouterOsApiPool

# ============== Configuration ==============
app = Flask(__name__)

# Environment variables
BOT_TOKEN = os.getenv('BOT_TOKEN')
ROUTER_HOST = os.getenv('ROUTER_HOST')
ROUTER_PORT = int(os.getenv('ROUTER_PORT', '8728'))
ROUTER_USER = os.getenv('ROUTER_USER')
ROUTER_PASS = os.getenv('ROUTER_PASS')
ADMIN_IDS = set(map(int, os.getenv('ADMIN_IDS', '').split(','))) if os.getenv('ADMIN_IDS') else set()

# Logging setup
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# RouterOS API Pool
try:
    pool = RouterOsApiPool(
        ROUTER_HOST,
        username=ROUTER_USER,
        password=ROUTER_PASS,
        port=ROUTER_PORT,
        use_ssl=False,
        plaintext_login=True
    )
    logger.info("RouterOS API initialized")
except Exception as e:
    logger.error(f"RouterOS API error: {e}")
    pool = None

# ============== Keyboards ==============
KB = {
    'keyboard': [
        [{'text': '📊 Speed'}, {'text': '📱 Devices'}],
        [{'text': '⚙️ Status'}, {'text': '🔥 Top5'}],
        [{'text': '🗂️ Backup'}, {'text': '📝 Logs'}],
        [{'text': '📈 Traffic'}, {'text': '❓ Help'}]
    ],
    'resize_keyboard': True
}

ADMIN_KB = {
    'keyboard': [
        [{'text': '📊 Speed'}, {'text': '📱 Devices'}],
        [{'text': '⚙️ Status'}, {'text': '🔥 Top5'}],
        [{'text': '🗂️ Backup'}, {'text': '📝 Logs'}],
        [{'text': '📈 Traffic'}, {'text': '🚫 Firewall'}],
        [{'text': '🔒 Block IP'}, {'text': '✅ Unblock IP'}],
        [{'text': '❓ Help'}]
    ],
    'resize_keyboard': True
}

# ============== Helpers ==============
def format_bytes(b):
    """Convert bytes to human readable"""
    for unit in ['B', 'KB', 'MB', 'GB']:
        if b < 1024:
            return f"{b:.1f}{unit}"
        b /= 1024
    return f"{b:.1f}TB"

def is_admin(chat_id):
    """Check if user is admin"""
    return not ADMIN_IDS or chat_id in ADMIN_IDS

def send_message(chat_id, text, keyboard=None):
    """Send Telegram message"""
    try:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        payload = {
            'chat_id': chat_id,
            'text': text,
            'parse_mode': 'HTML'
        }
        if keyboard:
            payload['reply_markup'] = keyboard
        requests.post(url, json=payload, timeout=10)
    except Exception as e:
        logger.error(f"Send message error: {e}")

# ============== Commands ==============
def cmd_speed(chat_id):
    """Get bandwidth usage"""
    if not pool:
        return "❌ Router offline"
    try:
        api = pool.get_api()
        q = api.get_resource('/queue/simple').call('print')
        if not q:
            return "📊 No bandwidth data"
        msg = "📊 Current Bandwidth:\n\n"
        for i, item in enumerate(q[:10], 1):
            msg += f"{i}. {item.get('name','?')}: {item.get('rate','0/0')}\n"
        return msg
    except Exception as e:
        logger.error(f"Speed error: {e}")
        return f"❌ Error: {str(e)[:80]}"

def cmd_devices(chat_id):
    """Get DHCP devices"""
    if not pool:
        return "❌ Router offline"
    try:
        api = pool.get_api()
        l = api.get_resource('/ip/dhcp-server/lease').call('print')
        a = [i for i in l if i.get('status') == 'bound'][:15]
        if not a:
            return "📱 No devices connected"
        msg = f"📱 Connected Devices ({len(a)}):\n\n"
        for i, d in enumerate(a, 1):
            # Get device name from comment, or use hostname, or fallback to MAC
            name = d.get('comment', '').strip()
            if not name:
                name = d.get('host-name', '').strip()
            if not name:
                name = d.get('mac-address', '?')[:17]
            
            ip = d.get('address', '?')
            msg += f"{i}. {name} → {ip}\n"
        return msg
    except Exception as e:
        logger.error(f"Devices error: {e}")
        return f"❌ Error: {str(e)[:80]}"

def cmd_status(chat_id):
    """Get router status"""
    if not pool:
        return "❌ Router offline"
    try:
        api = pool.get_api()
        r = api.get_resource('/system/resource').call('print')[0]
        msg = "⚙️ Router Status:\n\n"
        msg += f"CPU: {r.get('cpu-load','?')}%\n"
        msg += f"Uptime: {r.get('uptime','?')}\n"
        msg += f"Memory: {r.get('total-memory','?')}\n"
        msg += f"Version: {r.get('version','?')}\n"
        return msg
    except Exception as e:
        logger.error(f"Status error: {e}")
        return f"❌ Error: {str(e)[:80]}"

def cmd_top5(chat_id):
    """Get top 5 consumers"""
    if not pool:
        return "❌ Router offline"
    try:
        api = pool.get_api()
        q = api.get_resource('/queue/simple').call('print')
        t = []
        for i in q:
            try:
                rate = i.get('rate', '0/0')
                b = int(rate.split('/')[1]) if '/' in rate else 0
                t.append((i.get('name', '?'), b))
            except:
                pass
        t.sort(key=lambda x: x[1], reverse=True)
        if not t:
            return "🔥 No data"
        msg = "🔥 Top 5 Consumers:\n\n"
        for idx, (n, b) in enumerate(t[:5], 1):
            msg += f"{idx}. {n}: {format_bytes(b)}\n"
        return msg
    except Exception as e:
        logger.error(f"Top5 error: {e}")
        return f"❌ Error: {str(e)[:80]}"

def cmd_traffic(chat_id):
    """Get interface traffic"""
    if not pool:
        return "❌ Router offline"
    try:
        api = pool.get_api()
        ifaces = api.get_resource('/interface').call('print')
        if not ifaces:
            return "📈 No interfaces"
        msg = "📈 Interface Traffic:\n\n"
        for iface in ifaces[:8]:
            name = iface.get('name', '?')
            rx = int(iface.get('rx-byte', '0'))
            tx = int(iface.get('tx-byte', '0'))
            msg += f"{name}: ↓{format_bytes(rx)} ↑{format_bytes(tx)}\n"
        return msg
    except Exception as e:
        logger.error(f"Traffic error: {e}")
        return f"❌ Error: {str(e)[:80]}"

def cmd_backup(chat_id):
    """Create backup"""
    if not pool:
        return "❌ Router offline"
    if not is_admin(chat_id):
        return "🔒 Admin only"
    try:
        import time
        api = pool.get_api()
        name = f"bot-{int(time.time())}"
        api.get_resource('/system/backup').call('save', {'name': name})
        logger.warning(f"Backup created by {chat_id}: {name}")
        return f"✅ Backup: {name}.backup"
    except Exception as e:
        logger.error(f"Backup error: {e}")
        return f"❌ Error: {str(e)[:80]}"

def cmd_logs(chat_id):
    """Get system logs"""
    if not pool:
        return "❌ Router offline"
    try:
        api = pool.get_api()
        lg = api.get_resource('/log').call('print')
        if not lg:
            return "📝 No logs"
        msg = "📝 Last Logs:\n\n"
        for log in lg[-5:]:
            t = log.get('time', '?')
            m = log.get('message', '?')[:40]
            msg += f"[{t}] {m}\n"
        return msg
    except Exception as e:
        logger.error(f"Logs error: {e}")
        return f"❌ Error: {str(e)[:80]}"

def cmd_firewall(chat_id):
    """Show firewall rules"""
    if not pool:
        return "❌ Router offline"
    if not is_admin(chat_id):
        return "🔒 Admin only"
    try:
        api = pool.get_api()
        rules = api.get_resource('/ip/firewall/filter').call('print')[:10]
        if not rules:
            return "🚫 No rules"
        msg = "🚫 Firewall Rules:\n\n"
        for i, r in enumerate(rules, 1):
            proto = r.get('protocol', 'any')
            action = r.get('action', '?').upper()
            comment = r.get('comment', 'rule')[:25]
            msg += f"{i}. [{action}] {proto}: {comment}\n"
        return msg
    except Exception as e:
        logger.error(f"Firewall error: {e}")
        return f"❌ Error: {str(e)[:80]}"

def cmd_block(chat_id, ip):
    """Block IP address"""
    if not pool:
        return "❌ Router offline"
    if not is_admin(chat_id):
        return "🔒 Admin only"
    try:
        import re
        if not re.match(r'^(\d{1,3}\.){3}\d{1,3}$', ip):
            return "❌ Invalid IP"
        api = pool.get_api()
        api.get_resource('/ip/firewall/address-list').call('add', {
            'list': 'blocked',
            'address': ip,
            'comment': 'blocked-by-bot'
        })
        logger.warning(f"IP blocked by {chat_id}: {ip}")
        return f"🚫 Blocked {ip}"
    except Exception as e:
        logger.error(f"Block error: {e}")
        return f"❌ Error: {str(e)[:80]}"

def cmd_unblock(chat_id, ip):
    """Unblock IP address"""
    if not pool:
        return "❌ Router offline"
    if not is_admin(chat_id):
        return "🔒 Admin only"
    try:
        api = pool.get_api()
        rules = api.get_resource('/ip/firewall/address-list').call('print')
        found = False
        for rule in rules:
            if rule.get('address') == ip and rule.get('list') == 'blocked':
                api.get_resource('/ip/firewall/address-list').call('remove', {'.id': rule['.id']})
                found = True
        if not found:
            return f"❌ {ip} not found"
        logger.warning(f"IP unblocked by {chat_id}: {ip}")
        return f"✅ Unblocked {ip}"
    except Exception as e:
        logger.error(f"Unblock error: {e}")
        return f"❌ Error: {str(e)[:80]}"

def cmd_help(chat_id):
    """Show help"""
    admin = is_admin(chat_id)
    msg = "📚 MikroTik Bot Commands:\n\n"
    msg += "📊 Speed - Bandwidth\n"
    msg += "📱 Devices - DHCP list\n"
    msg += "⚙️ Status - Router info\n"
    msg += "🔥 Top5 - Top consumers\n"
    msg += "📈 Traffic - Interface stats\n"
    msg += "📝 Logs - System logs\n"
    if admin:
        msg += "\n🔒 Admin:\n"
        msg += "🗂️ Backup - Save config\n"
        msg += "🚫 Firewall - View rules\n"
        msg += "🔒 Block/Unblock IP\n"
        msg += "\nFormat: block 192.168.1.100\n"
    return msg

# ============== Main Webhook ==============
@app.route(f'/{BOT_TOKEN}', methods=['POST'])
def webhook():
    """Main webhook handler"""
    try:
        update = request.get_json(force=True)
    except:
        return jsonify({'ok': False})
    
    # Safety checks
    if 'message' not in update:
        return jsonify({'ok': True})
    
    msg = update['message']
    if 'text' not in msg or 'chat' not in msg:
        return jsonify({'ok': True})
    
    chat_id = msg['chat']['id']
    text = msg['text'].strip()
    
    logger.info(f"Message from {chat_id}: {text}")
    
    try:
        admin = is_admin(chat_id)
        keyboard = ADMIN_KB if admin else KB
        reply = ""
        
        # Main commands
        if text in ['Speed', '/speed', '📊 Speed']:
            reply = cmd_speed(chat_id)
        elif text in ['Devices', '/devices', '📱 Devices']:
            reply = cmd_devices(chat_id)
        elif text in ['Status', '/status', '⚙️ Status']:
            reply = cmd_status(chat_id)
        elif text in ['Top5', '/top5', '🔥 Top5']:
            reply = cmd_top5(chat_id)
        elif text in ['Traffic', '/traffic', '📈 Traffic']:
            reply = cmd_traffic(chat_id)
        elif text in ['Logs', '/logs', '📝 Logs']:
            reply = cmd_logs(chat_id)
        elif text in ['Backup', '/backup', '🗂️ Backup']:
            reply = cmd_backup(chat_id)
        elif text in ['Firewall', '/firewall', '🚫 Firewall']:
            reply = cmd_firewall(chat_id)
        elif text in ['Help', '/help', '❓ Help']:
            reply = cmd_help(chat_id)
        
        # Inline commands
        elif text.lower().startswith('block '):
            ip = text.split('block ', 1)[1].strip()
            reply = cmd_block(chat_id, ip)
        elif text.lower().startswith('unblock '):
            ip = text.split('unblock ', 1)[1].strip()
            reply = cmd_unblock(chat_id, ip)
        
        else:
            reply = cmd_help(chat_id)
        
        send_message(chat_id, reply, keyboard)
        return jsonify({'ok': True})
        
    except Exception as e:
        logger.error(f"Error: {e}")
        send_message(chat_id, "❌ Error occurred", KB)
        return jsonify({'ok': True})

# ============== Health Check ==============
@app.route('/health', methods=['GET'])
def health():
    """Health check for Render"""
    return jsonify({'status': 'ok'})

# ============== Main ==============
if __name__ == '__main__':
    port = int(os.getenv('PORT', 10000))
    logger.info(f"🤖 Bot starting on port {port}")
    app.run(host='0.0.0.0', port=port, debug=False)
