import uuid
import re
from django.db.models import Count, Q, Avg
from django.utils import timezone
from django.conf import settings
from .models import EmailLog, EmailTemplate
from .webhook_models import EmailEvent, UnsubscribeList
from .webhook_service import WebhookService
import logging

logger = logging.getLogger('api')


class AnalyticsService:
    """Service for email analytics and tracking"""
    
    @staticmethod
    def add_tracking_to_email(email_log, html_content):
        """Add tracking pixel and link tracking to HTML email"""
        if not html_content:
            return html_content
        
        # Generate tracking pixel ID
        pixel_id = str(uuid.uuid4())
        email_log.tracking_pixel_id = pixel_id
        email_log.save(update_fields=['tracking_pixel_id'])
        
        # Add tracking pixel
        base_url = getattr(settings, 'BASE_URL', 'http://localhost:3099')
        tracking_pixel = f'<img src="{base_url}/api/v1/track/open/{email_log.id}/{pixel_id}/" width="1" height="1" style="display:none;" />'
        
        # Insert tracking pixel before closing body tag
        if '</body>' in html_content:
            html_content = html_content.replace('</body>', f'{tracking_pixel}</body>')
        else:
            html_content += tracking_pixel
        
        # Add link tracking
        html_content = AnalyticsService.add_link_tracking(html_content, email_log.id)
        
        return html_content
    
    @staticmethod
    def add_link_tracking(html_content, email_log_id):
        """Add click tracking to all links in HTML"""
        if not html_content:
            return html_content
        
        # Find all links
        link_pattern = r'<a\s+[^>]*href=["\']([^"\']+)["\'][^>]*>'
        
        def replace_link(match):
            original_tag = match.group(0)
            url = match.group(1)
            
            # Skip tracking for unsubscribe links and other special URLs
            if any(skip in url.lower() for skip in ['unsubscribe', 'unsub', 'opt-out', 'mailto:', 'tel:']):
                return original_tag
            
            # Generate link ID
            link_id = str(uuid.uuid4())[:8]
            
            # Create tracking URL
            base_url = getattr(settings, 'BASE_URL', 'http://localhost:3099')
            tracking_url = f"{base_url}/api/v1/track/click/{email_log_id}/{link_id}/"
            
            # Replace href with tracking URL
            new_tag = re.sub(r'href=["\'][^"\']+["\']', f'href="{tracking_url}"', original_tag)
            
            # Add data attributes for original URL
            if 'data-original-url' not in new_tag:
                new_tag = new_tag.replace('>', f' data-original-url="{url}">')
            
            return new_tag
        
        return re.sub(link_pattern, replace_link, html_content)
    
    @staticmethod
    def track_email_open(email_log, request=None):
        """Track email open event"""
        try:
            event = WebhookService.track_email_event(
                email_log=email_log,
                event_type='opened',
                recipient_email=email_log.to,
                event_data={
                    'ip_address': request.META.get('REMOTE_ADDR') if request else None,
                    'user_agent': request.META.get('HTTP_USER_AGENT', '') if request else '',
                    'timestamp': timezone.now().isoformat()
                },
                request=request
            )
            
            logger.info(f"Tracked email open for {email_log.id}")
            return event
            
        except Exception as e:
            logger.error(f"Error tracking email open: {e}")
            return None
    
    @staticmethod
    def track_link_click(email_log, link_id, original_url, request=None):
        """Track link click event"""
        try:
            event = WebhookService.track_email_event(
                email_log=email_log,
                event_type='clicked',
                recipient_email=email_log.to,
                event_data={
                    'link_id': link_id,
                    'original_url': original_url,
                    'ip_address': request.META.get('REMOTE_ADDR') if request else None,
                    'user_agent': request.META.get('HTTP_USER_AGENT', '') if request else '',
                    'timestamp': timezone.now().isoformat()
                },
                request=request
            )
            
            logger.info(f"Tracked link click for {email_log.id}, link {link_id}")
            return event
            
        except Exception as e:
            logger.error(f"Error tracking link click: {e}")
            return None
    
    @staticmethod
    def get_email_stats(user, days=30):
        """Get comprehensive email statistics for a user"""
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=days)
        
        # Get user's email logs
        email_logs = EmailLog.objects.filter(
            api_key__created_by=user,
            created_at__gte=start_date
        )
        
        # Basic stats
        total_emails = email_logs.count()
        sent_emails = email_logs.filter(status='sent').count()
        failed_emails = email_logs.filter(status='failed').count()
        
        # Event stats
        events = EmailEvent.objects.filter(
            email_log__api_key__created_by=user,
            created_at__gte=start_date
        )
        
        opens = events.filter(event_type='opened').count()
        clicks = events.filter(event_type='clicked').count()
        bounces = events.filter(event_type='bounced').count()
        complaints = events.filter(event_type='complained').count()
        unsubscribes = events.filter(event_type='unsubscribed').count()
        
        # Calculate rates
        open_rate = (opens / sent_emails * 100) if sent_emails > 0 else 0
        click_rate = (clicks / sent_emails * 100) if sent_emails > 0 else 0
        bounce_rate = (bounces / sent_emails * 100) if sent_emails > 0 else 0
        complaint_rate = (complaints / sent_emails * 100) if sent_emails > 0 else 0
        unsubscribe_rate = (unsubscribes / sent_emails * 100) if sent_emails > 0 else 0
        
        # Daily breakdown
        daily_stats = []
        for i in range(days):
            date = start_date + timezone.timedelta(days=i)
            day_logs = email_logs.filter(created_at__date=date.date())
            day_events = events.filter(created_at__date=date.date())
            
            daily_stats.append({
                'date': date.date().isoformat(),
                'emails_sent': day_logs.filter(status='sent').count(),
                'emails_failed': day_logs.filter(status='failed').count(),
                'opens': day_events.filter(event_type='opened').count(),
                'clicks': day_events.filter(event_type='clicked').count(),
                'bounces': day_events.filter(event_type='bounced').count(),
                'complaints': day_events.filter(event_type='complained').count(),
                'unsubscribes': day_events.filter(event_type='unsubscribed').count(),
            })
        
        # Template performance
        template_stats = []
        for template in EmailTemplate.objects.filter(emaillog__api_key__created_by=user).distinct():
            template_logs = email_logs.filter(template_used=template)
            template_events = events.filter(email_log__template_used=template)
            
            template_stats.append({
                'template_name': template.name,
                'emails_sent': template_logs.filter(status='sent').count(),
                'opens': template_events.filter(event_type='opened').count(),
                'clicks': template_events.filter(event_type='clicked').count(),
                'open_rate': (template_events.filter(event_type='opened').count() / template_logs.filter(status='sent').count() * 100) if template_logs.filter(status='sent').count() > 0 else 0,
                'click_rate': (template_events.filter(event_type='clicked').count() / template_logs.filter(status='sent').count() * 100) if template_logs.filter(status='sent').count() > 0 else 0,
            })
        
        return {
            'period': {
                'start_date': start_date.isoformat(),
                'end_date': end_date.isoformat(),
                'days': days
            },
            'overview': {
                'total_emails': total_emails,
                'sent_emails': sent_emails,
                'failed_emails': failed_emails,
                'opens': opens,
                'clicks': clicks,
                'bounces': bounces,
                'complaints': complaints,
                'unsubscribes': unsubscribes
            },
            'rates': {
                'open_rate': round(open_rate, 2),
                'click_rate': round(click_rate, 2),
                'bounce_rate': round(bounce_rate, 2),
                'complaint_rate': round(complaint_rate, 2),
                'unsubscribe_rate': round(unsubscribe_rate, 2)
            },
            'daily_breakdown': daily_stats,
            'template_performance': template_stats
        }
    
    @staticmethod
    def get_recent_events(user, limit=50):
        """Get recent email events for a user"""
        events = EmailEvent.objects.filter(
            email_log__api_key__created_by=user
        ).select_related('email_log').order_by('-created_at')[:limit]
        
        return [{
            'id': event.id,
            'email_log_id': event.email_log.id,
            'event_type': event.event_type,
            'recipient_email': event.recipient_email,
            'email_subject': event.email_log.subject,
            'event_data': event.event_data,
            'created_at': event.created_at
        } for event in events]
    
    @staticmethod
    def get_top_recipients(user, limit=20):
        """Get top email recipients by volume"""
        from django.db.models import Count
        
        recipients = EmailLog.objects.filter(
            api_key__created_by=user,
            status='sent'
        ).values('to').annotate(
            email_count=Count('id'),
            open_count=Count('events', filter=Q(events__event_type='opened')),
            click_count=Count('events', filter=Q(events__event_type='clicked'))
        ).order_by('-email_count')[:limit]
        
        return list(recipients)
    
    @staticmethod
    def get_hourly_stats(user, days=7):
        """Get hourly email sending patterns"""
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=days)
        
        hourly_stats = []
        for hour in range(24):
            hour_logs = EmailLog.objects.filter(
                api_key__created_by=user,
                created_at__gte=start_date,
                created_at__hour=hour,
                status='sent'
            )
            
            hourly_stats.append({
                'hour': hour,
                'emails_sent': hour_logs.count(),
                'opens': EmailEvent.objects.filter(
                    email_log__api_key__created_by=user,
                    created_at__gte=start_date,
                    created_at__hour=hour,
                    event_type='opened'
                ).count(),
                'clicks': EmailEvent.objects.filter(
                    email_log__api_key__created_by=user,
                    created_at__gte=start_date,
                    created_at__hour=hour,
                    event_type='clicked'
                ).count()
            })
        
        return hourly_stats
    
    @staticmethod
    def get_delivery_status_stats(user, days=30):
        """Get detailed delivery status statistics"""
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=days)
        
        email_logs = EmailLog.objects.filter(
            api_key__created_by=user,
            created_at__gte=start_date
        )
        
        # Count by status
        status_counts = {}
        for status, _ in EmailLog.STATUS_CHOICES:
            status_counts[status] = email_logs.filter(status=status).count()
        
        # Get delivery timeline
        delivery_timeline = []
        for i in range(days):
            date = start_date + timezone.timedelta(days=i)
            day_logs = email_logs.filter(created_at__date=date.date())
            
            delivery_timeline.append({
                'date': date.date().isoformat(),
                'delivered': day_logs.filter(status='sent').count(),
                'failed': day_logs.filter(status='failed').count(),
                'bounced': day_logs.filter(status='bounced').count(),
                'queued': day_logs.filter(status='queued').count()
            })
        
        return {
            'status_breakdown': status_counts,
            'delivery_timeline': delivery_timeline,
            'total_emails': email_logs.count(),
            'delivery_rate': (status_counts['sent'] / email_logs.count() * 100) if email_logs.count() > 0 else 0
        }
    
    @staticmethod
    def get_engagement_metrics(user, days=30):
        """Get detailed engagement metrics"""
        end_date = timezone.now()
        start_date = end_date - timezone.timedelta(days=days)
        
        email_logs = EmailLog.objects.filter(
            api_key__created_by=user,
            created_at__gte=start_date,
            status='sent'
        )
        
        events = EmailEvent.objects.filter(
            email_log__api_key__created_by=user,
            created_at__gte=start_date
        )
        
        # Calculate engagement rates
        total_sent = email_logs.count()
        unique_opens = events.filter(event_type='opened').values('email_log').distinct().count()
        unique_clicks = events.filter(event_type='clicked').values('email_log').distinct().count()
        
        # Calculate click-to-open rate (CTOR)
        ctor = (unique_clicks / unique_opens * 100) if unique_opens > 0 else 0
        
        # Get engagement by template
        template_engagement = []
        for template in EmailTemplate.objects.filter(emaillog__api_key__created_by=user).distinct():
            template_logs = email_logs.filter(template_used=template)
            template_events = events.filter(email_log__template_used=template)
            
            template_opens = template_events.filter(event_type='opened').values('email_log').distinct().count()
            template_clicks = template_events.filter(event_type='clicked').values('email_log').distinct().count()
            
            template_engagement.append({
                'template_name': template.name,
                'emails_sent': template_logs.count(),
                'unique_opens': template_opens,
                'unique_clicks': template_clicks,
                'open_rate': (template_opens / template_logs.count() * 100) if template_logs.count() > 0 else 0,
                'click_rate': (template_clicks / template_logs.count() * 100) if template_logs.count() > 0 else 0,
                'ctor': (template_clicks / template_opens * 100) if template_opens > 0 else 0
            })
        
        return {
            'total_sent': total_sent,
            'unique_opens': unique_opens,
            'unique_clicks': unique_clicks,
            'open_rate': (unique_opens / total_sent * 100) if total_sent > 0 else 0,
            'click_rate': (unique_clicks / total_sent * 100) if total_sent > 0 else 0,
            'click_to_open_rate': ctor,
            'template_engagement': template_engagement
        }