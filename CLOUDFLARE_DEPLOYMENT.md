# 🌐 Cloudflare Tunnel Deployment for MailCurrent.io

## Prerequisites

1. **Cloudflare Account** - Sign up at cloudflare.com
2. **Domain Added** - Add mailcurrent.io to Cloudflare
3. **Server Access** - SSH access to your server

## Step 1: Install Cloudflare Tunnel

### On Your Server
```bash
# Download and install cloudflared
wget https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared-linux-amd64.deb

# Verify installation
cloudflared --version
```

## Step 2: Authenticate with Cloudflare

```bash
# Login to Cloudflare (opens browser)
cloudflared tunnel login

# This will:
# 1. Open your browser
# 2. Ask you to select your domain (mailcurrent.io)
# 3. Authorize the tunnel
# 4. Save credentials to ~/.cloudflared/cert.pem
```

## Step 3: Create Tunnel

```bash
# Create a new tunnel
cloudflared tunnel create mailcurrent-api

# This creates:
# - Tunnel ID (save this!)
# - Credentials file: ~/.cloudflared/[tunnel-id].json
```

## Step 4: Configure Tunnel

Create tunnel configuration file:

```bash
# Create config directory
mkdir -p ~/.cloudflared

# Create config file
nano ~/.cloudflared/config.yml
```

**Config file content:**
```yaml
tunnel: [YOUR-TUNNEL-ID]
credentials-file: /home/[username]/.cloudflared/[tunnel-id].json

ingress:
  # Main website
  - hostname: mailcurrent.io
    service: http://localhost:3099
    originRequest:
      httpHostHeader: mailcurrent.io
  
  # WWW redirect
  - hostname: www.mailcurrent.io
    service: http://localhost:3099
    originRequest:
      httpHostHeader: www.mailcurrent.io
  
  # API subdomain
  - hostname: api.mailcurrent.io
    service: http://localhost:3099
    originRequest:
      httpHostHeader: api.mailcurrent.io
  
  # Catch-all rule (required)
  - service: http_status:404
```

## Step 5: Configure DNS

### In Cloudflare Dashboard:
1. Go to **DNS** → **Records**
2. Add these records:

```
Type: CNAME
Name: @
Target: [tunnel-id].cfargotunnel.com
Proxy: ✅ (Orange cloud)

Type: CNAME  
Name: www
Target: [tunnel-id].cfargotunnel.com
Proxy: ✅ (Orange cloud)

Type: CNAME
Name: api
Target: [tunnel-id].cfargotunnel.com
Proxy: ✅ (Orange cloud)
```

## Step 6: Test Tunnel

```bash
# Test the tunnel
cloudflared tunnel run mailcurrent-api

# You should see:
# - Tunnel starting
# - DNS records being created
# - "Tunnel is running" message
```

## Step 7: Create Systemd Service

Create service file:
```bash
sudo nano /etc/systemd/system/cloudflared.service
```

**Service content:**
```ini
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=root
ExecStart=/usr/local/bin/cloudflared tunnel --config /home/[username]/.cloudflared/config.yml run
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
# Enable service
sudo systemctl enable cloudflared

# Start service
sudo systemctl start cloudflared

# Check status
sudo systemctl status cloudflared

# View logs
sudo journalctl -u cloudflared -f
```

## Step 8: Update Django Settings

Your settings are already updated! But let's add Cloudflare-specific settings:

```python
# In email_api/settings.py

# Cloudflare Tunnel Settings
SECURE_PROXY_SSL_HEADER = ('HTTP_CF_VISITOR', '{"scheme":"https"}')
USE_TZ = True

# Trust Cloudflare IPs
CLOUDFLARE_IPS = [
    '173.245.48.0/20',
    '103.21.244.0/22',
    '103.22.200.0/22',
    '103.31.4.0/22',
    '141.101.64.0/18',
    '108.162.192.0/18',
    '190.93.240.0/20',
    '188.114.96.0/20',
    '197.234.240.0/22',
    '198.41.128.0/17',
    '162.158.0.0/15',
    '104.16.0.0/13',
    '104.24.0.0/14',
    '172.64.0.0/13',
    '131.0.72.0/22'
]

# Add to ALLOWED_HOSTS
ALLOWED_HOSTS = [
    'localhost', '127.0.0.1', 'testserver', '0.0.0.0',
    'mailcurrent.io', 'www.mailcurrent.io', 'api.mailcurrent.io',
    '.cfargotunnel.com'  # Cloudflare tunnel domain
]
```

## Step 9: Start Your Django App

```bash
# Make sure your Django app is running
cd /var/www/Email-Api
python3 manage.py runserver 0.0.0.0:3099

# Or run in background
nohup python3 manage.py runserver 0.0.0.0:3099 > /dev/null 2>&1 &
```

## Step 10: Test Everything

### Test URLs:
- **Main Site**: https://mailcurrent.io
- **API Health**: https://api.mailcurrent.io/api/v1/health/
- **API Docs**: https://api.mailcurrent.io/api/v1/docs/

### Test API:
```bash
curl https://api.mailcurrent.io/api/v1/health/
```

## 🔧 **Advanced Configuration**

### Custom Headers
Add to your tunnel config:
```yaml
originRequest:
  httpHostHeader: api.mailcurrent.io
  originServerName: api.mailcurrent.io
  noTLSVerify: false
```

### Rate Limiting
In Cloudflare Dashboard:
1. Go to **Security** → **WAF**
2. Create rate limiting rules
3. Set limits for API endpoints

### Caching
1. Go to **Caching** → **Configuration**
2. Set cache rules for static files
3. Bypass cache for API endpoints

## 🚨 **Troubleshooting**

### Common Issues:

1. **Tunnel not starting**:
   ```bash
   # Check logs
   sudo journalctl -u cloudflared -f
   
   # Check config
   cloudflared tunnel validate ~/.cloudflared/config.yml
   ```

2. **DNS not resolving**:
   - Wait 5-10 minutes for DNS propagation
   - Check Cloudflare DNS records
   - Ensure proxy is enabled (orange cloud)

3. **502 Bad Gateway**:
   - Check if Django app is running on port 3099
   - Verify tunnel configuration
   - Check firewall settings

4. **SSL Issues**:
   - Cloudflare handles SSL automatically
   - Check if tunnel is running
   - Verify DNS records

## 🎉 **Benefits of Cloudflare Tunnel**

✅ **No port exposure** - Server stays private  
✅ **Automatic SSL** - No certificate management  
✅ **DDoS protection** - Built-in security  
✅ **Global CDN** - Faster worldwide access  
✅ **Free** - No additional costs  
✅ **Easy maintenance** - Simple updates  

## 📊 **Monitoring**

### Cloudflare Analytics:
- **Traffic**: Dashboard → Analytics
- **Security**: Security → Events
- **Performance**: Speed → Insights

### Server Monitoring:
```bash
# Check tunnel status
sudo systemctl status cloudflared

# Check Django app
ps aux | grep manage.py

# Check logs
tail -f /var/www/Email-Api/logs/email_api.log
```

---

🎉 **Your MailCurrent.io API is now live with Cloudflare Tunnel!**
