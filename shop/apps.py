from django.apps import AppConfig
import os


class ShopConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "shop"

    def ready(self):
        from django.contrib.auth import get_user_model
        from django.db.utils import OperationalError, ProgrammingError

        User = get_user_model()
        try:
            # Only create if no superuser exists yet
            if not User.objects.filter(is_superuser=True).exists():
                username = os.environ.get("DJANGO_SUPERUSER_USERNAME", "admin")
                email = os.environ.get("DJANGO_SUPERUSER_EMAIL", "admin@example.com")
                password = os.environ.get("DJANGO_SUPERUSER_PASSWORD", "Admin@123")

                print("No superuser found. Creating default superuser...")
                User.objects.create_superuser(username=username, email=email, password=password)
                print("Superuser created successfully.")
        except (OperationalError, ProgrammingError):
            # DB tables might not be ready on first migrate – ignore
            pass
