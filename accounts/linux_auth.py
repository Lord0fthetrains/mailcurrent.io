import subprocess
import spwd
import crypt
from django.contrib.auth.backends import BaseBackend
from django.contrib.auth import get_user_model
from django.conf import settings
import logging

User = get_user_model()

logger = logging.getLogger('accounts')


class LinuxSystemAuthBackend(BaseBackend):
    """
    Authenticate against Linux system users using PAM
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
            
        try:
            # Check if user exists in system
            try:
                spwd.getspnam(username)
            except KeyError:
                # User doesn't exist in system
                return None
            
            # Use PAM to authenticate
            if self._authenticate_with_pam(username, password):
                # Get or create Django user
                email = f'{username}@mailcurrent.io'
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': username.title(),
                        'last_name': 'System User',
                        'is_staff': True,  # Allow admin access
                        'is_superuser': True,  # Full admin access
                    }
                )
                
                if created:
                    logger.info(f"Created Django user for system user: {username}")
                else:
                    # Update existing user to ensure admin access
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()
                
                return user
                
        except Exception as e:
            logger.error(f"Linux auth error for user {username}: {str(e)}")
            return None
    
    def _authenticate_with_pam(self, username, password):
        """Authenticate using PAM"""
        try:
            # Use python-pam if available, otherwise fallback to subprocess
            try:
                import pam
                p = pam.pam()
                return p.authenticate(username, password)
            except ImportError:
                # Fallback to subprocess with pam_auth
                result = subprocess.run(
                    ['pam_auth', username, password],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return result.returncode == 0
        except Exception as e:
            logger.error(f"PAM authentication error: {str(e)}")
            return False
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None


class SimpleLinuxAuthBackend(BaseBackend):
    """
    Simple Linux authentication using crypt (no PAM dependency)
    """
    
    def authenticate(self, request, username=None, password=None, **kwargs):
        if not username or not password:
            return None
            
        try:
            # Get user from system
            try:
                user_info = spwd.getspnam(username)
            except KeyError:
                return None
            
            # Check password using crypt
            if self._check_password(password, user_info.sp_pwd):
                # Get or create Django user
                email = f'{username}@mailcurrent.io'
                user, created = User.objects.get_or_create(
                    email=email,
                    defaults={
                        'first_name': username.title(),
                        'last_name': 'System User',
                        'is_staff': True,
                        'is_superuser': True,
                    }
                )
                
                if created:
                    logger.info(f"Created Django user for system user: {username}")
                else:
                    user.is_staff = True
                    user.is_superuser = True
                    user.save()
                
                return user
                
        except Exception as e:
            logger.error(f"Simple Linux auth error for user {username}: {str(e)}")
            return None
    
    def _check_password(self, password, hashed):
        """Check password against system hash"""
        try:
            return crypt.crypt(password, hashed) == hashed
        except Exception:
            return False
    
    def get_user(self, user_id):
        try:
            return User.objects.get(pk=user_id)
        except User.DoesNotExist:
            return None
