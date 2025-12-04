from django.contrib.auth.backends import BaseBackend
from .models import Agent

class EmailBackend(BaseBackend):
    def authenticate(self, request, email=None, password=None, **kwargs):
        try:
            user = Agent.objects.get(email=email)
            if user.check_password(password):
                return user
        except Agent.DoesNotExist:
            return None

    def get_user(self, user_id):
        try:
            return Agent.objects.get(pk=user_id)
        except Agent.DoesNotExist:
            return None
