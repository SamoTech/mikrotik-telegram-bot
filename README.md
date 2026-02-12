# MikroTik Telegram Bot

A powerful Telegram bot for managing and monitoring MikroTik RouterOS devices via webhook-based Flask application. Optimized for cloud deployment on Render.com.

## Features

### Core Monitoring
- **📊 Bandwidth Monitor** - Real-time bandwidth usage with device names
- **📱 Device Manager** - View all connected DHCP devices with IP addresses
- **⚙️ Router Status** - System health metrics (CPU, memory, uptime, version)
- **🔥 Top 5 Consumers** - Identify top bandwidth-consuming devices
- **📈 Traffic Analytics** - Interface-level RX/TX statistics
- **📝 System Logs** - View recent router logs

### Administrator Tools
- **🗂️ Backup Management** - Create timestamped router backups
- **🚫 Firewall Rules** - View active firewall filter rules
- **🔒 IP Management** - Block/unblock IP addresses in address lists
- **💻 Terminal Commands** - Execute RouterOS API commands directly
- **📋 Daily Checklist** - Comprehensive system health monitoring report

## Prerequisites

- Python 3.8+
- MikroTik RouterOS device with API enabled
- Telegram Bot Token (from [@BotFather](https://t.me/BotFather))
- Cloud hosting with internet access (Render.com, Heroku, etc.)

## Installation

### 1. Clone Repository
```bash
git clone https://github.com/SamoTech/mikrotik-telegram-bot.git
cd mikrotik-telegram-bot
```

### 2. Install Dependencies
```bash
pip install -r requirements.txt
```

### 3. Configure MikroTik RouterOS

Enable API on your MikroTik device:
```
/ip service enable api
/ip service set api address=0.0.0.0/0 port=8728
```

Create a user account for the bot:
```
/user add name=telegram password=StrongPassword group=full
```

### 4. Set Environment Variables

Create a `.env` file or set environment variables:

```bash
# Telegram Bot Configuration
BOT_TOKEN=your_telegram_bot_token_here

# MikroTik Router Configuration
ROUTER_HOST=192.168.0.1          # Router IP address
ROUTER_PORT=8728                 # API port (default: 8728)
ROUTER_USER=telegram             # API user
ROUTER_PASS=StrongPassword       # API password

# Admin Configuration
ADMIN_IDS=123456789,987654321    # Comma-separated Telegram user IDs

# Server Configuration (for Render/Heroku)
PORT=10000                       # Server port
```

### 5. Configure Telegram Webhook

Set the webhook URL with your Telegram bot token:

```bash
curl -X POST https://api.telegram.org/bot{BOT_TOKEN}/setWebhook \
  -H "Content-Type: application/json" \
  -d '{"url": "https://your-app-url.com/{BOT_TOKEN}"}'
```

Replace `{BOT_TOKEN}` with your actual token and `your-app-url.com` with your deployment URL.

## Deployment

### Render.com Deployment

1. Push code to GitHub
2. Create new Web Service on [Render](https://render.com)
3. Connect your GitHub repository
4. Set environment variables in Render dashboard
5. Deploy

### Manual Deployment

```bash
# Install dependencies
pip install -r requirements.txt

# Run locally (for testing)
python app.py

# Access at: http://localhost:10000
```

## Usage

### User Commands

Start the bot and select commands from the keyboard menu:

| Command | Function |
|---------|----------|
| 📊 Speed | Show current bandwidth usage |
| 📱 Devices | List connected devices |
| ⚙️ Status | Show router status |
| 🔥 Top5 | Top 5 bandwidth consumers |
| 📈 Traffic | Interface traffic stats |
| 📝 Logs | Recent system logs |
| ❓ Help | Show help message |

### Admin Commands

Admins (defined by `ADMIN_IDS`) have access to:

| Command | Function |
|---------|----------|
| 🗂️ Backup | Create configuration backup |
| 🚫 Firewall | View firewall rules |
| 🔒 Block IP | Block an IP address |
| ✅ Unblock IP | Unblock an IP address |
| 💻 Terminal | Execute RouterOS commands |
| 📋 Checklist | Daily system health report |

### Admin Command Syntax

**Block IP:**
```
block 192.168.1.100
```

**Unblock IP:**
```
unblock 192.168.1.100
```

**Terminal Commands:**
```
terminal /system/resource
terminal /ip/address print
terminal /interface print
terminal /ip/firewall/filter print
```

## Configuration Details

### Device Names

The bot automatically displays device-friendly names instead of IP addresses by checking:
1. DHCP lease comment field
2. Hostname from DHCP lease
3. MAC address as fallback

Set device names in MikroTik:
```
/ip/dhcp-server/lease
set [find address=192.168.1.100] comment="My Phone"
```

### Admin IDs

To find your Telegram user ID, send `/start` to [@userinfobot](https://t.me/userinfobot)

Add multiple admins:
```
ADMIN_IDS=123456789,987654321,555555555
```

### Bandwidth Queue Management

The bot reads from `/queue/simple` in MikroTik. Ensure queues are properly configured:

```
/queue simple
add name=Device target=192.168.1.100
```

## API Endpoints

| Endpoint | Method | Purpose |
|----------|--------|---------|
| `/{BOT_TOKEN}` | POST | Telegram webhook (main handler) |
| `/health` | GET | Health check (for uptime monitoring) |

## Supported RouterOS Commands

The terminal command supports any RouterOS API path with `print` action:

- System: `/system/resource`, `/system/backup`, `/system/identity`
- Network: `/ip/address`, `/ip/route`, `/ip/firewall/filter`
- DHCP: `/ip/dhcp-server`, `/ip/dhcp-server/lease`
- Interfaces: `/interface`, `/interface/ether`
- Queues: `/queue/simple`, `/queue/tree`
- Security: `/ip/firewall/address-list`

**Blocked dangerous commands:** `reboot`, `reset`, `shutdown`, `remove`, `delete`

## Security Considerations

⚠️ **Important Security Notes:**

1. **Use Strong Credentials** - Use complex passwords for RouterOS API user
2. **Admin IDs** - Only grant bot admin access to trusted Telegram accounts
3. **Network Security** - Restrict API access to your server IP if possible:
   ```
   /ip service set api address=your-server-ip
   ```
4. **SSL/TLS** - For production, use SSL when connecting to RouterOS
5. **Dangerous Commands** - The bot blocks dangerous commands by design
6. **Logs** - All admin actions are logged with user IDs
7. **IP Blocking** - Blocked IPs are added to the "blocked" address list

## Troubleshooting

### Bot doesn't respond

1. Check bot token is correct:
   ```bash
   curl https://api.telegram.org/bot{BOT_TOKEN}/getMe
   ```

2. Verify webhook is set:
   ```bash
   curl https://api.telegram.org/bot{BOT_TOKEN}/getWebhookInfo
   ```

3. Check server logs for errors

### Router offline error

1. Verify ROUTER_HOST is correct
2. Check API is enabled: `/ip service enable api`
3. Test connection: `telnet ROUTER_HOST 8728`
4. Verify credentials

### No device names showing

1. Check DHCP lease comments are set
2. Verify hostnames are configured
3. Bot falls back to MAC addresses if names unavailable

### Terminal command not working

1. Ensure path starts with `/`
2. Only `print` action is supported
3. Check RouterOS user has permissions
4. View logs for detailed error messages

## Example Outputs

### Speed Command
```
📊 Current Bandwidth:

1. My Phone: 5.2M/2.1M
2. Laptop: 1.3M/850K
3. Smart TV: 2.8M/150K
...
```

### Daily Checklist
```
📋 Daily System Checklist

━━━━━ 🔧 SYSTEM HEALTH ━━━━━
✅ CPU Load: 15%
✅ Memory: 42.3% used
✅ Uptime: 30d 5h 12m
✅ Version: 7.9.2

━━━━━ 📱 CONNECTED DEVICES ━━━━━
✅ Connected: 8 devices
   • My Phone: 192.168.1.105
   • Laptop: 192.168.1.110
   ...

[More sections...]
```

## Environment Variables Reference

```bash
# Required
BOT_TOKEN              # Telegram bot token
ROUTER_HOST            # MikroTik IP address
ROUTER_USER            # API username
ROUTER_PASS            # API password

# Optional (with defaults)
ROUTER_PORT            # Default: 8728
ADMIN_IDS              # Default: empty (all users as admins)
PORT                   # Default: 10000
```

## Logging

The bot logs:
- Bot operations (info level)
- Admin actions (warning level) - backups, IP blocks, terminal commands
- Errors (error level) - API failures, connection issues

Check logs on Render or your hosting platform for debugging.

## Requirements

```
Flask==2.3.0
requests==2.31.0
routeros-api==0.17.0
python-dotenv==1.0.0
```

## License

MIT License - Feel free to modify and distribute

## Support

For issues, feature requests, or questions:
1. Check the [Troubleshooting](#troubleshooting) section
2. Review RouterOS API documentation
3. Open an issue on GitHub

## Changelog

### v1.0.0
- Initial release
- Core monitoring features
- Admin command set
- Terminal access
- Daily checklist
- Render.com optimization

## Disclaimer

This bot has access to your RouterOS device configuration and network management. Use with caution and restrict admin access to trusted users only. The author is not responsible for any network changes or data loss caused by improper use.

---

**Happy Monitoring!** 🚀
