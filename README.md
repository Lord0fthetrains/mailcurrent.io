# MailCurrent.io - Email API Service

A comprehensive Django-based email API service for sending transactional and marketing emails with advanced features like templates, analytics, and webhook support.

## 🚀 Features

### Core Email Functionality
- **RESTful API** for sending emails via HTTP requests
- **Template System** with Jinja2 templating engine
- **Custom Email Support** with full HTML/text content
- **SMTP Configuration** with custom SMTP server support
- **Email Attachments** support
- **Email Validation** and sanitization

### User Management
- **User Authentication** with email verification
- **API Key Management** with rate limiting
- **Subscription Plans** with usage tracking
- **Billing Integration** with Stripe
- **Password Reset** and account recovery

### Dashboard & Analytics
- **User Dashboard** with usage statistics
- **Email Logs** with detailed tracking
- **Analytics Service** for email performance
- **Real-time Status** monitoring
- **Usage Quotas** and notifications

### Advanced Features
- **Webhook Support** for email events
- **Email Security** with spam detection
- **DKIM/SPF/DMARC** verification
- **Unsubscribe Management**
- **Email Templates** with variable support
- **Status Page** for service monitoring

## 🛠️ Technology Stack

- **Backend**: Django 5.2.7, Django REST Framework
- **Database**: SQLite (development), PostgreSQL (production)
- **Email**: SMTP with custom server support
- **Templates**: Jinja2 templating engine
- **Frontend**: Bootstrap 5, HTML/CSS/JavaScript
- **Authentication**: Django Auth with token-based API
- **Payments**: Stripe integration
- **Security**: Bleach for HTML sanitization

## 📁 Project Structure

```
Email-Api/
├── accounts/                 # User management and authentication
├── api/                     # Core API functionality
├── frontend/                # Dashboard and web interface
├── email_api/              # Django project settings
├── templates/              # HTML templates
├── static/                 # Static files (CSS, JS, images)
├── requirements.txt        # Python dependencies
└── manage.py              # Django management script
```

## 🚀 Quick Start

### Prerequisites
- Python 3.12+
- pip
- Git

### Installation

1. **Clone the repository**
   ```bash
   git clone https://github.com/Lord0fthetrains/mailcurrent.io.git
   cd mailcurrent.io
   ```

2. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```

3. **Set up environment variables**
   ```bash
   cp .env.example .env
   # Edit .env with your configuration
   ```

4. **Run migrations**
   ```bash
   python manage.py migrate
   ```

5. **Create superuser**
   ```bash
   python manage.py createsuperuser
   ```

6. **Start development server**
   ```bash
   python manage.py runserver
   ```

## 🔧 Configuration

### Environment Variables
Create a `.env` file with the following variables:

```env
SECRET_KEY=your-secret-key
DEBUG=True
ALLOWED_HOSTS=localhost,127.0.0.1
DATABASE_URL=sqlite:///db.sqlite3

# Email Configuration
EMAIL_BACKEND=django.core.mail.backends.smtp.EmailBackend
EMAIL_HOST=smtp.gmail.com
EMAIL_PORT=587
EMAIL_USE_TLS=True
EMAIL_HOST_USER=your-email@gmail.com
EMAIL_HOST_PASSWORD=your-app-password

# Stripe Configuration
STRIPE_PUBLISHABLE_KEY=pk_test_...
STRIPE_SECRET_KEY=sk_test_...
STRIPE_WEBHOOK_SECRET=whsec_...

# Security
ENCRYPTION_KEY=your-encryption-key
```

## 📚 API Documentation

### Authentication
All API endpoints require authentication via API key in the header:
```
Authorization: Token your-api-key-here
```

### Send Email
```bash
POST /api/v1/emails/send/
Content-Type: application/json
Authorization: Token your-api-key

{
    "to": "recipient@example.com",
    "subject": "Hello World",
    "html_content": "<h1>Hello!</h1><p>This is a test email.</p>",
    "from_email": "sender@yourdomain.com",
    "from_name": "Your Name"
}
```

### Send Template Email
```bash
POST /api/v1/emails/send-template/
Content-Type: application/json
Authorization: Token your-api-key

{
    "template_name": "welcome",
    "to": "recipient@example.com",
    "variables": {
        "name": "John Doe",
        "company": "Example Corp"
    }
}
```

## 🎯 Usage Examples

### Python Client
```python
import requests

api_key = "your-api-key"
base_url = "https://api.mailcurrent.io"

# Send custom email
response = requests.post(
    f"{base_url}/api/v1/emails/send/",
    headers={"Authorization": f"Token {api_key}"},
    json={
        "to": "user@example.com",
        "subject": "Welcome!",
        "html_content": "<h1>Welcome to our service!</h1>"
    }
)
```

### cURL Example
```bash
curl -X POST https://api.mailcurrent.io/api/v1/emails/send/ \
  -H "Authorization: Token your-api-key" \
  -H "Content-Type: application/json" \
  -d '{
    "to": "user@example.com",
    "subject": "Test Email",
    "html_content": "<p>This is a test email.</p>"
  }'
```

## 🔒 Security Features

- **API Key Authentication** with rate limiting
- **HTML Sanitization** to prevent XSS attacks
- **Email Validation** and domain verification
- **SMTP Security** with TLS/SSL support
- **Password Encryption** for sensitive data
- **CSRF Protection** for web forms
- **SQL Injection Prevention** with Django ORM

## 📊 Monitoring & Analytics

- **Email Delivery Tracking** with status updates
- **Usage Analytics** with detailed metrics
- **Error Logging** with comprehensive error tracking
- **Performance Monitoring** with response time tracking
- **Status Page** for service uptime monitoring

## 🚀 Deployment

### Production Setup
1. **Configure production database** (PostgreSQL recommended)
2. **Set up reverse proxy** (Nginx)
3. **Configure SSL certificates**
4. **Set up monitoring** and logging
5. **Configure backup strategy**

### Docker Deployment
```bash
# Build and run with Docker
docker-compose up -d
```

## 🤝 Contributing

This is a private repository for MailCurrent.io development. For internal development:

1. Create a feature branch
2. Make your changes
3. Test thoroughly
4. Submit a pull request
5. Code review and merge

## 📄 License

Private - All rights reserved. This software is proprietary to MailCurrent.io.

## 🆘 Support

For support and questions:
- **Email**: support@mailcurrent.io
- **Documentation**: [API Docs](https://mailcurrent.io/docs)
- **Status Page**: [Status](https://status.mailcurrent.io)

## 🔄 Version History

- **v1.0.0** - Initial release with core email functionality
- **v1.1.0** - Added template system and analytics
- **v1.2.0** - Enhanced security and webhook support
- **v1.3.0** - Dashboard improvements and usage tracking

---

**MailCurrent.io** - Reliable Email API Service for Modern Applications