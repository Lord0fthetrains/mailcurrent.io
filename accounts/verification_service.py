from django.conf import settings
from django.utils import timezone
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.urls import reverse
from .verification_models import EmailVerificationToken, PasswordResetToken
from .models import User
import logging

logger = logging.getLogger('api')


class VerificationService:
    """Service for handling email verification and password reset"""
    
    @staticmethod
    def send_verification_email(user, request=None):
        """Send email verification to user"""
        try:
            # Create verification token
            token = EmailVerificationToken.objects.create(
                user=user,
                email=user.email
            )
            
            # Get base URL
            if request:
                base_url = f"{request.scheme}://{request.get_host()}"
            else:
                base_url = getattr(settings, 'BASE_URL', 'http://localhost:3099')
            
            # Create verification URL (user-friendly page)
            verification_url = f"{base_url}/api/v1/accounts/verify-email-page/{token.token}/"
            
            # Prepare email context
            context = {
                'user': user,
                'verification_url': verification_url,
                'site_name': getattr(settings, 'SITE_NAME', 'MailCurrent.io'),
                'expires_in': '24 hours'
            }
            
            # Render email templates
            subject = f"Verify your email address - {context['site_name']}"
            html_message = render_to_string('emails/verification.html', context)
            plain_message = render_to_string('emails/verification.txt', context)
            
            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Verification email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending verification email to {user.email}: {e}")
            return False
    
    @staticmethod
    def verify_email(token_string):
        """Verify email with token"""
        try:
            token = EmailVerificationToken.objects.get(token=token_string)
            
            if not token.is_valid():
                if token.is_expired():
                    return {'success': False, 'message': 'Verification token has expired'}
                elif token.is_used:
                    return {'success': False, 'message': 'Verification token has already been used'}
                else:
                    return {'success': False, 'message': 'Invalid verification token'}
            
            # Mark token as used
            token.is_used = True
            token.save()
            
            # Mark user as verified
            user = token.user
            user.is_verified = True
            user.save(update_fields=['is_verified'])
            
            logger.info(f"Email verified for user {user.email}")
            return {'success': True, 'message': 'Email verified successfully'}
            
        except EmailVerificationToken.DoesNotExist:
            return {'success': False, 'message': 'Invalid verification token'}
        except Exception as e:
            logger.error(f"Error verifying email: {e}")
            return {'success': False, 'message': 'Error verifying email'}
    
    @staticmethod
    def resend_verification_email(user, request=None):
        """Resend verification email to user"""
        try:
            # Invalidate old tokens
            EmailVerificationToken.objects.filter(
                user=user,
                is_used=False
            ).update(is_used=True)
            
            # Send new verification email
            return VerificationService.send_verification_email(user, request)
            
        except Exception as e:
            logger.error(f"Error resending verification email: {e}")
            return False
    
    @staticmethod
    def send_password_reset_email(user, request=None):
        """Send password reset email to user"""
        try:
            # Create password reset token
            token = PasswordResetToken.objects.create(user=user)
            
            # Get base URL
            if request:
                base_url = f"{request.scheme}://{request.get_host()}"
            else:
                base_url = getattr(settings, 'BASE_URL', 'http://localhost:3099')
            
            # Create reset URL (user-friendly page)
            reset_url = f"{base_url}/api/v1/accounts/reset-password-page/{token.token}/"
            
            # Prepare email context
            context = {
                'user': user,
                'reset_url': reset_url,
                'site_name': getattr(settings, 'SITE_NAME', 'MailCurrent.io'),
                'expires_in': '1 hour'
            }
            
            # Render email templates
            subject = f"Reset your password - {context['site_name']}"
            html_message = render_to_string('emails/password_reset.html', context)
            plain_message = render_to_string('emails/password_reset.txt', context)
            
            # Send email
            send_mail(
                subject=subject,
                message=plain_message,
                from_email=settings.DEFAULT_FROM_EMAIL,
                recipient_list=[user.email],
                html_message=html_message,
                fail_silently=False
            )
            
            logger.info(f"Password reset email sent to {user.email}")
            return True
            
        except Exception as e:
            logger.error(f"Error sending password reset email to {user.email}: {e}")
            return False
    
    @staticmethod
    def reset_password(token_string, new_password):
        """Reset password with token"""
        try:
            token = PasswordResetToken.objects.get(token=token_string)
            
            if not token.is_valid():
                if token.is_expired():
                    return {'success': False, 'message': 'Password reset token has expired'}
                elif token.is_used:
                    return {'success': False, 'message': 'Password reset token has already been used'}
                else:
                    return {'success': False, 'message': 'Invalid password reset token'}
            
            # Mark token as used
            token.is_used = True
            token.save()
            
            # Update user password
            user = token.user
            user.set_password(new_password)
            user.save(update_fields=['password'])
            
            logger.info(f"Password reset for user {user.email}")
            return {'success': True, 'message': 'Password reset successfully'}
            
        except PasswordResetToken.DoesNotExist:
            return {'success': False, 'message': 'Invalid password reset token'}
        except Exception as e:
            logger.error(f"Error resetting password: {e}")
            return {'success': False, 'message': 'Error resetting password'}
