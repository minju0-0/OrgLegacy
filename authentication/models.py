from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """
    Extends Django's built-in User model for OrgLegacy.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    def __str__(self):
        return self.user.username

