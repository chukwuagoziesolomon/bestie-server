import pytest
from django.urls import reverse
from django.utils import timezone


@pytest.mark.django_db
def test_whatsapp_verify_endpoint_creates_user(client):
    # Create a PendingUser record directly
    from bestyy.core_features.user.models import PendingUser, User

    p = PendingUser.objects.create(
        email="vendor+test@example.com",
        password="password123",
        first_name="Vera",
        last_name="Vendor",
        phone="+2348012345678".replace('+', ''),
        user_type="vendor",
        verification_code="123456",
        profile_data={}
    )
    # Ensure not expired
    p.expires_at = timezone.now() + timezone.timedelta(hours=1)
    p.save()

    url = reverse('whatsapp-verify-signup')
    resp = client.post(url, data={"phone": "+2348012345678", "code": "123456"}, content_type='application/json')

    assert resp.status_code == 200
    data = resp.json()
    assert data.get('ok') is True
    assert data.get('role') == 'vendor'

    # User should exist now
    assert User.objects.filter(email="vendor+test@example.com").exists()





















