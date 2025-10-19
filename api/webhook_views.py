from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_POST
from django.utils.decorators import method_decorator
from django.utils import timezone
from .webhook_models import WebhookEndpoint, WebhookDelivery, EmailEvent, UnsubscribeList
from .webhook_service import WebhookService, UnsubscribeService
from .models import EmailLog
from .webhook_serializers import WebhookEndpointSerializer, WebhookDeliverySerializer, EmailEventSerializer
import logging

logger = logging.getLogger('api')


class WebhookEndpointListCreateView(generics.ListCreateAPIView):
    """List and create webhook endpoints"""
    serializer_class = WebhookEndpointSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return WebhookEndpoint.objects.filter(user=self.request.user)
    
    def perform_create(self, serializer):
        serializer.save(user=self.request.user)


class WebhookEndpointDetailView(generics.RetrieveUpdateDestroyAPIView):
    """Retrieve, update, or delete webhook endpoint"""
    serializer_class = WebhookEndpointSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return WebhookEndpoint.objects.filter(user=self.request.user)


class WebhookDeliveryListView(generics.ListAPIView):
    """List webhook delivery attempts"""
    serializer_class = WebhookDeliverySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return WebhookDelivery.objects.filter(
            webhook_endpoint__user=self.request.user
        ).order_by('-created_at')


class EmailEventListView(generics.ListAPIView):
    """List email events for user's emails"""
    serializer_class = EmailEventSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return EmailEvent.objects.filter(
            email_log__api_key__created_by=self.request.user
        ).order_by('-created_at')


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def test_webhook(request, webhook_id):
    """Test webhook endpoint with sample data"""
    try:
        webhook = get_object_or_404(WebhookEndpoint, id=webhook_id, user=request.user)
        
        # Create test payload
        test_data = {
            'email_log_id': 123,
            'to_email': 'test@example.com',
            'from_email': 'noreply@example.com',
            'subject': 'Test Email',
            'template_used': 'test',
            'sent_at': '2024-01-01T00:00:00Z',
            'event_data': {'test': True}
        }
        
        # Send test webhook
        delivery = WebhookService.send_webhook(webhook, 'email.sent', test_data)
        
        return Response({
            'success': True,
            'message': 'Test webhook sent',
            'delivery_id': delivery.id,
            'status': delivery.status
        })
        
    except Exception as e:
        logger.error(f"Error testing webhook {webhook_id}: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
def unsubscribe_view(request, email_log_id, token):
    """Handle unsubscribe requests"""
    try:
        success = UnsubscribeService.process_unsubscribe(
            email_log_id=email_log_id,
            token=token,
            reason=request.GET.get('reason', ''),
            source='link'
        )
        
        if success:
            return Response({
                'success': True,
                'message': 'You have been successfully unsubscribed from future emails.'
            })
        else:
            return Response({
                'success': False,
                'message': 'Invalid unsubscribe link or already unsubscribed.'
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error processing unsubscribe: {e}")
        return Response({
            'success': False,
            'message': 'An error occurred while processing your unsubscribe request.'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def unsubscribe_email(request):
    """Manually unsubscribe an email address"""
    email = request.data.get('email')
    reason = request.data.get('reason', '')
    
    if not email:
        return Response({
            'success': False,
            'message': 'Email address is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        UnsubscribeService.add_to_unsubscribe_list(
            email=email,
            reason=reason,
            source='manual',
            user=request.user
        )
        
        return Response({
            'success': True,
            'message': f'{email} has been unsubscribed'
        })
        
    except Exception as e:
        logger.error(f"Error unsubscribing email {email}: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def unsubscribe_list(request):
    """Get list of unsubscribed emails for user"""
    try:
        unsubscribes = UnsubscribeList.objects.filter(user=request.user).order_by('-created_at')
        
        data = [{
            'email': unsubscribe.email,
            'reason': unsubscribe.reason,
            'source': unsubscribe.source,
            'created_at': unsubscribe.created_at
        } for unsubscribe in unsubscribes]
        
        return Response({
            'success': True,
            'unsubscribes': data
        })
        
    except Exception as e:
        logger.error(f"Error getting unsubscribe list: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def resubscribe_email(request):
    """Resubscribe an email address"""
    email = request.data.get('email')
    
    if not email:
        return Response({
            'success': False,
            'message': 'Email address is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    try:
        unsubscribe = UnsubscribeList.objects.filter(
            email__iexact=email,
            user=request.user
        ).first()
        
        if unsubscribe:
            unsubscribe.delete()
            return Response({
                'success': True,
                'message': f'{email} has been resubscribed'
            })
        else:
            return Response({
                'success': False,
                'message': 'Email not found in unsubscribe list'
            }, status=status.HTTP_404_NOT_FOUND)
            
    except Exception as e:
        logger.error(f"Error resubscribing email {email}: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@csrf_exempt
@require_POST
def email_tracking_pixel(request, email_log_id, pixel_id):
    """Handle email open tracking pixel"""
    try:
        email_log = get_object_or_404(EmailLog, id=email_log_id, tracking_pixel_id=pixel_id)
        
        # Track open event
        WebhookService.track_email_event(
            email_log=email_log,
            event_type='opened',
            recipient_email=email_log.to,
            event_data={
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'timestamp': timezone.now().isoformat()
            },
            request=request
        )
        
        # Return 1x1 transparent pixel
        from django.http import HttpResponse
        pixel_data = b'\x89PNG\r\n\x1a\n\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01\x08\x06\x00\x00\x00\x1f\x15\xc4\x89\x00\x00\x00\nIDATx\x9cc\x00\x01\x00\x00\x05\x00\x01\r\n-\xdb\x00\x00\x00\x00IEND\xaeB`\x82'
        return HttpResponse(pixel_data, content_type='image/png')
        
    except Exception as e:
        logger.error(f"Error tracking email open: {e}")
        # Return empty response
        return HttpResponse(status=204)


@api_view(['GET'])
def link_click_tracking(request, email_log_id, link_id):
    """Handle link click tracking"""
    try:
        email_log = get_object_or_404(EmailLog, id=email_log_id)
        
        # Get the original URL from the link_id (you'd need to store this mapping)
        # For now, we'll just track the click
        WebhookService.track_email_event(
            email_log=email_log,
            event_type='clicked',
            recipient_email=email_log.to,
            event_data={
                'link_id': link_id,
                'ip_address': request.META.get('REMOTE_ADDR'),
                'user_agent': request.META.get('HTTP_USER_AGENT', ''),
                'timestamp': timezone.now().isoformat()
            },
            request=request
        )
        
        # Redirect to original URL (you'd need to implement URL mapping)
        return Response({
            'success': True,
            'message': 'Click tracked',
            'redirect_url': f'https://example.com/clicked-link-{link_id}'
        })
        
    except Exception as e:
        logger.error(f"Error tracking link click: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
