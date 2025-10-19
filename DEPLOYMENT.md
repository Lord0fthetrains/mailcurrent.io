# 🚀 MailCurrent.io Deployment Guide

## Domain Configuration

### DNS Settings
Point your domain to your server:

```
A Record:     mailcurrent.io        → YOUR_SERVER_IP
A Record:     www.mailcurrent.io    → YOUR_SERVER_IP  
A Record:     api.mailcurrent.io    → YOUR_SERVER_IP
```

### SSL Certificate
1. **Install Certbot**:
   ```bash
   sudo apt update
   sudo apt install certbot python3-certbot-nginx
   ```

2. **Get SSL Certificate**:
   ```bash
   sudo certbot --nginx -d mailcurrent.io -d www.mailcurrent.io -d api.mailcurrent.io
   ```

## Production Configuration

### 1. Update Environment Variables
Create `.env` file:
```bash
DEBUG=False
SECRET_KEY=your-production-secret-key
DEFAULT_FROM_EMAIL=noreply@mailcurrent.io
DEFAULT_FROM_NAME=MailCurrent.io
```

### 2. Database Configuration
```bash
# Run migrations
python3 manage.py migrate

# Create superuser
python3 manage.py createsuperuser

# Collect static files
python3 manage.py collectstatic --noinput
```

### 3. Web Server Configuration (Nginx)
```nginx
server {
    listen 80;
    server_name mailcurrent.io www.mailcurrent.io api.mailcurrent.io;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name mailcurrent.io www.mailcurrent.io;
    
    ssl_certificate /etc/letsencrypt/live/mailcurrent.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mailcurrent.io/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:3099;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
    
    location /static/ {
        alias /var/www/Email-Api/staticfiles/;
    }
}

server {
    listen 443 ssl;
    server_name api.mailcurrent.io;
    
    ssl_certificate /etc/letsencrypt/live/mailcurrent.io/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/mailcurrent.io/privkey.pem;
    
    location / {
        proxy_pass http://127.0.0.1:3099;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### 4. Process Management (Systemd)
Create `/etc/systemd/system/mailcurrent.service`:
```ini
[Unit]
Description=MailCurrent.io Email API
After=network.target

[Service]
Type=simple
User=www-data
Group=www-data
WorkingDirectory=/var/www/Email-Api
Environment=PATH=/var/www/Email-Api/venv/bin
ExecStart=/var/www/Email-Api/venv/bin/python manage.py runserver 0.0.0.0:3099
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable mailcurrent
sudo systemctl start mailcurrent
sudo systemctl status mailcurrent
```

## API Endpoints

### Main API
- **Base URL**: `https://api.mailcurrent.io/api/v1/`
- **Documentation**: `https://api.mailcurrent.io/api/v1/docs/`

### Key Endpoints
- **Send Email**: `POST https://api.mailcurrent.io/api/v1/send/`
- **Templates**: `GET https://api.mailcurrent.io/api/v1/templates/`
- **User Registration**: `POST https://api.mailcurrent.io/api/v1/accounts/register/`
- **User Login**: `POST https://api.mailcurrent.io/api/v1/accounts/login/`

## Frontend URLs

- **Main Site**: `https://mailcurrent.io`
- **Dashboard**: `https://mailcurrent.io/dashboard/`
- **API Docs**: `https://mailcurrent.io/api-docs/`
- **Pricing**: `https://mailcurrent.io/pricing/`

## Security Checklist

- [ ] SSL certificate installed and working
- [ ] DEBUG=False in production
- [ ] Strong SECRET_KEY
- [ ] Firewall configured (ports 80, 443, 22)
- [ ] Database backups configured
- [ ] Log monitoring set up
- [ ] Rate limiting configured
- [ ] CORS properly configured

## Monitoring

### Log Files
- **Application**: `/var/www/Email-Api/logs/email_api.log`
- **Nginx**: `/var/log/nginx/access.log`
- **System**: `journalctl -u mailcurrent`

### Health Check
```bash
curl https://api.mailcurrent.io/api/v1/health/
```

## Backup Strategy

### Database Backup
```bash
# Daily backup
0 2 * * * /usr/bin/sqlite3 /var/www/Email-Api/db.sqlite3 ".backup /backups/mailcurrent-$(date +\%Y\%m\%d).db"
```

### File Backup
```bash
# Weekly backup
0 3 * * 0 tar -czf /backups/mailcurrent-files-$(date +\%Y\%m\%d).tar.gz /var/www/Email-Api/
```

## Support

- **Documentation**: https://mailcurrent.io/docs/
- **API Status**: https://status.mailcurrent.io
- **Support Email**: support@mailcurrent.io

---

🎉 **Welcome to MailCurrent.io - Your Email API Service!**
