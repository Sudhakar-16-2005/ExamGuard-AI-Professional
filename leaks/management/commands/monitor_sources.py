from django.core.management.base import BaseCommand
from django.utils import timezone

from leaks.models import Source
from leaks.services.web_monitor import monitor_web_source


class Command(BaseCommand):
    help = "Fetch configured public website/RSS/search-feed sources once. Run periodically with a scheduler."

    def add_arguments(self, parser):
        parser.add_argument(
            "--source", type=int, help="Monitor only one Source primary key"
        )

    def handle(self, *args, **options):
        queryset = Source.objects.filter(
            is_enabled=True,
            source_type__in=[
                Source.Type.WEBSITE,
                Source.Type.RSS,
                Source.Type.SEARCH_FEED,
            ],
        )
        if options["source"]:
            queryset = queryset.filter(pk=options["source"])
        for source in queryset:
            try:
                count = monitor_web_source(source)
                source.last_checked_at = timezone.now()
                source.last_error = ""
                source.save(update_fields=("last_checked_at", "last_error"))
                self.stdout.write(
                    self.style.SUCCESS(f"{source.name}: captured {count} item(s)")
                )
            except Exception as exc:  # noqa: BLE001 - connector failures are isolated per source
                source.last_checked_at = timezone.now()
                source.last_error = str(exc)[:2000]
                source.save(update_fields=("last_checked_at", "last_error"))
                self.stderr.write(f"{source.name}: {exc}")
