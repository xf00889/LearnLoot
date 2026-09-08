import pytest
from django.db import IntegrityError, transaction

from providers.models import Provider


@pytest.mark.django_db
def test_provider_defaults_to_active():
    provider = Provider.objects.create(name="Example Learning", slug="example-learning")

    assert provider.status == Provider.Status.ACTIVE
    assert str(provider) == "Example Learning"


@pytest.mark.django_db
def test_provider_slug_is_unique():
    Provider.objects.create(name="Provider One", slug="shared-provider")

    with pytest.raises(IntegrityError), transaction.atomic():
        Provider.objects.create(name="Provider Two", slug="shared-provider")