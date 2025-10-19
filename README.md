# MailCurrent.io

A powerful Django REST Framework-based email microservice that provides both template-based and custom HTML email sending capabilities with API key authentication and comprehensive logging.

## Features

### Stage 1 (Current)
- **Template-based emails** with Jinja2 variable substitution
- **Custom HTML/text emails** with full content control
- **API key authentication** with rate limiting
- **Sender customization** (email, name, reply-to)
- **Attachment support** (base64 encoded)
- **Email logging** and statistics
- **Admin panel** for management
- **Postfix SMTP integration**

### Stage 2 (Future)
- User accounts with registration/login
- Pricing tiers with usage limits and feature restrictions
- Stripe payment integration
- Web dashboard for users

### Stage 3 (Future)
- Webhooks and delivery status tracking
- Unsubscribe management
- Analytics and reporting
- Advanced security features
- Template versioning and testing

## Quick Start

### Prerequisites
- Python 3.12+
- Postfix mail server (or any SMTP server)
- Django 5.2+

### Installation

1. **Clone and setup the project:**
```bash
cd /var/www/place/email-api
pip3 install --user --break-system-packages -r requirements.txt
```

2. **Configure environment variables:**
```bash
cp .env.example .env
# Edit .env with your settings
```

3. **Run migrations:**
```bash
python3 manage.py migrate
```

4. **Create superuser and sample data:**
```bash
python3 manage.py createsuperuser
python3 manage.py setup_sample_data
```

5. **Start the development server:**
```bash
python3 manage.py runserver 0.0.0.0:3099
```

## Configuration

### Environment Variables (.env)

```env
SECRET_KEY=your-secret-key-here
DEBUG=False
ALLOWED_HOSTS=localhost,127.0.0.1,0.0.0.0
SMTP_HOST=localhost
SMTP_PORT=25
DEFAULT_FROM_EMAIL=noreply@yourdomain.com
DEFAULT_FROM_NAME=MailCurrent.io
RATE_LIMIT_PER_HOUR=1000
ALLOWED_SENDER_DOMAINS=yourdomain.com,app.yourdomain.com
```

### Postfix Configuration

The service is configured to use Postfix on localhost:25. Ensure Postfix is running:

```bash
sudo systemctl status postfix
sudo systemctl start postfix
```

## API Documentation

### Authentication

All API requests require an API key in the `X-API-Key` header:

```bash
curl -H "X-API-Key: your-api-key-here" \
     -H "Content-Type: application/json" \
     http://localhost:3099/api/v1/validate/
```

### Endpoints

#### Send Template Email
```bash
POST /api/v1/send-template/
```

**Request Body:**
```json
{
  "template": "welcome",
  "to": "user@example.com",
  "variables": {
    "user_name": "John Doe",
    "app_name": "MyApp"
  },
  "from_email": "notifications@yourdomain.com",
  "from_name": "My App",
  "reply_to": "support@yourdomain.com"
}
```

#### Send Custom Email
```bash
POST /api/v1/send/
```

**Request Body:**
```json
{
  "to": "user@example.com",
  "subject": "Custom Subject",
  "html": "<h1>Hello World</h1><p>This is a custom email.</p>",
  "text": "Hello World\n\nThis is a custom email.",
  "from_email": "custom@yourdomain.com",
  "from_name": "Custom Sender",
  "reply_to": "support@yourdomain.com",
  "attachments": [
    {
      "filename": "document.pdf",
      "content": "base64_encoded_content",
      "mimetype": "application/pdf"
    }
  ],
  "headers": {
    "X-Custom-Header": "value"
  }
}
```

#### List Templates
```bash
GET /api/v1/templates/
```

#### Get Email Statistics
```bash
GET /api/v1/stats/?days=30
```

#### Validate API Key
```bash
GET /api/v1/validate/
```

#### Health Check
```bash
GET /api/v1/health/
```

### Admin Endpoints (Admin Only)

#### List Email Logs
```bash
GET /api/v1/logs/?api_key_id=1&status=sent&page=1&page_size=50
```

#### Manage API Keys
```bash
GET /api/v1/api-keys/
POST /api/v1/api-keys/
GET /api/v1/api-keys/{id}/
PUT /api/v1/api-keys/{id}/
DELETE /api/v1/api-keys/{id}/
```

## Email Templates

### Built-in Templates

1. **welcome** - Welcome new users
   - Required variables: `user_name`, `app_name`
   - Optional: `welcome_message`, `features`, `verification_link`, `login_url`

2. **verification** - Email verification
   - Required variables: `user_name`, `app_name`, `verification_link`
   - Optional: `verification_code`, `expiry_time`

3. **notification** - General notifications
   - Required variables: `user_name`, `app_name`, `notification_title`, `notification_message`
   - Optional: `priority`, `details`, `action_url`, `action_text`

### Template Variables

Templates use Jinja2 syntax for variable substitution:

```html
<h1>Welcome to {{ app_name }}!</h1>
<p>Hello {{ user_name }},</p>
{% if features %}
<ul>
  {% for feature in features %}
  <li>{{ feature }}</li>
  {% endfor %}
</ul>
{% endif %}
```

## Usage Examples

### Send Welcome Email
```bash
curl -X POST http://localhost:3099/api/v1/send-template/ \
  -H "X-API-Key: tjZm0GwRGEHYX1WqMa_10VR3AycEhM5p86nywD6hHCA" \
  -H "Content-Type: application/json" \
  -d '{
    "template": "welcome",
    "to": "user@example.com",
    "variables": {
      "user_name": "John Doe",
      "app_name": "MyApp",
      "welcome_message": "Thanks for joining us!",
      "features": ["Feature 1", "Feature 2", "Feature 3"]
    }
  }'
```

### Send Custom HTML Email
```bash
curl -X POST http://localhost:3099/api/v1/send/ \
  -H "X-API-Key: tjZm0GwRGEHYX1WqMa_10VR3AycEhM5p86nywD6hHCA" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "user@example.com",
    "subject": "Custom Newsletter",
    "html": "<h1>Newsletter</h1><p>This is our monthly newsletter.</p>",
    "text": "Newsletter\n\nThis is our monthly newsletter.",
    "from_name": "Newsletter Team"
  }'
```

### Check API Key Status
```bash
curl -H "X-API-Key: tjZm0GwRGEHYX1WqMa_10VR3AycEhM5p86nywD6hHCA" \
     http://localhost:3099/api/v1/validate/
```

## Admin Panel

Access the Django admin panel at `http://localhost:3099/admin/` with:
- Username: `admin`
- Password: `admin123`

### Admin Features
- **API Keys**: Create, edit, and manage API keys
- **Email Templates**: Create and edit email templates
- **Email Logs**: View all sent emails with detailed information
- **Attachments**: View email attachments

## Database Models

### APIKey
- `key`: Unique API key (auto-generated)
- `name`: Service identifier
- `is_active`: Whether the key is active
- `rate_limit`: Emails per hour limit
- `default_from_email`: Default sender email
- `default_from_name`: Default sender name
- `allowed_domains`: List of allowed sender domains

### EmailTemplate
- `name`: Template identifier (slug)
- `subject`: Email subject with variable support
- `html_content`: HTML template content
- `text_content`: Plain text template content
- `required_variables`: List of required template variables

### EmailLog
- `to`: Recipient email
- `subject`: Email subject
- `status`: sent/failed/queued/bounced
- `template_used`: Reference to template (if used)
- `api_key`: Reference to API key used
- `from_email`, `from_name`: Sender information
- `sent_at`: Timestamp when sent
- `error_message`: Error details (if failed)

## Security Features

- **API Key Authentication**: Secure API key-based authentication
- **Rate Limiting**: Configurable rate limits per API key
- **Domain Whitelisting**: Restrict sender domains per API key
- **HTML Sanitization**: Bleach-based HTML sanitization
- **Input Validation**: Comprehensive input validation
- **CORS Configuration**: Configurable CORS settings

## Monitoring and Logging

- **Email Logs**: All emails are logged with full details
- **Error Tracking**: Failed emails are logged with error messages
- **Statistics**: Email statistics and usage tracking
- **Admin Interface**: Comprehensive admin panel for monitoring

## Deployment

### Production Setup

1. **Environment Configuration:**
```bash
# Set production environment variables
export DEBUG=False
export SECRET_KEY=your-production-secret-key
export ALLOWED_HOSTS=yourdomain.com,api.yourdomain.com
```

2. **Database Migration:**
```bash
python3 manage.py migrate
python3 manage.py collectstatic
```

3. **Run with Gunicorn:**
```bash
pip install gunicorn
gunicorn email_api.wsgi:application --bind 0.0.0.0:8000
```

4. **Nginx Configuration:**
```nginx
server {
    listen 80;
    server_name api.yourdomain.com;
    
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
    }
}
```

### Systemd Service

Create `/etc/systemd/system/email-api.service`:

```ini
[Unit]
Description=MailCurrent.io
After=network.target

[Service]
User=www-data
Group=www-data
WorkingDirectory=/var/www/place/email-api
ExecStart=/usr/bin/python3 manage.py runserver 0.0.0.0:3099
Restart=always

[Install]
WantedBy=multi-user.target
```

Enable and start:
```bash
sudo systemctl enable email-api
sudo systemctl start email-api
```

## Troubleshooting

### Common Issues

1. **Email not sending:**
   - Check Postfix status: `sudo systemctl status postfix`
   - Verify SMTP configuration in settings
   - Check email logs in admin panel

2. **API key authentication failing:**
   - Verify API key is active
   - Check rate limits
   - Ensure correct header format: `X-API-Key`

3. **Template rendering errors:**
   - Check required variables are provided
   - Verify Jinja2 syntax in templates
   - Check template is active

### Logs

- Application logs: `/var/www/place/email-api/logs/email_api.log`
- Django logs: Check admin panel for email logs
- System logs: `journalctl -u email-api`

## API Response Format

### Success Response
```json
{
  "success": true,
  "message": "Email sent successfully",
  "timestamp": "2024-01-15T10:30:00Z"
}
```

### Error Response
```json
{
  "success": false,
  "error": "Template 'welcome' not found",
  "errors": {
    "template": ["Template 'welcome' not found or inactive"]
  }
}
```

## License

This project is licensed under the MIT License.

## Support

For support and questions:
- Check the admin panel for email logs and statistics
- Review the API documentation above
- Check system logs for detailed error information
