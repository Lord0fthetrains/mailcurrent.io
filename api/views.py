from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated, IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.throttling import UserRateThrottle
from django.shortcuts import get_object_or_404
from django.utils import timezone
from django.db.models import Q
import logging

from .models import APIKey, EmailTemplate, EmailLog
from .serializers import (
    EmailTemplateSerializer, EmailLogSerializer, SendTemplateEmailSerializer,
    SendCustomEmailSerializer, APIKeySerializer, CreateAPIKeySerializer,
    EmailStatsSerializer, ValidateAPIKeySerializer
)
from .services import EmailService
from .permissions import APIKeyPermission

logger = logging.getLogger('api')


class SendTemplateEmailView(APIView):
    """Send email using predefined template"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    
    def post(self, request):
        serializer = SendTemplateEmailSerializer(data=request.data)
        if serializer.is_valid():
            try:
                email_service = EmailService()
                success, message = email_service.send_template_email(
                    template_name=serializer.validated_data['template'],
                    to_email=serializer.validated_data['to'],
                    variables=serializer.validated_data.get('variables', {}),
                    api_key=request.user,
                    from_email=serializer.validated_data.get('from_email'),
                    from_name=serializer.validated_data.get('from_name'),
                    reply_to=serializer.validated_data.get('reply_to')
                )
                
                if success:
                    return Response({
                        'success': True,
                        'message': message,
                        'timestamp': timezone.now().isoformat()
                    }, status=status.HTTP_200_OK)
                else:
                    # Check if it's an email verification error
                    if "Email verification required" in message:
                        return Response({
                            'success': False,
                            'error': message
                        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)
                    else:
                        return Response({
                            'success': False,
                            'error': message
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                logger.error(f"Template email error: {str(e)}")
                return Response({
                    'success': False,
                    'error': f'Email sending failed: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


class SendCustomEmailView(APIView):
    """Send custom email with HTML/text content"""
    permission_classes = [IsAuthenticated]
    throttle_classes = [UserRateThrottle]
    
    def post(self, request):
        serializer = SendCustomEmailSerializer(data=request.data)
        if serializer.is_valid():
            try:
                email_service = EmailService()
                success, message = email_service.send_custom_email(
                    to_email=serializer.validated_data['to'],
                    subject=serializer.validated_data['subject'],
                    html_content=serializer.validated_data.get('html'),
                    text_content=serializer.validated_data.get('text'),
                    api_key=request.user,
                    from_email=serializer.validated_data.get('from_email'),
                    from_name=serializer.validated_data.get('from_name'),
                    reply_to=serializer.validated_data.get('reply_to'),
                    attachments=serializer.validated_data.get('attachments'),
                    headers=serializer.validated_data.get('headers')
                )
                
                if success:
                    return Response({
                        'success': True,
                        'message': message,
                        'timestamp': timezone.now().isoformat()
                    }, status=status.HTTP_200_OK)
                else:
                    # Check if it's an email verification error
                    if "Email verification required" in message:
                        return Response({
                            'success': False,
                            'error': message
                        }, status=status.HTTP_405_METHOD_NOT_ALLOWED)
                    else:
                        return Response({
                            'success': False,
                            'error': message
                        }, status=status.HTTP_400_BAD_REQUEST)
                    
            except Exception as e:
                logger.error(f"Custom email error: {str(e)}")
                return Response({
                    'success': False,
                    'error': f'Email sending failed: {str(e)}'
                }, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


class TemplatesListView(APIView):
    """List available email templates"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        templates = EmailTemplate.objects.filter(is_active=True)
        serializer = EmailTemplateSerializer(templates, many=True)
        return Response({
            'success': True,
            'templates': serializer.data
        })


class EmailLogsView(APIView):
    """View email logs (admin only)"""
    permission_classes = [IsAdminUser]
    
    def get(self, request):
        # Get query parameters
        api_key_id = request.query_params.get('api_key_id')
        status_filter = request.query_params.get('status')
        template_name = request.query_params.get('template')
        page = int(request.query_params.get('page', 1))
        page_size = min(int(request.query_params.get('page_size', 50)), 100)
        
        # Build queryset
        queryset = EmailLog.objects.all()
        
        if api_key_id:
            queryset = queryset.filter(api_key_id=api_key_id)
        if status_filter:
            queryset = queryset.filter(status=status_filter)
        if template_name:
            queryset = queryset.filter(template_used__name=template_name)
        
        # Pagination
        start = (page - 1) * page_size
        end = start + page_size
        logs = queryset[start:end]
        
        serializer = EmailLogSerializer(logs, many=True)
        
        return Response({
            'success': True,
            'logs': serializer.data,
            'page': page,
            'page_size': page_size,
            'total': queryset.count()
        })


class ValidateAPIKeyView(APIView):
    """Validate API key"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        api_key = request.user
        serializer = ValidateAPIKeySerializer({
            'valid': True,
            'api_key_name': api_key.name,
            'rate_limit': api_key.rate_limit,
            'is_active': api_key.is_active
        })
        return Response(serializer.data)


class EmailStatsView(APIView):
    """Get email statistics"""
    permission_classes = [IsAuthenticated]
    
    def get(self, request):
        days = int(request.query_params.get('days', 30))
        email_service = EmailService()
        stats = email_service.get_email_stats(api_key=request.user, days=days)
        
        serializer = EmailStatsSerializer(stats)
        return Response({
            'success': True,
            'stats': serializer.data,
            'period_days': days
        })


# Admin views
class APIKeysListView(APIView):
    """List and create API keys for authenticated users"""
    permission_classes = [APIKeyPermission]
    
    def get(self, request):
        # Get active API keys for the authenticated user
        if hasattr(request.user, 'created_by'):
            # API key authentication - get keys for the user who created this key
            user = request.user.created_by
            api_keys = APIKey.objects.filter(created_by=user, is_active=True)
        else:
            # Regular user authentication
            api_keys = APIKey.objects.filter(created_by=request.user, is_active=True)
        
        serializer = APIKeySerializer(api_keys, many=True)
        return Response({
            'success': True,
            'api_keys': serializer.data
        })
    
    def post(self, request):
        # Create API key for the authenticated user
        if hasattr(request.user, 'created_by'):
            # API key authentication - use the user who created this key
            user = request.user.created_by
        else:
            # Regular user authentication
            user = request.user
        
        serializer = CreateAPIKeySerializer(data=request.data)
        if serializer.is_valid():
            api_key = serializer.save(created_by=user)
            response_serializer = APIKeySerializer(api_key)
            return Response({
                'success': True,
                'api_key': response_serializer.data,
                'message': f'API key created successfully. Key: {api_key.key}'
            }, status=status.HTTP_201_CREATED)
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)


class APIKeyDetailView(APIView):
    """Retrieve, update, or delete API key (admin only)"""
    permission_classes = [IsAdminUser]
    
    def get(self, request, pk):
        api_key = get_object_or_404(APIKey, pk=pk)
        serializer = APIKeySerializer(api_key)
        return Response({
            'success': True,
            'api_key': serializer.data
        })
    
    def put(self, request, pk):
        api_key = get_object_or_404(APIKey, pk=pk)
        serializer = APIKeySerializer(api_key, data=request.data, partial=True)
        if serializer.is_valid():
            serializer.save()
            return Response({
                'success': True,
                'api_key': serializer.data,
                'message': 'API key updated successfully'
            })
        else:
            return Response({
                'success': False,
                'errors': serializer.errors
            }, status=status.HTTP_400_BAD_REQUEST)
    
    def delete(self, request, pk):
        api_key = get_object_or_404(APIKey, pk=pk)
        api_key.delete()
        return Response({
            'success': True,
            'message': 'API key deleted successfully'
        }, status=status.HTTP_204_NO_CONTENT)


@api_view(['GET'])
@permission_classes([])
def health_check(request):
    """Health check endpoint"""
    return Response({
        'status': 'healthy',
        'timestamp': timezone.now().isoformat(),
        'version': '1.0.0'
    })