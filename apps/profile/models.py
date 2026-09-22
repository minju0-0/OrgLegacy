from django.db import models  # noqa: F401

# This app intentionally has no models of its own — it reads and
# writes the User model and the shared Profile model that lives in
# apps/accounts/models.py.
