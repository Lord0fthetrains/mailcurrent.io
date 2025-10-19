from django.db import models
from django.contrib.auth import get_user_model
from django.utils import timezone
import uuid

User = get_user_model()


class BlacklistEntry(models.Model):
    """Email addresses and domains that are blacklisted"""
    TYPE_CHOICES = [
        ('email', 'Email Address'),
        ('domain', 'Domain'),
        ('ip', 'IP Address'),
        ('pattern', 'Pattern'),
    ]
    
    REASON_CHOICES = [
        ('bounce', 'Bounce'),
        ('complaint', 'Complaint'),
        ('spam', 'Spam'),
        ('manual', 'Manual'),
        ('abuse', 'Abuse'),
        ('unsubscribe', 'Unsubscribe'),
    ]
    
    entry_type = models.CharField(max_length=20, choices=TYPE_CHOICES)
    value = models.CharField(max_length=255, unique=True, help_text="Email, domain, IP, or pattern to blacklist")
    reason = models.CharField(max_length=20, choices=REASON_CHOICES, default='manual')
    description = models.TextField(blank=True, help_text="Additional details about why this was blacklisted")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, null=True, blank=True, related_name='blacklist_entries')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    expires_at = models.DateTimeField(null=True, blank=True, help_text="Optional expiration date")
    
    def __str__(self):
        return f"{self.entry_type}: {self.value} ({self.reason})"
    
    class Meta:
        ordering = ['-created_at']
        indexes = [
            models.Index(fields=['entry_type', 'is_active']),
            models.Index(fields=['value']),
            models.Index(fields=['created_at']),
        ]


class SpamScore(models.Model):
    """Spam score configuration and thresholds"""
    name = models.CharField(max_length=100, unique=True)
    description = models.TextField()
    threshold = models.FloatField(help_text="Spam score threshold (0.0 to 1.0)")
    action = models.CharField(max_length=20, choices=[
        ('allow', 'Allow'),
        ('quarantine', 'Quarantine'),
        ('reject', 'Reject'),
    ], default='quarantine')
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} (threshold: {self.threshold})"


class SpamRule(models.Model):
    """Individual spam detection rules"""
    RULE_TYPES = [
        ('content', 'Content Analysis'),
        ('header', 'Header Analysis'),
        ('sender', 'Sender Analysis'),
        ('recipient', 'Recipient Analysis'),
        ('technical', 'Technical Analysis'),
    ]
    
    name = models.CharField(max_length=100, unique=True)
    rule_type = models.CharField(max_length=20, choices=RULE_TYPES)
    description = models.TextField()
    pattern = models.TextField(help_text="Regex pattern or rule logic")
    score = models.FloatField(help_text="Score to add if rule matches (can be negative)")
    is_active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.name} ({self.rule_type}) - {self.score}"


class EmailSecurityLog(models.Model):
    """Log of security-related email events"""
    email_log = models.ForeignKey('api.EmailLog', on_delete=models.CASCADE, related_name='security_logs')
    event_type = models.CharField(max_length=50, choices=[
        ('blacklist_check', 'Blacklist Check'),
        ('spam_score', 'Spam Score'),
        ('dkim_verification', 'DKIM Verification'),
        ('spf_verification', 'SPF Verification'),
        ('dmarc_verification', 'DMARC Verification'),
        ('quarantine', 'Quarantined'),
        ('rejected', 'Rejected'),
    ])
    details = models.JSONField(default=dict, help_text="Additional event details")
    score = models.FloatField(null=True, blank=True, help_text="Spam score if applicable")
    action_taken = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"{self.email_log.subject} - {self.event_type}"
    
    class Meta:
        ordering = ['-created_at']


class DKIMRecord(models.Model):
    """DKIM configuration for domains"""
    domain = models.CharField(max_length=255, unique=True)
    selector = models.CharField(max_length=100, default='default')
    private_key = models.TextField(help_text="DKIM private key")
    public_key = models.TextField(help_text="DKIM public key")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dkim_records')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.domain} ({self.selector})"
    
    class Meta:
        unique_together = ['domain', 'selector']


class SPFRecord(models.Model):
    """SPF configuration for domains"""
    domain = models.CharField(max_length=255, unique=True)
    spf_record = models.TextField(help_text="SPF record content")
    includes = models.JSONField(default=list, help_text="List of included domains")
    ip_addresses = models.JSONField(default=list, help_text="List of allowed IP addresses")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='spf_records')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.domain} - {self.spf_record[:50]}..."


class DMARCRecord(models.Model):
    """DMARC configuration for domains"""
    domain = models.CharField(max_length=255, unique=True)
    policy = models.CharField(max_length=20, choices=[
        ('none', 'None'),
        ('quarantine', 'Quarantine'),
        ('reject', 'Reject'),
    ], default='quarantine')
    percentage = models.IntegerField(default=100, help_text="Percentage of emails to apply policy to")
    rua = models.EmailField(blank=True, help_text="Aggregate reports email")
    ruf = models.EmailField(blank=True, help_text="Forensic reports email")
    is_active = models.BooleanField(default=True)
    created_by = models.ForeignKey(User, on_delete=models.CASCADE, related_name='dmarc_records')
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"{self.domain} - {self.policy}"
