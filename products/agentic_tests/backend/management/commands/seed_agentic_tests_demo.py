"""
Seed demo agentic tests + run history for the hackathon demo.

Usage:
    python manage.py seed_agentic_tests_demo --team-id 2
    python manage.py seed_agentic_tests_demo --team-id 2 --wipe

Creates 4 hedgebox-themed tests (proposed and active) with run history so the
list view and a detail page are demo-ready.
"""

import random
from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from products.agentic_tests.backend.models import AgenticTest, AgenticTestRun

DEMO_TESTS = [
    {
        "name": "Hedgebox upload flow",
        "target_url": "https://hedgebox-dummy.posthog.com",
        "prompt": (
            "Sign in with test@hedgebox.dev / Hackathon123!, click the Upload button, "
            "drag a file onto the dropzone, and verify the uploaded file appears in the "
            "Recent uploads list."
        ),
        "status": "active",
        "failure_rate": 0.05,
    },
    {
        "name": "Hedgebox sharing",
        "target_url": "https://hedgebox-dummy.posthog.com/files",
        "prompt": (
            "Open the most recent file, click Share, copy the link, and verify the "
            "share dialog closes with a confirmation toast."
        ),
        "status": "active",
        "failure_rate": 0.1,
    },
    {
        "name": "Hedgebox pricing page (proposed)",
        "target_url": "https://hedgebox-dummy.posthog.com/pricing",
        "prompt": (
            "Confirm the Pro plan price is visible above the fold and that the "
            "'Upgrade' button is reachable without scrolling."
        ),
        "status": "proposed",
        "failure_rate": 0.0,
    },
    {
        "name": "Broken: checkout flow (demo)",
        "target_url": "https://hedgebox-dummy.posthog.com/upgrade",
        "prompt": (
            "Click Upgrade to Pro, fill in the credit card 4242 4242 4242 4242 with any "
            "future expiry, click Pay, and verify the success page appears."
        ),
        "status": "active",
        "failure_rate": 1.0,
    },
]

RUN_HISTORY_COUNT = 24
RUN_INTERVAL_MINUTES = 15


class Command(BaseCommand):
    help = "Seed demo agentic tests with realistic run history."

    def add_arguments(self, parser) -> None:
        parser.add_argument("--team-id", type=int, required=True)
        parser.add_argument("--wipe", action="store_true", help="Delete existing agentic tests for this team first.")

    def handle(self, *args, **options) -> None:
        team_id: int = options["team_id"]
        if options["wipe"]:
            count, _ = AgenticTest.objects.filter(team_id=team_id).delete()
            self.stdout.write(self.style.WARNING(f"Deleted {count} existing agentic tests"))

        now = timezone.now()
        for fixture in DEMO_TESTS:
            test = AgenticTest.objects.create(
                team_id=team_id,
                name=fixture["name"],
                target_url=fixture["target_url"],
                prompt=fixture["prompt"],
                status=fixture["status"],
                last_run_at=(now - timedelta(minutes=random.randint(1, 30)) if fixture["status"] == "active" else None),
            )
            if fixture["status"] == "active":
                self._seed_run_history(test, fixture["failure_rate"], now)
            self.stdout.write(self.style.SUCCESS(f"  ✔ {fixture['name']} ({fixture['status']})"))

        self.stdout.write(self.style.SUCCESS(f"\nSeeded {len(DEMO_TESTS)} tests for team {team_id}"))

    def _seed_run_history(self, test: AgenticTest, failure_rate: float, now) -> None:
        for idx in range(RUN_HISTORY_COUNT):
            started = now - timedelta(minutes=RUN_INTERVAL_MINUTES * (idx + 1))
            failed = random.random() < failure_rate
            status_value = AgenticTestRun.Status.FAILED if failed else AgenticTestRun.Status.PASSED
            duration = random.randint(2200, 5500) if not failed else random.randint(8000, 12000)
            AgenticTestRun.objects.create(
                agentic_test=test,
                started_at=started,
                finished_at=started + timedelta(milliseconds=duration),
                status=status_value,
                duration_ms=duration,
                output={"evaluation": "Prompt satisfied." if not failed else "Agent could not complete the prompt."},
                error_message=(
                    "Agent could not find the [data-attr=upgrade-pay] selector after 3 attempts." if failed else ""
                ),
                browserbase_session_id=f"bb-{test.id.hex[:8]}-{idx}",
            )
