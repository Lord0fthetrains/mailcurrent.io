import requests
import json
import hmac
import hashlib
import time
from django.conf import settings
from django.utils import timezone
from django.core.exceptions import ValidationError
from .webhook_models import WebhookEndpoint, WebhookDelivery, EmailEvent
import logging

logger = logging.getLogger('api')


class WebhookService:
    """Service for handling webhook deliveries and event tracking"""
    
    @staticmethod
    def create_signature(payload, secret):
        """Create HMAC signature for webhook payload"""
        return hmac.new(
            secret.encode('utf-8'),
            payload.encode('utf-8'),
            hashlib.sha256
        ).hexdigest()
    
    @staticmethod
    def send_webhook(webhook_endpoint, event_type, data):
        """Send webhook notification to endpoint"""
        try:
            # Prepare payload
            payload = {
                'event': event_type,
                'data': data,
                'timestamp': timezone.now().isoformat(),
                'id': str(time.time())
            }
            
            payload_json = json.dumps(payload, default=str)
            signature = WebhookService.create_signature(payload_json, webhook_endpoint.secret)
            
            # Prepare headers
            headers = {
                'Content-Type': 'application/json',
                'X-Webhook-Signature': f'sha256={signature}',
                'X-Webhook-Event': event_type,
                'User-Agent': 'Email-API-Webhook/1.0'
            }
            
            # Create webhook delivery record
            delivery = WebhookDelivery.objects.create(
                webhook_endpoint=webhook_endpoint,
                event_type=event_type,
                payload=payload,
                status='pending'
            )
            
            # Send webhook
            response = requests.post(
                webhook_endpoint.url,
                data=payload_json,
                headers=headers,
                timeout=webhook_endpoint.timeout_seconds
            )
            
            # Update delivery record
            delivery.response_status = response.status_code
            delivery.response_body = response.text[:1000]  # Limit response body
            delivery.attempt_count += 1
            delivery.last_attempt_at = timezone.now()
            
            if response.status_code >= 200 and response.status_code < 300:
                delivery.status = 'delivered'
                logger.info(f"Webhook delivered successfully to {webhook_endpoint.url}")
            else:
                delivery.status = 'failed'
                logger.warning(f"Webhook failed to {webhook_endpoint.url}: {response.status_code}")
                
                # Schedule retry if within retry limit
                if delivery.attempt_count < webhook_endpoint.retry_count:
                    delivery.status = 'retrying'
                    delivery.next_retry_at = timezone.now() + timezone.timedelta(
                        minutes=2 ** delivery.attempt_count  # Exponential backoff
                    )
            
            delivery.save()
            return delivery
            
        except requests.exceptions.RequestException as e:
            logger.error(f"Webhook request failed to {webhook_endpoint.url}: {e}")
            
            # Update delivery record
            delivery.response_body = str(e)[:1000]
            delivery.attempt_count += 1
            delivery.last_attempt_at = timezone.now()
            
            if delivery.attempt_count < webhook_endpoint.retry_count:
                delivery.status = 'retrying'
                delivery.next_retry_at = timezone.now() + timezone.timedelta(
                    minutes=2 ** delivery.attempt_count
                )
            else:
                delivery.status = 'failed'
            
            delivery.save()
            return delivery
            
        except Exception as e:
            logger.error(f"Unexpected error sending webhook to {webhook_endpoint.url}: {e}")
            return None
    
    @staticmethod
    def send_event_webhooks(email_log, event_type, event_data=None):
        """Send webhook notifications for email events"""
        if not event_data:
            event_data = {}
        
        # Get all active webhook endpoints for the user
        user = email_log.api_key.created_by if hasattr(email_log.api_key, 'created_by') else None
        if not user:
            return
        
        webhook_endpoints = WebhookEndpoint.objects.filter(
            user=user,
            is_active=True,
            events__contains=[event_type]
        )
        
        # Prepare event data
        webhook_data = {
            'email_log_id': email_log.id,
            'to_email': email_log.to_email,
            'from_email': email_log.from_email,
            'subject': email_log.subject,
            'template_used': email_log.template_used,
            'sent_at': email_log.sent_at.isoformat() if email_log.sent_at else None,
            'event_data': event_data
        }
        
        # Send to all matching endpoints
        for endpoint in webhook_endpoints:
            WebhookService.send_webhook(endpoint, event_type, webhook_data)
    
    @staticmethod
    def track_email_event(email_log, event_type, recipient_email, event_data=None, request=None):
        """Track email event and send webhooks"""
        if not event_data:
            event_data = {}
        
        # Extract request info if available
        ip_address = None
        user_agent = ''
        if request:
            ip_address = request.META.get('REMOTE_ADDR')
            user_agent = request.META.get('HTTP_USER_AGENT', '')
        
        # Create event record
        event = EmailEvent.objects.create(
            email_log=email_log,
            event_type=event_type,
            recipient_email=recipient_email,
            event_data=event_data,
            ip_address=ip_address,
            user_agent=user_agent
        )
        
        # Send webhook notifications
        WebhookService.send_event_webhooks(email_log, event_type, event_data)
        
        logger.info(f"Tracked {event_type} event for email {email_log.id}")
        return event
    
    @staticmethod
    def retry_failed_webhooks():
        """Retry failed webhook deliveries"""
        now = timezone.now()
        failed_deliveries = WebhookDelivery.objects.filter(
            status='retrying',
            next_retry_at__lte=now
        )
        
        for delivery in failed_deliveries:
            WebhookService.send_webhook(
                delivery.webhook_endpoint,
                delivery.event_type,
                delivery.payload
            )
    
    @staticmethod
    def cleanup_old_deliveries(days=30):
        """Clean up old webhook delivery records"""
        cutoff_date = timezone.now() - timezone.timedelta(days=days)
        deleted_count = WebhookDelivery.objects.filter(
            created_at__lt=cutoff_date,
            status__in=['delivered', 'failed']
        ).delete()[0]
        
        logger.info(f"Cleaned up {deleted_count} old webhook delivery records")
        return deleted_count


class UnsubscribeService:
    """Service for managing unsubscribe functionality"""
    
    @staticmethod
    def is_unsubscribed(email):
        """Check if email is in unsubscribe list"""
        return UnsubscribeList.objects.filter(email__iexact=email).exists()
    
    @staticmethod
    def add_to_unsubscribe_list(email, reason='', source='manual', user=None):
        """Add email to unsubscribe list"""
        unsubscribe, created = UnsubscribeList.objects.get_or_create(
            email__iexact=email,
            defaults={
                'email': email,
                'reason': reason,
                'source': source,
                'user': user
            }
        )
        
        if created:
            logger.info(f"Added {email} to unsubscribe list")
        else:
            logger.info(f"{email} already in unsubscribe list")
        
        return unsubscribe
    
    @staticmethod
    def generate_unsubscribe_url(email_log, base_url=None):
        """Generate unsubscribe URL for email"""
        if not base_url:
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:3099')
        
        # Create a secure token for unsubscribe
        import secrets
        token = secrets.token_urlsafe(32)
        
        # Store token in email_log for verification
        email_log.unsubscribe_token = token
        email_log.save(update_fields=['unsubscribe_token'])
        
        return f"{base_url}/api/v1/unsubscribe/{email_log.id}/{token}/"
    
    @staticmethod
    def process_unsubscribe(email_log_id, token, reason='', source='link'):
        """Process unsubscribe request"""
        try:
            email_log = EmailLog.objects.get(id=email_log_id, unsubscribe_token=token)
            
            # Add to unsubscribe list
            UnsubscribeService.add_to_unsubscribe_list(
                email_log.to_email,
                reason=reason,
                source=source,
                user=email_log.api_key.created_by if hasattr(email_log.api_key, 'created_by') else None
            )
            
            # Track unsubscribe event
            WebhookService.track_email_event(
                email_log,
                'unsubscribed',
                email_log.to_email,
                {'reason': reason, 'source': source}
            )
            
            return True
            
        except EmailLog.DoesNotExist:
            logger.warning(f"Invalid unsubscribe token for email_log {email_log_id}")
            return False
