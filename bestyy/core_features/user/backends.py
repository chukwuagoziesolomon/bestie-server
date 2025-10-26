from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()

class SocialAuthBackend(ModelBackend):
    """
    Custom authentication backend that prevents admin users from authenticating
    through social login.
    """
    def authenticate(self, request, **kwargs):
        user = super().authenticate(request, **kwargs)
        
        # If user is an admin, don't allow social login
        if user and (user.is_staff or user.is_superuser):
            return None
            
        return user
