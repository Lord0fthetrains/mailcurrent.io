from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
from django.contrib.auth.hashers import make_password, check_password
from django.core.exceptions import ImproperlyConfigured
import secrets
import hashlib
import json
import base64
from cryptography.fernet import Fernet
from django.conf import settings

User = get_user_model()


class APIKey(models.Model):
    """API Key model for authentication"""
    key = models.CharField(max_length=64, unique=True, db_index=True)
    name = models.CharField(max_length=100, help_text="Service identifier")
    is_active = models.BooleanField(default=True)
    rate_limit = models.PositiveIntegerField(default=1000, help_text="Emails per hour")
    default_from_email = models.EmailField(blank=True, null=True, help_text="Default sender email")
    default_from_name = models.CharField(max_length=100, blank=True, null=True, help_text="Default sender name")
    allowed_domains = models.JSONField(default=list, help_text="List of allowed sender domains")
    
    # Custom SMTP Configuration
    custom_smtp_host = models.CharField(max_length=255, blank=True, null=True, help_text="Custom SMTP host")
    custom_smtp_port = models.PositiveIntegerField(default=587, help_text="Custom SMTP port")
    custom_smtp_username = models.CharField(max_length=255, blank=True, null=True, help_text="Custom SMTP username")
    custom_smtp_password = models.CharField(max_length=500, blank=True, null=True, help_text="Custom SMTP password (encrypted)")
    custom_smtp_use_tls = models.BooleanField(default=True, help_text="Use TLS for custom SMTP")
    custom_smtp_use_ssl = models.BooleanField(default=False, help_text="Use SSL for custom SMTP")
    
    created_at = models.DateTimeField(auto_now_add=True)
    last_used_at = models.DateTimeField(null=True, blank=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = "API Key"
        verbose_name_plural = "API Keys"

    def __str__(self):
        return f"{self.name} ({self.key[:8]}...)"

    def save(self, *args, **kwargs):
        if not self.key:
            # Generate a new API key
            self.key = self.generate_key()
        super().save(*args, **kwargs)

    @staticmethod
    def generate_key():
        """Generate a secure API key"""
        return secrets.token_urlsafe(32)

    def is_valid_domain(self, domain):
        """Check if a domain is allowed for this API key"""
        if not self.allowed_domains:
            return True  # No restrictions
        return domain in self.allowed_domains

    def update_last_used(self):
        """Update the last used timestamp"""
        self.last_used_at = timezone.now()
        self.save(update_fields=['last_used_at'])
    
    def should_use_custom_smtp(self, from_email):
        """Check if custom SMTP should be used for the given from_email"""
        if not self.custom_smtp_host:
            return False
        
        # If no custom SMTP is configured, use default
        if not all([self.custom_smtp_host, self.custom_smtp_username, self.custom_smtp_password]):
            return False
        
        # Extract domain from from_email
        if '@' not in from_email:
            return False
        
        domain = from_email.split('@')[1].lower()
        
        # Use custom SMTP if the domain is in allowed_domains or if no restrictions
        if not self.allowed_domains:
            return True
        
        return domain in [d.lower() for d in self.allowed_domains]
    
    def _get_encryption_key(self):
        """Get or create encryption key for SMTP passwords"""
        key = getattr(settings, 'SMTP_PASSWORD_ENCRYPTION_KEY', None)
        if not key:
            # Generate a key from SECRET_KEY if no specific key is set
            key = hashlib.sha256(settings.SECRET_KEY.encode()).digest()
        return key
    
    def _encrypt_password(self, password):
        """Encrypt the SMTP password"""
        if not password:
            return None
        try:
            key = self._get_encryption_key()
            f = Fernet(base64.urlsafe_b64encode(key))
            encrypted = f.encrypt(password.encode())
            return base64.urlsafe_b64encode(encrypted).decode()
        except Exception:
            # Fallback to simple base64 encoding if encryption fails
            return base64.b64encode(password.encode()).decode()
    
    def _decrypt_password(self, encrypted_password):
        """Decrypt the SMTP password"""
        if not encrypted_password:
            return None
        try:
            key = self._get_encryption_key()
            f = Fernet(base64.urlsafe_b64encode(key))
            encrypted = base64.urlsafe_b64decode(encrypted_password.encode())
            return f.decrypt(encrypted).decode()
        except Exception:
            # Fallback to simple base64 decoding if decryption fails
            try:
                return base64.b64decode(encrypted_password.encode()).decode()
            except Exception:
                return None
    
    def set_smtp_password(self, password):
        """Set and encrypt the SMTP password"""
        if password:
            self.custom_smtp_password = self._encrypt_password(password)
        else:
            self.custom_smtp_password = None
    
    def get_smtp_password(self):
        """Get the decrypted SMTP password for sending emails"""
        return self._decrypt_password(self.custom_smtp_password)
    
    def get_smtp_config(self, from_email):
        """Get SMTP configuration for the given from_email"""
        if self.should_use_custom_smtp(from_email):
            return {
                'host': self.custom_smtp_host,
                'port': self.custom_smtp_port,
                'username': self.custom_smtp_username,
                'password': self.get_smtp_password(),  # Decrypted password
                'use_tls': self.custom_smtp_use_tls,
                'use_ssl': self.custom_smtp_use_ssl,
                'is_custom': True
            }
        else:
            # Return default SMTP configuration
            from email_api.settings import EMAIL_HOST, EMAIL_PORT, EMAIL_USE_TLS, EMAIL_USE_SSL
            return {
                'host': EMAIL_HOST,
                'port': EMAIL_PORT,
                'username': '',  # Default SMTP doesn't use authentication
                'password': '',
                'use_tls': EMAIL_USE_TLS,
                'use_ssl': EMAIL_USE_SSL,
                'is_custom': False
            }
    
    @property
    def is_authenticated(self):
        """Required for Django REST Framework compatibility"""
        return True


class EmailTemplate(models.Model):
    """Email template model for predefined templates"""
    name = models.SlugField(unique=True, help_text="Template identifier")
    subject = models.CharField(max_length=200, help_text="Email subject (supports variables)")
    html_content = models.TextField(help_text="HTML template content (Jinja2 format)")
    text_content = models.TextField(help_text="Plain text template content")
    description = models.TextField(blank=True, help_text="Template description")
    required_variables = models.JSONField(default=list, help_text="List of required variables")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True)

    class Meta:
        verbose_name = "Email Template"
        verbose_name_plural = "Email Templates"

    def __str__(self):
        return self.name

    def get_required_variables(self):
        """Get list of required variables"""
        return self.required_variables or []

    def validate_variables(self, variables):
        """Validate that all required variables are provided"""
        required = set(self.get_required_variables())
        provided = set(variables.keys())
        missing = required - provided
        if missing:
            raise ValueError(f"Missing required variables: {', '.join(missing)}")


class EmailLog(models.Model):
    """Email log model for tracking sent emails"""
    STATUS_CHOICES = [
        ('queued', 'Queued'),
        ('sent', 'Sent'),
        ('failed', 'Failed'),
        ('bounced', 'Bounced'),
    ]

    to = models.EmailField()
    subject = models.CharField(max_length=200)
    template_used = models.ForeignKey(EmailTemplate, on_delete=models.SET_NULL, null=True, blank=True)
    api_key = models.ForeignKey(APIKey, on_delete=models.CASCADE)
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='queued')
    error_message = models.TextField(blank=True, null=True)
    message_id = models.CharField(max_length=200, blank=True, null=True)
    from_email = models.EmailField()
    from_name = models.CharField(max_length=100, blank=True)
    reply_to = models.EmailField(blank=True, null=True)
    sent_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    # Additional metadata
    variables_used = models.JSONField(default=dict, blank=True)
    attachment_count = models.PositiveIntegerField(default=0)
    
    # Webhook and tracking fields
    unsubscribe_token = models.CharField(max_length=64, blank=True, null=True)
    tracking_pixel_id = models.CharField(max_length=64, blank=True, null=True)
    html_length = models.PositiveIntegerField(default=0)
    text_length = models.PositiveIntegerField(default=0)

    class Meta:
        verbose_name = "Email Log"
        verbose_name_plural = "Email Logs"
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.to} - {self.subject} ({self.status})"

    def mark_sent(self, message_id=None):
        """Mark email as sent"""
        self.status = 'sent'
        self.sent_at = timezone.now()
        if message_id:
            self.message_id = message_id
        self.save()

    def mark_failed(self, error_message):
        """Mark email as failed"""
        self.status = 'failed'
        self.error_message = error_message
        self.save()

    def mark_bounced(self):
        """Mark email as bounced"""
        self.status = 'bounced'
        self.save()


class EmailAttachment(models.Model):
    """Email attachment model"""
    email_log = models.ForeignKey(EmailLog, on_delete=models.CASCADE, related_name='attachments')
    filename = models.CharField(max_length=255)
    content_type = models.CharField(max_length=100)
    size = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Email Attachment"
        verbose_name_plural = "Email Attachments"

    def __str__(self):
        return f"{self.email_log} - {self.filename}"