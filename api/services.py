import base64
import logging
from typing import Dict, List, Optional, Tuple
from django.core.mail import EmailMultiAlternatives
from django.template.loader import render_to_string
from django.conf import settings
from django.utils import timezone
from jinja2 import Template, TemplateError
import bleach
from .models import APIKey, EmailTemplate, EmailLog, EmailAttachment
from .analytics_service import AnalyticsService

logger = logging.getLogger('api')


class EmailService:
    """Service class for handling email operations"""
    
    def __init__(self):
        self.allowed_tags = [
            'p', 'br', 'strong', 'em', 'u', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6',
            'ul', 'ol', 'li', 'a', 'img', 'div', 'span', 'table', 'tr', 'td', 'th',
            'thead', 'tbody', 'tfoot', 'blockquote', 'hr'
        ]
        self.allowed_attributes = {
            'a': ['href', 'title', 'target'],
            'img': ['src', 'alt', 'title', 'width', 'height'],
            'table': ['border', 'cellpadding', 'cellspacing', 'width'],
            'td': ['colspan', 'rowspan', 'width', 'height'],
            'th': ['colspan', 'rowspan', 'width', 'height'],
        }

    def send_template_email(
        self, 
        template_name: str, 
        to_email: str, 
        variables: Dict = None, 
        api_key: APIKey = None,
        from_email: str = None,
        from_name: str = None,
        reply_to: str = None
    ) -> Tuple[bool, str]:
        """
        Send email using a predefined template
        
        Args:
            template_name: Name of the template to use
            to_email: Recipient email address
            variables: Dictionary of variables for template rendering
            api_key: API key object for authentication and defaults
            from_email: Override sender email
            from_name: Override sender name
            reply_to: Reply-to email address
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Check quota before sending
            if api_key and api_key.created_by:
                quota_check = self._check_quota(api_key.created_by)
                if not quota_check['can_send']:
                    return False, quota_check['message']
                
                # Check if user's email is verified
                if not api_key.created_by.is_verified:
                    return False, "Email verification required. Please verify your email address before sending emails via API."
                
                # Check if user account is active
                if not api_key.created_by.is_active:
                    return False, "Account suspended. Your account has been deactivated. Please contact support for assistance."
            
            # Get template
            template = EmailTemplate.objects.get(name=template_name, is_active=True)
            
            # Validate variables
            template.validate_variables(variables or {})
            
            # Render template
            subject = self._render_template(template.subject, variables or {})
            html_content = self._render_template(template.html_content, variables or {})
            text_content = self._render_template(template.text_content, variables or {})
            
            # Sanitize HTML
            html_content = self._sanitize_html(html_content)
            
            # Determine sender information
            sender_email, sender_name = self._get_sender_info(
                api_key, from_email, from_name
            )
            
            # Create email log
            email_log = EmailLog.objects.create(
                to=to_email,
                subject=subject,
                template_used=template,
                api_key=api_key,
                from_email=sender_email,
                from_name=sender_name or '',
                reply_to=reply_to,
                variables_used=variables or {},
                html_length=len(html_content),
                text_length=len(text_content)
            )
            
            # Send email
            success, message = self._send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                from_email=sender_email,
                from_name=sender_name,
                reply_to=reply_to,
                email_log=email_log,
                api_key=api_key
            )
            
            # Increment usage if email was sent successfully
            if success and api_key and api_key.created_by:
                self._increment_usage(api_key.created_by)
            
            return success, message
            
        except EmailTemplate.DoesNotExist:
            logger.error(f"Template not found: {template_name}")
            return False, f"Template '{template_name}' not found"
        except TemplateError as e:
            logger.error(f"Template rendering error: {str(e)}")
            return False, f"Template rendering error: {str(e)}"
        except Exception as e:
            logger.error(f"Template email error: {str(e)}")
            return False, f"Email sending failed: {str(e)}"

    def send_custom_email(
        self,
        to_email: str,
        subject: str,
        html_content: str = None,
        text_content: str = None,
        api_key: APIKey = None,
        from_email: str = None,
        from_name: str = None,
        reply_to: str = None,
        attachments: List[Dict] = None,
        headers: Dict = None
    ) -> Tuple[bool, str]:
        """
        Send custom email with full HTML/text content
        
        Args:
            to_email: Recipient email address
            subject: Email subject
            html_content: HTML content
            text_content: Plain text content
            api_key: API key object for authentication and defaults
            from_email: Override sender email
            from_name: Override sender name
            reply_to: Reply-to email address
            attachments: List of attachment dictionaries
            headers: Custom email headers
            
        Returns:
            Tuple of (success, message)
        """
        try:
            # Check quota before sending
            if api_key and api_key.created_by:
                quota_check = self._check_quota(api_key.created_by)
                if not quota_check['can_send']:
                    return False, quota_check['message']
                
                # Check if user's email is verified
                if not api_key.created_by.is_verified:
                    return False, "Email verification required. Please verify your email address before sending emails via API."
                
                # Check if user account is active
                if not api_key.created_by.is_active:
                    return False, "Account suspended. Your account has been deactivated. Please contact support for assistance."
            
            # Determine sender information
            sender_email, sender_name = self._get_sender_info(
                api_key, from_email, from_name
            )
            
            # Sanitize HTML if provided
            if html_content:
                html_content = self._sanitize_html(html_content)
            
            # Create email log
            email_log = EmailLog.objects.create(
                to=to_email,
                subject=subject,
                api_key=api_key,
                from_email=sender_email,
                from_name=sender_name or '',
                reply_to=reply_to,
                html_length=len(html_content or ''),
                text_length=len(text_content or ''),
                attachment_count=len(attachments or [])
            )
            
            # Add tracking to HTML content
            if html_content:
                html_content = AnalyticsService.add_tracking_to_email(email_log, html_content)
            
            # Process attachments
            processed_attachments = []
            if attachments:
                processed_attachments = self._process_attachments(attachments, email_log)
            
            # Send email
            success, message = self._send_email(
                to_email=to_email,
                subject=subject,
                html_content=html_content,
                text_content=text_content,
                from_email=sender_email,
                from_name=sender_name,
                reply_to=reply_to,
                attachments=processed_attachments,
                headers=headers or {},
                email_log=email_log,
                api_key=api_key
            )
            
            # Increment usage if email was sent successfully
            if success and api_key and api_key.created_by:
                self._increment_usage(api_key.created_by)
            
            return success, message
            
        except Exception as e:
            logger.error(f"Custom email error: {str(e)}")
            return False, f"Email sending failed: {str(e)}"

    def _get_sender_info(self, api_key: APIKey, from_email: str = None, from_name: str = None) -> Tuple[str, str]:
        """Get sender email and name with proper fallback hierarchy"""
        
        # Priority: request > API key defaults > system defaults
        sender_email = (
            from_email or 
            (api_key.default_from_email if api_key else None) or 
            settings.DEFAULT_FROM_EMAIL
        )
        
        sender_name = (
            from_name or 
            (api_key.default_from_name if api_key else None) or 
            settings.DEFAULT_FROM_NAME
        )
        
        # Validate SMTP configuration for custom domains
        if api_key and sender_email != settings.DEFAULT_FROM_EMAIL:
            domain = sender_email.split('@')[1] if '@' in sender_email else ''
            
            # If allowed_domains is not empty, check if this domain is allowed
            if api_key.allowed_domains and len(api_key.allowed_domains) > 0:
                if domain in [d.lower() for d in api_key.allowed_domains]:
                    # This domain is in allowed_domains, so it should use custom SMTP
                    if not api_key.custom_smtp_host or not api_key.custom_smtp_username or not api_key.custom_smtp_password:
                        raise ValueError("Invalid or inactive API key SMTP Details")
                else:
                    # This domain is not in allowed_domains, reject it
                    raise ValueError(f"Sender domain '{domain}' not allowed for this API key")
            else:
                # If allowed_domains is empty or None, any custom domain requires SMTP configuration
                if not api_key.custom_smtp_host or not api_key.custom_smtp_username or not api_key.custom_smtp_password:
                    raise ValueError("Invalid or inactive API key SMTP Details")
        
        return sender_email, sender_name

    def _render_template(self, template_content: str, variables: Dict) -> str:
        """Render Jinja2 template with variables"""
        try:
            template = Template(template_content)
            return template.render(**variables)
        except Exception as e:
            logger.error(f"Template rendering error: {str(e)}")
            raise TemplateError(f"Template rendering failed: {str(e)}")

    def _sanitize_html(self, html_content: str) -> str:
        """Sanitize HTML content to prevent XSS attacks"""
        try:
            return bleach.clean(
                html_content,
                tags=self.allowed_tags,
                attributes=self.allowed_attributes,
                strip=True
            )
        except Exception as e:
            logger.error(f"HTML sanitization error: {str(e)}")
            return html_content  # Return original if sanitization fails

    def _process_attachments(self, attachments: List[Dict], email_log: EmailLog) -> List[Tuple[str, str, str]]:
        """Process and validate attachments"""
        processed = []
        
        for attachment in attachments:
            try:
                filename = attachment.get('filename', 'attachment')
                content_type = attachment.get('mimetype', 'application/octet-stream')
                content = attachment.get('content', '')
                
                # Decode base64 content
                if content:
                    file_data = base64.b64decode(content)
                    size = len(file_data)
                else:
                    file_data = b''
                    size = 0
                
                # Create attachment record
                EmailAttachment.objects.create(
                    email_log=email_log,
                    filename=filename,
                    content_type=content_type,
                    size=size
                )
                
                processed.append((filename, file_data, content_type))
                
            except Exception as e:
                logger.error(f"Attachment processing error: {str(e)}")
                continue
        
        return processed

    def _send_email(
        self,
        to_email: str,
        subject: str,
        html_content: str = None,
        text_content: str = None,
        from_email: str = None,
        from_name: str = None,
        reply_to: str = None,
        attachments: List[Tuple[str, str, str]] = None,
        headers: Dict = None,
        email_log: EmailLog = None,
        api_key: APIKey = None
    ) -> Tuple[bool, str]:
        """Send the actual email using Django's email backend or custom SMTP"""
        try:
            # Create email message
            from_addr = f'"{from_name}" <{from_email}>' if from_name else from_email
            
            msg = EmailMultiAlternatives(
                subject=subject,
                body=text_content or '',
                from_email=from_addr,
                to=[to_email],
                reply_to=[reply_to] if reply_to else None,
                headers=headers or {}
            )
            
            # Add HTML alternative
            if html_content:
                msg.attach_alternative(html_content, "text/html")
            
            # Add attachments
            if attachments:
                for filename, content, content_type in attachments:
                    msg.attach(filename, content, content_type)
            
            # Check if we should use custom SMTP
            if api_key and api_key.should_use_custom_smtp(from_email):
                smtp_config = api_key.get_smtp_config(from_email)
                
                # Validate SMTP configuration before attempting to send
                if not smtp_config.get('host'):
                    return False, "Custom SMTP host not configured"
                if not smtp_config.get('username'):
                    return False, "Custom SMTP username not configured"
                if not smtp_config.get('password'):
                    return False, "Custom SMTP password not configured"
                
                success, message = self._send_via_custom_smtp(msg, smtp_config)
                if not success:
                    return False, message
            else:
                # Send using default Django email backend
                msg.send()
            
            # Update email log
            if email_log:
                email_log.mark_sent()
            
            logger.info(f"Email sent successfully to {to_email}")
            return True, "Email sent successfully"
            
        except Exception as e:
            logger.error(f"Email sending error: {str(e)}")
            
            # Update email log
            if email_log:
                email_log.mark_failed(str(e))
            
            return False, f"Email sending failed: {str(e)}"
    
    def _send_via_custom_smtp(self, msg, smtp_config):
        """Send email via custom SMTP configuration"""
        server = None
        try:
            import smtplib
            from email.mime.text import MIMEText
            from email.mime.multipart import MIMEMultipart
            from email.mime.base import MIMEBase
            from email import encoders
            import socket
            
            # Validate SMTP configuration
            if not smtp_config.get('host') or not smtp_config.get('username') or not smtp_config.get('password'):
                return False, "Custom SMTP configuration incomplete"
            
            # Create SMTP connection with timeout
            try:
                if smtp_config['use_ssl']:
                    server = smtplib.SMTP_SSL(smtp_config['host'], smtp_config['port'], timeout=30)
                else:
                    server = smtplib.SMTP(smtp_config['host'], smtp_config['port'], timeout=30)
                    if smtp_config['use_tls']:
                        server.starttls()
                
                # Set debug level for better error reporting
                server.set_debuglevel(0)
                
            except (socket.gaierror, socket.timeout, ConnectionRefusedError) as e:
                return False, f"SMTP connection failed: {str(e)}"
            except Exception as e:
                return False, f"SMTP connection error: {str(e)}"
            
            # Authenticate
            try:
                server.login(smtp_config['username'], smtp_config['password'])
            except smtplib.SMTPAuthenticationError as e:
                return False, f"SMTP authentication failed: {str(e)}"
            except Exception as e:
                return False, f"SMTP authentication error: {str(e)}"
            
            # Send email
            try:
                # Convert Django EmailMultiAlternatives to MIME message for smtplib
                mime_msg = msg.message()
                server.send_message(mime_msg)
                logger.info(f"Email sent via custom SMTP ({smtp_config['host']})")
                return True, "Email sent via custom SMTP"
            except smtplib.SMTPRecipientsRefused as e:
                return False, f"SMTP recipients refused: {str(e)}"
            except smtplib.SMTPSenderRefused as e:
                return False, f"SMTP sender refused: {str(e)}"
            except smtplib.SMTPDataError as e:
                return False, f"SMTP data error: {str(e)}"
            except Exception as e:
                return False, f"SMTP send error: {str(e)}"
            
        except Exception as e:
            logger.error(f"Custom SMTP error: {str(e)}")
            return False, f"Custom SMTP error: {str(e)}"
        finally:
            # Ensure connection is properly closed
            if server:
                try:
                    server.quit()
                except Exception as e:
                    logger.warning(f"Error closing SMTP connection: {str(e)}")
                    try:
                        server.close()
                    except Exception:
                        pass

    def validate_email_address(self, email: str) -> bool:
        """Validate email address format"""
        import re
        pattern = r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$'
        return re.match(pattern, email) is not None

    def get_email_stats(self, api_key: APIKey = None, days: int = 30) -> Dict:
        """Get email statistics for an API key"""
        from datetime import timedelta
        
        since = timezone.now() - timedelta(days=days)
        queryset = EmailLog.objects.filter(created_at__gte=since)
        
        if api_key:
            queryset = queryset.filter(api_key=api_key)
        
        stats = {
            'total_emails': queryset.count(),
            'sent_emails': queryset.filter(status='sent').count(),
            'failed_emails': queryset.filter(status='failed').count(),
            'bounced_emails': queryset.filter(status='bounced').count(),
            'queued_emails': queryset.filter(status='queued').count(),
        }
        
        return stats
    
    def _check_quota(self, user) -> Dict:
        """Check if user can send more emails based on their quota"""
        try:
            from accounts.models import Subscription
            
            # Get user's subscription
            subscription = getattr(user, 'subscription', None)
            if not subscription:
                return {
                    'can_send': True,
                    'message': 'No subscription found - using default limits'
                }
            
            # Check if subscription is active
            if subscription.status not in ['active', 'trialing']:
                return {
                    'can_send': False,
                    'message': 'Subscription is not active. Please update your payment method or contact support.'
                }
            
            # Check quota
            if not subscription.can_send_email():
                # Send quota exceeded notification
                from accounts.quota_service import QuotaNotificationService
                QuotaNotificationService._send_quota_exceeded(
                    user, subscription, 
                    subscription.emails_sent_this_period, 
                    subscription.plan.emails_per_month
                )
                
                return {
                    'can_send': False,
                    'message': f'Monthly email quota exceeded ({subscription.emails_sent_this_period}/{subscription.plan.emails_per_month}). Please upgrade your plan or wait for the next billing cycle.'
                }
            
            # Check if approaching quota (80% threshold)
            usage_percentage = (subscription.emails_sent_this_period / subscription.plan.emails_per_month) * 100
            if usage_percentage >= 80:
                # Send quota warning
                from accounts.quota_service import QuotaNotificationService
                QuotaNotificationService._send_quota_warning(
                    user, subscription, 
                    subscription.emails_sent_this_period, 
                    subscription.plan.emails_per_month
                )
            
            return {
                'can_send': True,
                'message': 'Quota check passed'
            }
            
        except Exception as e:
            logger.error(f"Error checking quota for user {user.email}: {str(e)}")
            return {
                'can_send': True,
                'message': 'Quota check failed - allowing email to proceed'
            }
    
    def _increment_usage(self, user):
        """Increment user's email usage counter"""
        try:
            from accounts.models import Subscription
            
            subscription = getattr(user, 'subscription', None)
            if subscription:
                subscription.increment_usage()
                
        except Exception as e:
            logger.error(f"Error incrementing usage for user {user.email}: {str(e)}")
