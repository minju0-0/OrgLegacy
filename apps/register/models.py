from django.db import models  # noqa: F401

# The register feature has no models of its own — it creates a
# built-in Django User plus a shared accounts.Profile record (see
# apps/accounts/models.py) on successful sign-up.
