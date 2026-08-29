import uuid

from django.conf import settings
from django.db import models


class FarmRole(models.TextChoices):
    OWNER = "owner", "Owner"
    WORKER = "worker", "Worker"


class Farm(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    name = models.CharField(max_length=200)
    slug = models.SlugField(max_length=80, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["name"]

    def __str__(self) -> str:
        return self.name


class FarmMembership(models.Model):
    id = models.UUIDField(primary_key=True, default=uuid.uuid4, editable=False)
    farm = models.ForeignKey(Farm, on_delete=models.CASCADE, related_name="memberships")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="farm_memberships",
    )
    role = models.CharField(max_length=16, choices=FarmRole.choices)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = [("farm", "user")]
        ordering = ["farm__name", "user__username"]

    def __str__(self) -> str:
        return f"{self.user} @ {self.farm} ({self.role})"
