from django.contrib import admin
from django.utils.html import format_html
from django.urls import reverse
from django.utils import timezone
from .models import APIKey, EmailTemplate, EmailLog, EmailAttachment
from .status_models import SystemComponent, ComponentStatus, SystemIncident, SystemMetrics, StatusPageSettings


@admin.register(APIKey)
class APIKeyAdmin(admin.ModelAdmin):
    list_display = ['name', 'key_display', 'is_active', 'rate_limit', 'created_at', 'last_used_at']
    list_filter = ['is_active', 'created_at', 'last_used_at']
    search_fields = ['name', 'key']
    readonly_fields = ['key', 'created_at', 'last_used_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'key', 'is_active')
        }),
        ('Rate Limiting', {
            'fields': ('rate_limit',)
        }),
        ('Default Sender Settings', {
            'fields': ('default_from_email', 'default_from_name', 'allowed_domains'),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'last_used_at'),
            'classes': ('collapse',)
        }),
    )
    
    def key_display(self, obj):
        """Display masked API key"""
        if obj.key:
            return f"{obj.key[:8]}...{obj.key[-4:]}"
        return "Not generated"
    key_display.short_description = "API Key"
    
    def save_model(self, request, obj, form, change):
        """Generate API key if creating new instance"""
        if not change and not obj.key:
            obj.key = APIKey.generate_key()
        super().save_model(request, obj, form, change)


@admin.register(EmailTemplate)
class EmailTemplateAdmin(admin.ModelAdmin):
    list_display = ['name', 'subject', 'is_active', 'created_at', 'updated_at']
    list_filter = ['is_active', 'created_at', 'updated_at']
    search_fields = ['name', 'subject', 'description']
    readonly_fields = ['created_at', 'updated_at']
    fieldsets = (
        ('Basic Information', {
            'fields': ('name', 'subject', 'description', 'is_active')
        }),
        ('Template Content', {
            'fields': ('html_content', 'text_content'),
            'classes': ('wide',)
        }),
        ('Variables', {
            'fields': ('required_variables',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at', 'updated_at'),
            'classes': ('collapse',)
        }),
    )
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('created_by')


@admin.register(EmailLog)
class EmailLogAdmin(admin.ModelAdmin):
    list_display = [
        'to', 'subject', 'template_name', 'api_key_name', 'status', 
        'sent_at', 'created_at'
    ]
    list_filter = [
        'status', 'template_used', 'api_key', 'created_at', 'sent_at'
    ]
    search_fields = ['to', 'subject', 'from_email', 'message_id']
    readonly_fields = [
        'to', 'subject', 'template_used', 'api_key', 'status', 'error_message',
        'message_id', 'from_email', 'from_name', 'reply_to', 'sent_at', 
        'created_at', 'variables_used', 'attachment_count', 'html_length', 
        'text_length'
    ]
    fieldsets = (
        ('Email Details', {
            'fields': ('to', 'subject', 'from_email', 'from_name', 'reply_to')
        }),
        ('Template & API Key', {
            'fields': ('template_used', 'api_key')
        }),
        ('Status & Delivery', {
            'fields': ('status', 'error_message', 'message_id', 'sent_at')
        }),
        ('Content Information', {
            'fields': ('html_length', 'text_length', 'attachment_count'),
            'classes': ('collapse',)
        }),
        ('Variables Used', {
            'fields': ('variables_used',),
            'classes': ('collapse',)
        }),
        ('Timestamps', {
            'fields': ('created_at',),
            'classes': ('collapse',)
        }),
    )
    
    def template_name(self, obj):
        """Display template name"""
        return obj.template_used.name if obj.template_used else "Custom"
    template_name.short_description = "Template"
    
    def api_key_name(self, obj):
        """Display API key name with link"""
        if obj.api_key:
            url = reverse('admin:api_apikey_change', args=[obj.api_key.id])
            return format_html('<a href="{}">{}</a>', url, obj.api_key.name)
        return "Unknown"
    api_key_name.short_description = "API Key"
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('template_used', 'api_key')
    
    def has_add_permission(self, request):
        """Prevent adding email logs manually"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing email logs"""
        return False


@admin.register(EmailAttachment)
class EmailAttachmentAdmin(admin.ModelAdmin):
    list_display = ['email_log', 'filename', 'content_type', 'size', 'created_at']
    list_filter = ['content_type', 'created_at']
    search_fields = ['filename', 'email_log__to', 'email_log__subject']
    readonly_fields = ['email_log', 'filename', 'content_type', 'size', 'created_at']
    
    def get_queryset(self, request):
        return super().get_queryset(request).select_related('email_log')
    
    def has_add_permission(self, request):
        """Prevent adding attachments manually"""
        return False
    
    def has_change_permission(self, request, obj=None):
        """Prevent editing attachments"""
        return False


# Status System Admin
@admin.register(SystemComponent)
class SystemComponentAdmin(admin.ModelAdmin):
    list_display = ['name', 'description', 'is_active', 'order', 'created_at']
    list_filter = ['is_active', 'created_at']
    search_fields = ['name', 'description']
    ordering = ['order', 'name']


@admin.register(ComponentStatus)
class ComponentStatusAdmin(admin.ModelAdmin):
    list_display = ['component', 'status', 'response_time', 'uptime_percentage', 'created_at']
    list_filter = ['status', 'component', 'created_at']
    search_fields = ['component__name', 'message']
    readonly_fields = ['created_at']
    ordering = ['-created_at']


@admin.register(SystemIncident)
class SystemIncidentAdmin(admin.ModelAdmin):
    list_display = ['title', 'status', 'impact', 'started_at', 'resolved_at', 'created_at']
    list_filter = ['status', 'impact', 'started_at', 'resolved_at']
    search_fields = ['title', 'description']
    filter_horizontal = ['affected_components']
    readonly_fields = ['created_at', 'updated_at']
    ordering = ['-started_at']


@admin.register(SystemMetrics)
class SystemMetricsAdmin(admin.ModelAdmin):
    list_display = ['date', 'uptime_percentage', 'avg_response_time', 'emails_sent', 'api_requests', 'error_rate']
    list_filter = ['date']
    search_fields = ['date']
    readonly_fields = ['created_at']
    ordering = ['-date']


@admin.register(StatusPageSettings)
class StatusPageSettingsAdmin(admin.ModelAdmin):
    list_display = ['site_name', 'show_uptime', 'show_metrics', 'show_incidents', 'auto_refresh_seconds']
    readonly_fields = ['created_at', 'updated_at']
    
    def has_add_permission(self, request):
        """Only allow one settings instance"""
        return not StatusPageSettings.objects.exists()


# Customize admin site
admin.site.site_header = "MailCurrent.io Administration"
admin.site.site_title = "MailCurrent.io Admin"
admin.site.index_title = "MailCurrent.io Management"