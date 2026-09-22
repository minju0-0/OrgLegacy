from django.db import models  # noqa: F401

# This app intentionally has no models of its own — it reads and
# writes the built-in User model. Deleting an account cascades onto
# the shared accounts.Profile automatically via Profile.user's
# on_delete=CASCADE, so this app doesn't need to know Profile exists.
