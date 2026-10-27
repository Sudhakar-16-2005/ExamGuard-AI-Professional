from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError
from django.test import SimpleTestCase, TestCase


class PasswordPolicyTests(SimpleTestCase):
    def test_password_shorter_than_eight_is_rejected(self):
        with self.assertRaises(ValidationError):
            validate_password("Ab1!xyz")

    def test_eight_character_password_is_accepted(self):
        validate_password("Ax7!qP2z")


class AdminAccessTests(TestCase):
    def test_admin_requires_authentication(self):
        response = self.client.get("/admin/")
        self.assertEqual(response.status_code, 302)

    def test_staff_user_can_open_admin(self):
        user = get_user_model().objects.create_user(
            "analyst", password="Ax7!qP2z", is_staff=True
        )
        self.client.force_login(user)
        self.assertEqual(self.client.get("/admin/").status_code, 200)
