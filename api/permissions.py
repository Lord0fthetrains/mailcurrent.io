from rest_framework.authentication import BaseAuthentication
from rest_framework.exceptions import AuthenticationFailed
from django.contrib.auth.models import AnonymousUser
from .models import APIKey
import logging

logger = logging.getLogger('api')


class APIKeyAuthentication(BaseAuthentication):
    """
    Custom API key authentication for the email service.
    Expects API key in X-API-Key header.
    """
    
    def authenticate(self, request):
        api_key = request.META.get('HTTP_X_API_KEY')
        
        if not api_key:
            return None
            
        try:
            # Find the API key
            api_key_obj = APIKey.objects.get(key=api_key, is_active=True)
            
            # Update last used timestamp
            api_key_obj.update_last_used()
            
            # Return a tuple of (user, auth) - we'll use the API key as the user
            return (api_key_obj, api_key_obj)
            
        except APIKey.DoesNotExist:
            logger.warning(f"Invalid API key attempted: {api_key[:8]}...")
            raise AuthenticationFailed('Invalid API key')
        except Exception as e:
            logger.error(f"API key authentication error: {str(e)}")
            raise AuthenticationFailed('Authentication failed')

    def authenticate_header(self, request):
        return 'X-API-Key'


from rest_framework.permissions import BasePermission

class APIKeyPermission(BasePermission):
    """
    Custom permission class for API key authentication.
    """
    
    def has_permission(self, request, view):
        # Check if user is authenticated (has valid API key)
        return hasattr(request, 'user') and request.user is not None and not isinstance(request.user, AnonymousUser) and hasattr(request.user, 'key')
    
    def has_object_permission(self, request, view, obj):
        # For object-level permissions, check if the API key owns the object
        if hasattr(obj, 'api_key'):
            return obj.api_key == request.user
        return True
