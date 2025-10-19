from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class WebhookEndpoint(models.Model):
    """Webhook endpoints for delivery notifications"""
    WEBHOOK_EVENTS = [
        ('email.sent', 'Email Sent'),
        ('email.delivered', 'Email Delivered'),
        ('email.bounced', 'Email Bounced'),
        ('email.complained', 'Email Complained'),
        ('email.opened', 'Email Opened'),
        ('email.clicked', 'Email Clicked'),
        ('email.unsubscribed', 'Email Unsubscribed'),
    ]
    
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='webhook_endpoints')
    name = models.CharField(max_length=255)
    url = models.URLField()
    events = models.JSONField(default=list, help_text="List of events to send to this endpoint")
    secret = models.CharField(max_length=64, default='')
    is_active = models.BooleanField(default=True)
    retry_count = models.PositiveIntegerField(default=3)
    timeout_seconds = models.PositiveIntegerField(default=30)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def save(self, *args, **kwargs):
        if not self.secret:
            self.secret = uuid.uuid4().hex
        super().save(*args, **kwargs)
    
    def __str__(self):
        return f"{self.name} - {self.url}"
    
    class Meta:
        unique_together = ['user', 'url']


class WebhookDelivery(models.Model):
    """Track webhook delivery attempts"""
    STATUS_CHOICES = [
        ('pending', 'Pending'),
        ('delivered', 'Delivered'),
        ('failed', 'Failed'),
        ('retrying', 'Retrying'),
    ]
    
    webhook_endpoint = models.ForeignKey(WebhookEndpoint, on_delete=models.CASCADE, related_name='deliveries')
    event_type = models.CharField(max_length=50)
    payload = models.JSONField()
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default='pending')
    response_status = models.PositiveIntegerField(null=True, blank=True)
    response_body = models.TextField(blank=True)
    attempt_count = models.PositiveIntegerField(default=0)
    last_attempt_at = models.DateTimeField(null=True, blank=True)
    next_retry_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.webhook_endpoint.name} - {self.event_type} - {self.status}"
    
    class Meta:
        ordering = ['-created_at']


class EmailEvent(models.Model):
    """Track email events (opens, clicks, bounces, etc.)"""
    EVENT_TYPES = [
        ('sent', 'Sent'),
        ('delivered', 'Delivered'),
        ('bounced', 'Bounced'),
        ('complained', 'Complained'),
        ('opened', 'Opened'),
        ('clicked', 'Clicked'),
        ('unsubscribed', 'Unsubscribed'),
    ]
    
    email_log = models.ForeignKey('api.EmailLog', on_delete=models.CASCADE, related_name='events')
    event_type = models.CharField(max_length=20, choices=EVENT_TYPES)
    recipient_email = models.EmailField()
    event_data = models.JSONField(default=dict, help_text="Additional event-specific data")
    ip_address = models.GenericIPAddressField(null=True, blank=True)
    user_agent = models.TextField(blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.email_log.subject} - {self.event_type} - {self.recipient_email}"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['email_log', 'event_type']),
            models.Index(fields=['recipient_email', 'event_type']),
            models.Index(fields=['created_at']),
        ]


class UnsubscribeList(models.Model):
    """Track unsubscribed email addresses"""
    email = models.EmailField(unique=True)
    reason = models.CharField(max_length=100, blank=True, help_text="Reason for unsubscribing")
    source = models.CharField(max_length=50, default='manual', help_text="How they unsubscribed")
    user = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='unsubscribes')
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.email} - {self.reason}"
    
    class Meta:
        ordering = ['-created_at']


# EmailTemplate model is defined in models.py to avoid conflicts
