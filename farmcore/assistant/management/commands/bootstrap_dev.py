from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

from farms.models import Farm, FarmMembership, FarmRole


class Command(BaseCommand):
    help = "Create dev user, demo farm, and owner membership if database is empty."

    def add_arguments(self, parser):
        parser.add_argument(
            "--if-empty",
            action="store_true",
            help="Only bootstrap when no farms exist.",
        )

    def handle(self, *args, **options):
        if options["if_empty"] and Farm.objects.exists():
            self.stdout.write("Bootstrap skipped — farms already exist.")
            return

        user_model = get_user_model()
        user, created = user_model.objects.get_or_create(
            username="owner",
            defaults={"email": "owner@example.com"},
        )
        if created:
            user.set_password("owner")
            user.save()
            self.stdout.write(self.style.SUCCESS("Created user owner / owner"))

        farm, _ = Farm.objects.get_or_create(
            slug="demo-farm",
            defaults={"name": "Demo Farm"},
        )
        FarmMembership.objects.get_or_create(
            farm=farm,
            user=user,
            defaults={"role": FarmRole.OWNER},
        )
        self.stdout.write(self.style.SUCCESS(f"Demo farm ready: {farm.slug} ({farm.id})"))
