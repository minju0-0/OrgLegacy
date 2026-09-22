from django.db import models  # noqa: F401

# The login feature has no models of its own. It authenticates
# against Django's built-in User model and does not need to store
# anything additional.
