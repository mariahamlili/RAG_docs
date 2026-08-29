import uuid

from django.contrib.auth.models import AbstractBaseUser


def user_uuid(user: AbstractBaseUser) -> uuid.UUID:
    """Stable UUID for audit fields when using Django's integer user PK."""
    return uuid.uuid5(uuid.NAMESPACE_URL, f"farmcore-user:{user.pk}")
