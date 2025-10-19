from rest_framework import serializers
from .webhook_models import WebhookEndpoint, WebhookDelivery, EmailEvent, UnsubscribeList


class WebhookEndpointSerializer(serializers.ModelSerializer):
    """Serializer for webhook endpoints"""
    
    class Meta:
        model = WebhookEndpoint
        fields = [
            'id', 'name', 'url', 'events', 'is_active', 'retry_count',
            'timeout_seconds', 'created_at', 'updated_at'
        ]
        read_only_fields = ['id', 'created_at', 'updated_at']
    
    def validate_events(self, value):
        """Validate webhook events"""
        valid_events = [choice[0] for choice in WebhookEndpoint.WEBHOOK_EVENTS]
        for event in value:
            if event not in valid_events:
                raise serializers.ValidationError(f"Invalid event: {event}")
        return value
    
    def validate_url(self, value):
        """Validate webhook URL"""
        if not value.startswith(('http://', 'https://')):
            raise serializers.ValidationError("URL must start with http:// or https://")
        return value


class WebhookDeliverySerializer(serializers.ModelSerializer):
    """Serializer for webhook delivery attempts"""
    webhook_endpoint_name = serializers.CharField(source='webhook_endpoint.name', read_only=True)
    
    class Meta:
        model = WebhookDelivery
        fields = [
            'id', 'webhook_endpoint', 'webhook_endpoint_name', 'event_type',
            'status', 'response_status', 'response_body', 'attempt_count',
            'last_attempt_at', 'next_retry_at', 'created_at', 'updated_at'
        ]
        read_only_fields = [
            'id', 'webhook_endpoint', 'event_type', 'status', 'response_status',
            'response_body', 'attempt_count', 'last_attempt_at', 'next_retry_at',
            'created_at', 'updated_at'
        ]


class EmailEventSerializer(serializers.ModelSerializer):
    """Serializer for email events"""
    email_subject = serializers.CharField(source='email_log.subject', read_only=True)
    email_to = serializers.EmailField(source='email_log.to', read_only=True)
    
    class Meta:
        model = EmailEvent
        fields = [
            'id', 'email_log', 'email_subject', 'email_to', 'event_type',
            'recipient_email', 'event_data', 'ip_address', 'user_agent',
            'created_at'
        ]
        read_only_fields = [
            'id', 'email_log', 'event_type', 'recipient_email', 'event_data',
            'ip_address', 'user_agent', 'created_at'
        ]


class UnsubscribeListSerializer(serializers.ModelSerializer):
    """Serializer for unsubscribe list"""
    
    class Meta:
        model = UnsubscribeList
        fields = [
            'id', 'email', 'reason', 'source', 'created_at'
        ]
        read_only_fields = ['id', 'created_at']


class WebhookTestSerializer(serializers.Serializer):
    """Serializer for testing webhooks"""
    event_type = serializers.ChoiceField(choices=WebhookEndpoint.WEBHOOK_EVENTS)
    test_data = serializers.JSONField(required=False, default=dict)
    
    def validate_event_type(self, value):
        """Validate event type"""
        valid_events = [choice[0] for choice in WebhookEndpoint.WEBHOOK_EVENTS]
        if value not in valid_events:
            raise serializers.ValidationError(f"Invalid event type: {value}")
        return value


class UnsubscribeRequestSerializer(serializers.Serializer):
    """Serializer for unsubscribe requests"""
    email = serializers.EmailField()
    reason = serializers.CharField(required=False, allow_blank=True)
    
    def validate_email(self, value):
        """Validate email format"""
        return value.lower().strip()


class ResubscribeRequestSerializer(serializers.Serializer):
    """Serializer for resubscribe requests"""
    email = serializers.EmailField()
    
    def validate_email(self, value):
        """Validate email format"""
        return value.lower().strip()
