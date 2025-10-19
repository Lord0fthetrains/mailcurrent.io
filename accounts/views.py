from rest_framework import generics, status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.response import Response
from rest_framework.authtoken.models import Token
from django.contrib.auth import login, logout
from django.db import transaction
from django.utils import timezone
from django.db import models
from django.shortcuts import render
from api.models import EmailLog
from .models import User, Plan, Subscription, UsageLog, BillingHistory
from .serializers import (
    UserRegistrationSerializer, UserLoginSerializer, UserProfileSerializer,
    PlanSerializer, SubscriptionSerializer, UsageLogSerializer, BillingHistorySerializer,
    ChangePasswordSerializer, UpdateProfileSerializer
)
from api.serializers import APIKeySerializer
from .verification_service import VerificationService
from api.models import APIKey
import logging

logger = logging.getLogger('api')


class UserRegistrationView(generics.CreateAPIView):
    """User registration endpoint"""
    queryset = User.objects.all()
    serializer_class = UserRegistrationSerializer
    permission_classes = [AllowAny]
    
    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        with transaction.atomic():
            user = serializer.save()
            
            # Create a free trial subscription
            free_plan = Plan.objects.filter(name='Free Trial').first()
            if free_plan:
                Subscription.objects.create(
                    user=user,
                    plan=free_plan,
                    status='trialing',
                    current_period_start=timezone.now(),
                    current_period_end=timezone.now() + timezone.timedelta(days=14),  # 14-day trial
                    trial_end=timezone.now() + timezone.timedelta(days=14)
                )
            
            # Create a default API key
            APIKey.objects.create(
                name=f"{user.email} - Default Key",
                created_by=user,
                rate_limit=100  # Lower limit for trial users
            )
        
        # Send verification email
        VerificationService.send_verification_email(user, request)
        
        # Create auth token
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'success': True,
            'message': 'User registered successfully. Please check your email to verify your account.',
            'token': token.key,
            'user': UserProfileSerializer(user).data
        }, status=status.HTTP_201_CREATED)


class UserLoginView(generics.GenericAPIView):
    """User login endpoint"""
    serializer_class = UserLoginSerializer
    permission_classes = [AllowAny]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = serializer.validated_data['user']
        login(request, user)
        
        # Create or get auth token
        token, created = Token.objects.get_or_create(user=user)
        
        return Response({
            'success': True,
            'message': 'Login successful',
            'token': token.key,
            'user': UserProfileSerializer(user).data
        })


class UserLogoutView(generics.GenericAPIView):
    """User logout endpoint"""
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        try:
            # Delete the user's token
            request.user.auth_token.delete()
            logout(request)
            return Response({
                'success': True,
                'message': 'Logout successful'
            })
        except Exception as e:
            return Response({
                'success': False,
                'message': 'Logout failed'
            }, status=status.HTTP_400_BAD_REQUEST)


class UserProfileView(generics.RetrieveUpdateAPIView):
    """User profile management"""
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        return self.request.user


class ChangePasswordView(generics.GenericAPIView):
    """Change user password"""
    serializer_class = ChangePasswordSerializer
    permission_classes = [IsAuthenticated]
    
    def post(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data, context={'request': request})
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'success': True,
            'message': 'Password changed successfully'
        })


class PlanListView(generics.ListAPIView):
    """List available pricing plans"""
    queryset = Plan.objects.filter(is_active=True)
    serializer_class = PlanSerializer
    permission_classes = [AllowAny]


class SubscriptionView(generics.RetrieveUpdateAPIView):
    """User subscription management"""
    serializer_class = SubscriptionSerializer
    permission_classes = [IsAuthenticated]
    
    def get_object(self):
        subscription, created = Subscription.objects.get_or_create(
            user=self.request.user,
            defaults={
                'plan': Plan.objects.filter(name='Free Trial').first(),
                'status': 'trialing',
                'current_period_start': timezone.now(),
                'current_period_end': timezone.now() + timezone.timedelta(days=14),
                'trial_end': timezone.now() + timezone.timedelta(days=14)
            }
        )
        return subscription


class UsageLogView(generics.ListAPIView):
    """User usage logs"""
    serializer_class = UsageLogSerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return UsageLog.objects.filter(user=self.request.user)


class BillingHistoryView(generics.ListAPIView):
    """User billing history"""
    serializer_class = BillingHistorySerializer
    permission_classes = [IsAuthenticated]
    
    def get_queryset(self):
        return BillingHistory.objects.filter(user=self.request.user)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def user_dashboard(request):
    """User dashboard data"""
    user = request.user
    
    # Get subscription info
    subscription = getattr(user, 'subscription', None)
    
    # Get active API keys only
    api_keys = APIKey.objects.filter(created_by=user, is_active=True)
    
    # Get usage stats - count actual sent emails from EmailLog
    emails_this_month = EmailLog.objects.filter(
        api_key__created_by=user,
        sent_at__gte=timezone.now().replace(day=1),
        status='sent'
    ).count()
    
    # Get cost from UsageLog (if any)
    usage_this_month = UsageLog.objects.filter(
        user=user,
        timestamp__gte=timezone.now().replace(day=1)
    ).aggregate(
        total_cost=models.Sum('cost')
    )
    
    # Get recent activity with pagination support
    page = int(request.GET.get('page', 1))
    per_page = int(request.GET.get('per_page', 10))
    offset = (page - 1) * per_page
    
    recent_emails = EmailLog.objects.filter(api_key__created_by=user).order_by('-created_at')[offset:offset + per_page]
    total_emails = EmailLog.objects.filter(api_key__created_by=user).count()
    
    return Response({
        'user': UserProfileSerializer(user).data,
        'subscription': SubscriptionSerializer(subscription).data if subscription else None,
        'api_keys': [
            {
                'id': key.id,
                'name': key.name,
                'key': key.key[:8] + '...' if key.key else None,
                'is_active': key.is_active,
                'rate_limit': key.rate_limit,
                'created_at': key.created_at,
                'last_used_at': key.last_used_at
            }
            for key in api_keys
        ],
        'usage_stats': {
            'emails_this_month': emails_this_month,
            'cost_this_month': float(usage_this_month['total_cost'] or 0),
            'emails_remaining': max(0, (subscription.plan.emails_per_month - emails_this_month) if subscription else 0)
        },
        'recent_emails': [
            {
                'id': email.id,
                'to_email': email.to,
                'subject': email.subject,
                'status': email.status,
                'sent_at': email.sent_at,
                'created_at': email.created_at,
                'html_content': '',  # EmailLog doesn't store HTML content, only length
                'template_used': email.template_used.name if email.template_used else None,
                'error_message': email.error_message
            }
            for email in recent_emails
        ],
        'pagination': {
            'current_page': page,
            'per_page': per_page,
            'total_emails': total_emails,
            'total_pages': (total_emails + per_page - 1) // per_page,
            'has_next': offset + per_page < total_emails,
            'has_previous': page > 1
        }
    })


@api_view(['GET', 'POST'])
@permission_classes([IsAuthenticated])
def api_keys(request):
    """List or create API keys"""
    if request.method == 'GET':
        # List user's active API keys only
        api_keys = APIKey.objects.filter(created_by=request.user, is_active=True).order_by('-created_at')
        serializer = APIKeySerializer(api_keys, many=True, context={'request': request})
        return Response({
            'api_keys': serializer.data
        })
    else:
        # Create new API key
        name = request.data.get('name', f"{request.user.email} - API Key")
        
        api_key = APIKey.objects.create(
            name=name,
            created_by=request.user,
            rate_limit=100  # Default rate limit
        )
        
        serializer = APIKeySerializer(api_key, context={'request': request})
        return Response({
            'success': True,
            'message': 'API key created successfully',
            'api_key': serializer.data
        }, status=status.HTTP_201_CREATED)


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def create_api_key(request):
    """Create a new API key for the user"""
    name = request.data.get('name')
    if not name:
        return Response({
            'success': False,
            'message': 'API key name is required'
        }, status=status.HTTP_400_BAD_REQUEST)
    
    # Check API key limit
    subscription = getattr(request.user, 'subscription', None)
    if subscription:
        current_keys = APIKey.objects.filter(created_by=request.user).count()
        if current_keys >= subscription.plan.api_keys_limit:
            return Response({
                'success': False,
                'message': f'API key limit reached ({subscription.plan.api_keys_limit})'
            }, status=status.HTTP_400_BAD_REQUEST)
    
    # Create API key
    api_key = APIKey.objects.create(
        name=name,
        created_by=request.user,
        rate_limit=subscription.plan.emails_per_month // 30 if subscription else 100  # Daily rate limit
    )
    
    return Response({
        'success': True,
        'message': 'API key created successfully',
        'api_key': {
            'id': api_key.id,
            'name': api_key.name,
            'key': api_key.key,
            'created_at': api_key.created_at
        }
    }, status=status.HTTP_201_CREATED)


@api_view(['PUT'])
@permission_classes([IsAuthenticated])
def update_api_key(request, key_id):
    """Update an API key"""
    try:
        # Get the user who owns this API key
        if hasattr(request.user, 'created_by'):
            # API key authentication - get the user who created this key
            user = request.user.created_by
        else:
            # Regular user authentication
            user = request.user
        
        api_key = APIKey.objects.get(id=key_id, created_by=user)
        
        # Update fields
        api_key.name = request.data.get('name', api_key.name)
        api_key.rate_limit = request.data.get('rate_limit', api_key.rate_limit)
        api_key.default_from_email = request.data.get('default_from_email') or None
        api_key.default_from_name = request.data.get('default_from_name') or None
        api_key.allowed_domains = request.data.get('allowed_domains', api_key.allowed_domains)
        api_key.is_active = request.data.get('is_active', api_key.is_active)
        
        # Update SMTP configuration
        if 'custom_smtp_host' in request.data:
            api_key.custom_smtp_host = request.data.get('custom_smtp_host') or None
        if 'custom_smtp_port' in request.data:
            api_key.custom_smtp_port = request.data.get('custom_smtp_port', 587)
        if 'custom_smtp_username' in request.data:
            api_key.custom_smtp_username = request.data.get('custom_smtp_username') or None
        if 'custom_smtp_password' in request.data:
            password = request.data.get('custom_smtp_password')
            if password:
                api_key.set_smtp_password(password)
            else:
                api_key.custom_smtp_password = None
        if 'custom_smtp_use_tls' in request.data:
            api_key.custom_smtp_use_tls = request.data.get('custom_smtp_use_tls', True)
        if 'custom_smtp_use_ssl' in request.data:
            api_key.custom_smtp_use_ssl = request.data.get('custom_smtp_use_ssl', False)
        
        api_key.save()
        
        serializer = APIKeySerializer(api_key, context={'request': request})
        return Response({
            'success': True,
            'message': 'API key updated successfully',
            'api_key': serializer.data
        })
    except APIKey.DoesNotExist:
        return Response({
            'success': False,
            'message': 'API key not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_api_key(request, key_id):
    """Soft delete an API key by marking it as inactive and clearing sensitive data"""
    try:
        api_key = APIKey.objects.get(id=key_id, created_by=request.user)
        
        # Soft delete: mark as inactive and clear sensitive data
        api_key.is_active = False
        api_key.custom_smtp_host = None
        api_key.custom_smtp_port = 587
        api_key.custom_smtp_username = None
        api_key.custom_smtp_password = None
        api_key.custom_smtp_use_tls = True
        api_key.custom_smtp_use_ssl = False
        api_key.allowed_domains = []
        api_key.save()
        
        return Response({
            'success': True,
            'message': 'API key deactivated successfully'
        })
    except APIKey.DoesNotExist:
        return Response({
            'success': False,
            'message': 'API key not found'
        }, status=status.HTTP_404_NOT_FOUND)


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email(request, token):
    """Verify user email with token"""
    try:
        from .verification_models import EmailVerificationToken
        
        # Get the verification token
        verification_token = EmailVerificationToken.objects.get(token=token)
        
        # Check if token is expired
        if verification_token.is_expired():
            return Response({
                'success': False,
                'message': 'Verification token has expired. Please request a new one.'
            }, status=status.HTTP_400_BAD_REQUEST)
        
        # Verify the user
        user = verification_token.user
        user.is_verified = True
        user.save()
        
        # Delete the used token
        verification_token.delete()
        
        return Response({
            'success': True,
            'message': 'Email verified successfully! You can now use all features of the service.'
        })
        
    except EmailVerificationToken.DoesNotExist:
        return Response({
            'success': False,
            'message': 'Invalid verification token'
        }, status=status.HTTP_400_BAD_REQUEST)
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        return Response({
            'success': False,
            'message': 'An error occurred during verification'
        }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


@api_view(['GET'])
@permission_classes([AllowAny])
def verify_email_page(request, token):
    """User-friendly email verification page"""
    try:
        from .verification_models import EmailVerificationToken
        
        # Get the verification token
        verification_token = EmailVerificationToken.objects.get(token=token)
        
        # Check if token is expired
        if verification_token.is_expired():
            return render(request, 'auth/verification_expired.html', {
                'message': 'Verification token has expired. Please request a new one.'
            })
        
        # Verify the user
        user = verification_token.user
        user.is_verified = True
        user.save()
        
        # Delete the used token
        verification_token.delete()
        
        return render(request, 'auth/verification_success.html', {
            'user': user,
            'message': 'Email verified successfully! You can now use all features of the service.'
        })
        
    except EmailVerificationToken.DoesNotExist:
        return render(request, 'auth/verification_invalid.html', {
            'message': 'Invalid verification token'
        })
    except Exception as e:
        logger.error(f"Email verification error: {str(e)}")
        return render(request, 'auth/verification_error.html', {
            'message': 'An error occurred during verification'
        })