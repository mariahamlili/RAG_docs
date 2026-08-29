import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from farms.models import Farm, FarmMembership, FarmRole


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.fixture
def owner_principal(db):
    user_model = get_user_model()
    user = user_model.objects.create_user(username="testowner", password="test")
    farm = Farm.objects.create(name="Test Farm", slug="test-farm")
    FarmMembership.objects.create(farm=farm, user=user, role=FarmRole.OWNER)
    return user, farm
