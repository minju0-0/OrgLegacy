from django.db import models
from django.contrib.auth.models import User


class Profile(models.Model):
    """
    Shared, cross-cutting extension of Django's built-in User model.

    This lives in its own small `accounts` app (not inside login,
    register, profile, or settings) because all four of those features
    need to read or write it. Vertical slicing says a feature should
    own the code for its own capability and avoid depending directly
    on another feature's internals — so instead of Profile living
    inside (for example) the register app and profile/settings
    reaching into it, it lives in a small shared area that any feature
    may depend on.
    """

    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')
    bio = models.TextField(
        blank=True,
        default='',
        max_length=300,
        help_text="A short bio shown on your profile page.",
    )
    avatar_url = models.URLField(
        blank=True,
        default='',
        help_text="Link to a profile photo (optional).",
    )

    def __str__(self):
        return self.user.username
