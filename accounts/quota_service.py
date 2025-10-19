import logging
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.utils import timezone
from django.conf import settings
from .models import User, Subscription, Plan
from api.models import EmailLog

logger = logging.getLogger('api')


class QuotaNotificationService:
    """Service for handling quota notifications and warnings"""
    
    @staticmethod
    def check_and_send_quota_notifications():
        """Check all active subscriptions and send quota notifications if needed"""
        try:
            active_subscriptions = Subscription.objects.filter(
                status__in=['active', 'trialing']
            ).select_related('user', 'plan')
            
            for subscription in active_subscriptions:
                QuotaNotificationService._check_subscription_quota(subscription)
                
        except Exception as e:
            logger.error(f"Error checking quota notifications: {str(e)}")
    
    @staticmethod
    def _check_subscription_quota(subscription):
        """Check quota for a specific subscription and send notifications if needed"""
        try:
            user = subscription.user
            plan = subscription.plan
            
            # Get current usage
            current_usage = subscription.emails_sent_this_period
            quota_limit = plan.emails_per_month
            usage_percentage = (current_usage / quota_limit) * 100 if quota_limit > 0 else 0
            
            # Check if we should send a warning (80% threshold)
            if usage_percentage >= 80 and usage_percentage < 100:
                if not QuotaNotificationService._has_recent_quota_warning(user):
                    QuotaNotificationService._send_quota_warning(user, subscription, current_usage, quota_limit)
            
            # Check if quota is exceeded
            elif current_usage >= quota_limit:
                if not QuotaNotificationService._has_recent_quota_exceeded(user):
                    QuotaNotificationService._send_quota_exceeded(user, subscription, current_usage, quota_limit)
                    
        except Exception as e:
            logger.error(f"Error checking quota for user {subscription.user.email}: {str(e)}")
    
    @staticmethod
    def _has_recent_quota_warning(user):
        """Check if user has received a quota warning in the last 24 hours"""
        from datetime import timedelta
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        return EmailLog.objects.filter(
            to=user.email,
            subject__icontains='quota warning',
            created_at__gte=cutoff_time
        ).exists()
    
    @staticmethod
    def _has_recent_quota_exceeded(user):
        """Check if user has received a quota exceeded notification in the last 24 hours"""
        from datetime import timedelta
        cutoff_time = timezone.now() - timedelta(hours=24)
        
        return EmailLog.objects.filter(
            to=user.email,
            subject__icontains='quota exceeded',
            created_at__gte=cutoff_time
        ).exists()
    
    @staticmethod
    def _send_quota_warning(user, subscription, current_usage, quota_limit):
        """Send quota warning email"""
        try:
            plan = subscription.plan
            usage_percentage = (current_usage / quota_limit) * 100
            emails_remaining = max(0, quota_limit - current_usage)
            
            # Calculate reset date
            reset_date = subscription.current_period_end.strftime('%B %d, %Y')
            current_period = subscription.current_period_start.strftime('%B %Y')
            
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'MailCurrent.io'),
                'current_period': current_period,
                'usage_percentage': round(usage_percentage, 1),
                'emails_sent': current_usage,
                'quota_limit': quota_limit,
                'emails_remaining': emails_remaining,
                'plan_name': plan.name,
                'reset_date': reset_date,
                'current_year': timezone.now().year,
            }
            
            # Render email content
            html_content = render_to_string('emails/quota_warning.html', context)
            text_content = render_to_string('emails/quota_warning.txt', context)
            
            # Send email
            send_mail(
                subject=f'⚠️ Email Quota Warning - {plan.name} Plan',
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=False
            )
            
            logger.info(f"Quota warning sent to {user.email}")
            
        except Exception as e:
            logger.error(f"Error sending quota warning to {user.email}: {str(e)}")
    
    @staticmethod
    def _send_quota_exceeded(user, subscription, current_usage, quota_limit):
        """Send quota exceeded email"""
        try:
            plan = subscription.plan
            overage_count = max(0, current_usage - quota_limit)
            
            # Calculate reset date
            reset_date = subscription.current_period_end.strftime('%B %d, %Y')
            current_period = subscription.current_period_start.strftime('%B %Y')
            
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'MailCurrent.io'),
                'current_period': current_period,
                'emails_sent': current_usage,
                'quota_limit': quota_limit,
                'overage_count': overage_count,
                'plan_name': plan.name,
                'reset_date': reset_date,
                'current_year': timezone.now().year,
            }
            
            # Render email content
            html_content = render_to_string('emails/quota_exceeded.html', context)
            text_content = render_to_string('emails/quota_exceeded.txt', context)
            
            # Send email
            send_mail(
                subject=f'🚨 Email Quota Exceeded - {plan.name} Plan',
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=False
            )
            
            logger.info(f"Quota exceeded notification sent to {user.email}")
            
        except Exception as e:
            logger.error(f"Error sending quota exceeded notification to {user.email}: {str(e)}")
    
    @staticmethod
    def send_quota_reset_notification(user, subscription):
        """Send notification when quota resets"""
        try:
            plan = subscription.plan
            
            context = {
                'user': user,
                'site_name': getattr(settings, 'SITE_NAME', 'MailCurrent.io'),
                'plan_name': plan.name,
                'quota_limit': plan.emails_per_month,
                'current_year': timezone.now().year,
            }
            
            # Render email content
            html_content = render_to_string('emails/quota_reset.html', context)
            text_content = render_to_string('emails/quota_reset.txt', context)
            
            # Send email
            send_mail(
                subject=f'✅ Email Quota Reset - {plan.name} Plan',
                message=text_content,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_content,
                fail_silently=False
            )
            
            logger.info(f"Quota reset notification sent to {user.email}")
            
        except Exception as e:
            logger.error(f"Error sending quota reset notification to {user.email}: {str(e)}")
