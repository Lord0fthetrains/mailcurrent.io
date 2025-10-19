from django.db import models
from django.utils import timezone


class SystemComponent(models.Model):
    """System components to monitor"""
    name = models.CharField(max_length=100)
    description = models.TextField(blank=True)
    is_active = models.BooleanField(default=True)
    order = models.PositiveIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['order', 'name']
    
    def __str__(self):
        return self.name


class ComponentStatus(models.Model):
    """Status snapshots for components"""
    component = models.ForeignKey(SystemComponent, on_delete=models.CASCADE, related_name='statuses')
    status = models.CharField(max_length=20, choices=[
        ('operational', 'Operational'),
        ('degraded', 'Degraded Performance'),
        ('partial', 'Partial Outage'),
        ('major', 'Major Outage'),
        ('maintenance', 'Maintenance'),
    ])
    response_time = models.PositiveIntegerField(help_text="Response time in milliseconds", null=True, blank=True)
    uptime_percentage = models.DecimalField(max_digits=5, decimal_places=2, default=100.00)
    message = models.TextField(blank=True, help_text="Status message for users")
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-created_at']
    
    def __str__(self):
        return f"{self.component.name} - {self.status}"


class SystemIncident(models.Model):
    """System incidents and maintenance windows"""
    title = models.CharField(max_length=200)
    description = models.TextField()
    status = models.CharField(max_length=20, choices=[
        ('investigating', 'Investigating'),
        ('identified', 'Identified'),
        ('monitoring', 'Monitoring'),
        ('resolved', 'Resolved'),
        ('scheduled', 'Scheduled Maintenance'),
    ])
    impact = models.CharField(max_length=20, choices=[
        ('none', 'No Impact'),
        ('minor', 'Minor Impact'),
        ('major', 'Major Impact'),
        ('critical', 'Critical Impact'),
    ])
    affected_components = models.ManyToManyField(SystemComponent, blank=True)
    started_at = models.DateTimeField()
    resolved_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    class Meta:
        ordering = ['-started_at']
    
    def __str__(self):
        return self.title
    
    @property
    def is_resolved(self):
        return self.status == 'resolved' and self.resolved_at is not None


class SystemMetrics(models.Model):
    """System performance metrics"""
    date = models.DateField()
    uptime_percentage = models.DecimalField(max_digits=5, decimal_places=2)
    avg_response_time = models.PositiveIntegerField(help_text="Average response time in milliseconds")
    emails_sent = models.PositiveIntegerField(default=0)
    api_requests = models.PositiveIntegerField(default=0)
    error_rate = models.DecimalField(max_digits=5, decimal_places=2, default=0.00)
    created_at = models.DateTimeField(auto_now_add=True)
    
    class Meta:
        ordering = ['-date']
        unique_together = ['date']
    
    def __str__(self):
        return f"Metrics for {self.date}"


class StatusPageSettings(models.Model):
    """Status page configuration"""
    site_name = models.CharField(max_length=100, default="MailCurrent.io")
    site_description = models.TextField(default="MailCurrent.io Service Status")
    show_uptime = models.BooleanField(default=True)
    show_metrics = models.BooleanField(default=True)
    show_incidents = models.BooleanField(default=True)
    auto_refresh_seconds = models.PositiveIntegerField(default=60)
    contact_email = models.EmailField(default="status@mailcurrent.io")
    twitter_handle = models.CharField(max_length=50, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)
    
    def __str__(self):
        return f"Status Page Settings"
    
    @classmethod
    def get_settings(cls):
        settings, created = cls.objects.get_or_create(pk=1)
        return settings
