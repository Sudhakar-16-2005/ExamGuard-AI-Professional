
import os

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = "Create or update a Django superuser using temporary environment variables."

    def handle(self, *args, **options):
        username = os.environ.get("ADMIN_USERNAME")
        email = os.environ.get("ADMIN_EMAIL", "")
        password = os.environ.get("ADMIN_PASSWORD")

        if not username or not password:
            raise CommandError(
                "Set ADMIN_USERNAME and ADMIN_PASSWORD before running this command."
            )

        User = get_user_model()
        user, created = User.objects.get_or_create(
            **{User.USERNAME_FIELD: username},
            defaults={"email": email} if any(
                field.name == "email" for field in User._meta.fields
            ) else {},
        )

        user.is_staff = True
        user.is_superuser = True
        user.set_password(password)
        user.save()

        self.stdout.write(
            self.style.SUCCESS(
                f"Superuser {'created' if created else 'updated'} successfully."
            )
        )
