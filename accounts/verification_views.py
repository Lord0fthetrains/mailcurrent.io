from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from django.shortcuts import render
from django.contrib.auth import get_user_model
from .verification_service import VerificationService
from .serializers import UserProfileSerializer
import logging

logger = logging.getLogger('api')
User = get_user_model()


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_verification_email(request):
    """Send verification email to current user"""
    try:
        user = request.user
        
        if user.is_verified:
            return Response({
                'success': False,
                'message': 'Email is already verified'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        success = VerificationService.send_verification_email(user, request)
        
        if success:
            return Response({
                'success': True,
                'message': 'Verification email sent successfully'
            })
        else:
            return Response({
                'success': False,
                'message': 'Failed to send verification email'
            }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
            
    except Exception as e:
        logger.error(f"Error sending verification email: {e}")
        return Response({
            'success': False,
            'message': 'Error sending verification email'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request, token):
    """Verify email with token"""
    try:
        result = VerificationService.verify_email(token)
        
        if result['success']:
            return Response({
                'success': True,
                'message': result['message']
            })
        else:
            return Response({
                'success': False,
                'message': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error verifying email: {e}")
        return Response({
            'success': False,
            'message': 'Error verifying email'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email_page(request, token):
    """Verify email with token (web page)"""
    try:
        result = VerificationService.verify_email(token)
        
        context = {
            'success': result['success'],
            'message': result['message'],
            'site_name': 'MailCurrent.io'
        }
        
        return render(request, 'emails/verification_result.html', context)
            
    except Exception as e:
        logger.error(f"Error verifying email: {e}")
        context = {
            'success': False,
            'message': 'Error verifying email',
            'site_name': 'MailCurrent.io'
        }
        return render(request, 'emails/verification_result.html', context)


@api_view(['POST'])
@permission_classes([AllowAny])
def request_password_reset(request):
    """Request password reset email"""
    try:
        email = request.data.get('email')
        
        if not email:
            return Response({
                'success': False,
                'message': 'Email address is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        try:
            user = User.objects.get(email=email)
        except User.DoesNotExist:
            # Don't reveal if email exists or not for security
            return Response({
                'success': True,
                'message': 'If the email exists, a password reset link has been sent'
            })
        
        success = VerificationService.send_password_reset_email(user, request)
        
        return Response({
            'success': True,
            'message': 'If the email exists, a password reset link has been sent'
        })
            
    except Exception as e:
        logger.error(f"Error requesting password reset: {e}")
        return Response({
            'success': False,
            'message': 'Error requesting password reset'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password(request, token):
    """Reset password with token"""
    try:
        new_password = request.data.get('new_password')
        
        if not new_password:
            return Response({
                'success': False,
                'message': 'New password is required'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        result = VerificationService.reset_password(token, new_password)
        
        if result['success']:
            return Response({
                'success': True,
                'message': result['message']
            })
        else:
            return Response({
                'success': False,
                'message': result['message']
            }, status=status.HTTP_400_BAD_REQUEST)
            
    except Exception as e:
        logger.error(f"Error resetting password: {e}")
        return Response({
            'success': False,
            'message': 'Error resetting password'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


def reset_password_page(request, token):
    """Reset password page with token"""
    try:
        from .verification_models import PasswordResetToken
        
        token_obj = PasswordResetToken.objects.get(token=token)
        
        if not token_obj.is_valid():
            context = {
                'valid': False,
                'message': 'Invalid or expired password reset token',
                'site_name': 'MailCurrent.io'
            }
        else:
            context = {
                'valid': True,
                'token': token,
                'site_name': 'MailCurrent.io'
            }
        
        return render(request, 'emails/password_reset_form.html', context)
        
    except PasswordResetToken.DoesNotExist:
        context = {
            'valid': False,
            'message': 'Invalid password reset token',
            'site_name': 'MailCurrent.io'
        }
        return render(request, 'emails/password_reset_form.html', context)
    except Exception as e:
        logger.error(f"Error loading password reset page: {e}")
        context = {
            'valid': False,
            'message': 'Error loading password reset page',
            'site_name': 'MailCurrent.io'
        }
        return render(request, 'emails/password_reset_form.html', context)
