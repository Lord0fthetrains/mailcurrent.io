from rest_framework import serializers
from .models import APIKey, EmailTemplate, EmailLog, EmailAttachment


class EmailTemplateSerializer(serializers.ModelSerializer):
    """Serializer for email templates"""
    
    class Meta:
        model = EmailTemplate
        fields = ['name', 'subject', 'description', 'required_variables', 'is_active', 'created_at']


class EmailLogSerializer(serializers.ModelSerializer):
    """Serializer for email logs"""
    template_name = serializers.CharField(source='template_used.name', read_only=True)
    api_key_name = serializers.CharField(source='api_key.name', read_only=True)
    
    class Meta:
        model = EmailLog
        fields = [
            'id', 'to', 'subject', 'template_name', 'api_key_name', 'status',
            'error_message', 'message_id', 'from_email', 'from_name', 'reply_to',
            'sent_at', 'created_at', 'attachment_count', 'html_length', 'text_length'
        ]


class SendTemplateEmailSerializer(serializers.Serializer):
    """Serializer for sending template-based emails"""
    template = serializers.CharField(max_length=100, help_text="Template name")
    to = serializers.EmailField(help_text="Recipient email address")
    variables = serializers.JSONField(default=dict, help_text="Template variables")
    from_email = serializers.EmailField(required=False, help_text="Override sender email")
    from_name = serializers.CharField(max_length=100, required=False, help_text="Override sender name")
    reply_to = serializers.EmailField(required=False, help_text="Reply-to email address")
    
    def validate_template(self, value):
        """Validate that template exists and is active"""
        try:
            template = EmailTemplate.objects.get(name=value, is_active=True)
            return value
        except EmailTemplate.DoesNotExist:
            raise serializers.ValidationError(f"Template '{value}' not found or inactive")
    
    def validate_variables(self, value):
        """Validate template variables"""
        if not isinstance(value, dict):
            raise serializers.ValidationError("Variables must be a dictionary")
        return value


class SendCustomEmailSerializer(serializers.Serializer):
    """Serializer for sending custom emails"""
    to = serializers.EmailField(help_text="Recipient email address")
    subject = serializers.CharField(max_length=200, help_text="Email subject")
    html = serializers.CharField(required=False, help_text="HTML content")
    text = serializers.CharField(required=False, help_text="Plain text content")
    from_email = serializers.EmailField(required=False, help_text="Override sender email")
    from_name = serializers.CharField(max_length=100, required=False, help_text="Override sender name")
    reply_to = serializers.EmailField(required=False, help_text="Reply-to email address")
    attachments = serializers.ListField(
        child=serializers.DictField(),
        required=False,
        help_text="List of attachments"
    )
    headers = serializers.DictField(required=False, help_text="Custom email headers")
    
    def validate(self, data):
        """Validate that at least HTML or text content is provided"""
        if not data.get('html') and not data.get('text'):
            raise serializers.ValidationError("Either 'html' or 'text' content must be provided")
        return data
    
    def validate_attachments(self, value):
        """Validate attachment format"""
        if not value:
            return value
        
        for attachment in value:
            required_fields = ['filename', 'content', 'mimetype']
            for field in required_fields:
                if field not in attachment:
                    raise serializers.ValidationError(f"Attachment missing required field: {field}")
        
        return value


class APIKeySerializer(serializers.ModelSerializer):
    """Serializer for API keys"""
    key_display = serializers.SerializerMethodField()
    key = serializers.SerializerMethodField()
    
    class Meta:
        model = APIKey
        fields = [
            'id', 'name', 'key', 'key_display', 'is_active', 'rate_limit',
            'default_from_email', 'default_from_name', 'allowed_domains',
            'custom_smtp_host', 'custom_smtp_port', 'custom_smtp_username',
            'custom_smtp_use_tls', 'custom_smtp_use_ssl',
            'created_at', 'last_used_at'
        ]
        read_only_fields = ['id', 'created_at', 'last_used_at']
        extra_kwargs = {
            'custom_smtp_password': {'write_only': True}
        }
    
    def get_key_display(self, obj):
        """Return masked API key for display"""
        return f"{obj.key[:8]}..." if obj.key else ""
    
    def get_key(self, obj):
        """Return full API key for the owner"""
        # Only return the full key if the user is the owner
        request = self.context.get('request')
        if request and hasattr(request, 'user') and obj.created_by == request.user:
            return obj.key
        return None


class CreateAPIKeySerializer(serializers.ModelSerializer):
    """Serializer for creating new API keys"""
    
    class Meta:
        model = APIKey
        fields = [
            'name', 'is_active', 'rate_limit', 'default_from_email',
            'default_from_name', 'allowed_domains'
        ]
    
    def create(self, validated_data):
        """Create new API key with generated key"""
        api_key = APIKey.objects.create(**validated_data)
        return api_key


class EmailStatsSerializer(serializers.Serializer):
    """Serializer for email statistics"""
    total_emails = serializers.IntegerField()
    sent_emails = serializers.IntegerField()
    failed_emails = serializers.IntegerField()
    bounced_emails = serializers.IntegerField()
    queued_emails = serializers.IntegerField()


class ValidateAPIKeySerializer(serializers.Serializer):
    """Serializer for API key validation"""
    valid = serializers.BooleanField()
    api_key_name = serializers.CharField(required=False)
    rate_limit = serializers.IntegerField(required=False)
    is_active = serializers.BooleanField(required=False)
