from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.shortcuts import get_object_or_404
from .analytics_service import AnalyticsService
from .webhook_models import EmailEvent
from .models import EmailLog
import logging

logger = logging.getLogger('api')


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def email_stats(request):
    """Get comprehensive email statistics"""
    try:
        days = int(request.GET.get('days', 30))
        if days > 365:
            days = 365  # Limit to 1 year max
        
        stats = AnalyticsService.get_email_stats(request.user, days)
        
        return Response({
            'success': True,
            'stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting email stats: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def recent_events(request):
    """Get recent email events"""
    try:
        limit = int(request.GET.get('limit', 50))
        if limit > 200:
            limit = 200  # Limit to 200 max
        
        events = AnalyticsService.get_recent_events(request.user, limit)
        
        return Response({
            'success': True,
            'events': events
        })
        
    except Exception as e:
        logger.error(f"Error getting recent events: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def top_recipients(request):
    """Get top email recipients"""
    try:
        limit = int(request.GET.get('limit', 20))
        if limit > 100:
            limit = 100  # Limit to 100 max
        
        recipients = AnalyticsService.get_top_recipients(request.user, limit)
        
        return Response({
            'success': True,
            'recipients': recipients
        })
        
    except Exception as e:
        logger.error(f"Error getting top recipients: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def hourly_stats(request):
    """Get hourly email sending patterns"""
    try:
        days = int(request.GET.get('days', 7))
        if days > 30:
            days = 30  # Limit to 30 days max
        
        stats = AnalyticsService.get_hourly_stats(request.user, days)
        
        return Response({
            'success': True,
            'hourly_stats': stats
        })
        
    except Exception as e:
        logger.error(f"Error getting hourly stats: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def email_performance(request, email_log_id):
    """Get detailed performance for a specific email"""
    try:
        email_log = get_object_or_404(EmailLog, id=email_log_id, api_key__created_by=request.user)
        
        # Get events for this email
        events = EmailEvent.objects.filter(email_log=email_log).order_by('-created_at')
        
        # Count events by type
        event_counts = {}
        for event_type, _ in EmailEvent.EVENT_TYPES:
            event_counts[event_type] = events.filter(event_type=event_type).count()
        
        # Get recent events
        recent_events = [{
            'id': event.id,
            'event_type': event.event_type,
            'recipient_email': event.recipient_email,
            'event_data': event.event_data,
            'created_at': event.created_at
        } for event in events[:20]]
        
        return Response({
            'success': True,
            'email_log': {
                'id': email_log.id,
                'to': email_log.to,
                'subject': email_log.subject,
                'status': email_log.status,
                'sent_at': email_log.sent_at,
                'created_at': email_log.created_at
            },
            'event_counts': event_counts,
            'recent_events': recent_events
        })
        
    except Exception as e:
        logger.error(f"Error getting email performance: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def dashboard_summary(request):
    """Get dashboard summary statistics"""
    try:
        # Get stats for last 30 days
        stats = AnalyticsService.get_email_stats(request.user, 30)
        
        # Get recent events
        recent_events = AnalyticsService.get_recent_events(request.user, 10)
        
        # Get top recipients
        top_recipients = AnalyticsService.get_top_recipients(request.user, 5)
        
        return Response({
            'success': True,
            'summary': {
                'total_emails': stats['overview']['total_emails'],
                'sent_emails': stats['overview']['sent_emails'],
                'open_rate': stats['rates']['open_rate'],
                'click_rate': stats['rates']['click_rate'],
                'bounce_rate': stats['rates']['bounce_rate']
            },
            'recent_events': recent_events,
            'top_recipients': top_recipients
        })
        
    except Exception as e:
        logger.error(f"Error getting dashboard summary: {e}")
        return Response({
            'success': False,
            'message': str(e)
        }, status=status.HTTP_400_BAD_REQUEST)
