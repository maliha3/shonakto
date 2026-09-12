from django.contrib.auth import get_user_model
from django.contrib.auth.backends import ModelBackend

User = get_user_model()


class EmailBackend(ModelBackend):
    """Allows authenticate(email=..., password=...) since USERNAME_FIELD is email."""

    def authenticate(self, request, email=None, password=None, **kwargs):
        email = email or kwargs.get("username")
        if email is None or password is None:
            return None
        try:
            user = User.objects.get(email__iexact=email)
        except User.DoesNotExist:
            return None
        if user.check_password(password) and self.user_can_authenticate(user):
            return user
        return None
