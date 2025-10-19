from django.contrib.auth.backends import ModelBackend
from django.contrib.auth import get_user_model
from django.core.exceptions import ValidationError

User = get_user_model()


class ActiveUserBackend(ModelBackend):
    """
    Custom authentication backend that only allows active users to login
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if username is None or password is None:
            return None
            
        try:
            # Try to get user by email
            user = User.objects.get(email=username)
        except User.DoesNotExist:
            return None
            
        # Check if user is active
        if not user.is_active:
            return None
            
        # Check password
        if user.check_password(password):
            return user
            
        return None
    
    def get_user(self, user_id):
        try:
            user = User.objects.get(pk=user_id)
            # Only return user if they are active
            if user.is_active:
                return user
            return None
        except User.DoesNotExist:
            return None
