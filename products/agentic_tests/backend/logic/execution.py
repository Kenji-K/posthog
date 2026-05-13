"""
Execution path for an agentic test run.

For now this is a deterministic mock — the browserbase integration is a teammate's
piece and will replace `_run_mock`. The expected shape from any real runner is:

    { passed: bool, output: dict, error?: str, browserbase_session_id?: str, screenshot_url?: str }

Slack alerting fires on failure if `slack_webhook_url` is set on the test.
"""

import json
import time
from typing import Any

from django.utils import timezone

import requests
import structlog

from posthog.ph_client import ph_scoped_capture

from products.agentic_tests.backend.models import AgenticTest, AgenticTestRun

logger = structlog.get_logger(__name__)


def execute_agentic_test(test: AgenticTest) -> AgenticTestRun:
    """Run a single execution of an agentic test and persist the result."""
    run = AgenticTestRun.objects.create(
        agentic_test=test,
        status=AgenticTestRun.Status.RUNNING,
    )
    start = time.monotonic()

    try:
        result = _run_mock(test)
    except Exception as exc:  # noqa: BLE001 — surface anything as a failed run
        logger.exception("agentic_test_runner_error", test_id=str(test.id), error=str(exc))
        result = {"passed": False, "output": {}, "error": f"Runner error: {exc}"}

    duration_ms = int((time.monotonic() - start) * 1000)
    run.finished_at = timezone.now()
    run.duration_ms = duration_ms
    run.output = result.get("output", {})
    run.browserbase_session_id = result.get("browserbase_session_id", "")
    run.screenshot_url = result.get("screenshot_url", "")
    run.status = AgenticTestRun.Status.PASSED if result["passed"] else AgenticTestRun.Status.FAILED
    if not result["passed"]:
        run.error_message = (result.get("error") or "")[:5000]
        _emit_failure_event(test=test, run=run)
        if test.slack_webhook_url:
            _post_slack_alert(test=test, run=run)
    run.save()

    test.last_run_at = run.started_at
    test.save(update_fields=["last_run_at", "updated_at"])
    return run


def _run_mock(test: AgenticTest) -> dict[str, Any]:
    """Deterministic mock so the demo works without a real browser runner."""
    is_broken = "broken" in (test.name or "").lower() or "fail" in (test.prompt or "").lower()
    if is_broken:
        return {
            "passed": False,
            "output": {"steps_attempted": 3, "last_action": "click submit button"},
            "error": "Agent could not find the [data-attr=submit] selector after 3 attempts (mock failure).",
            "browserbase_session_id": "mock-session-broken",
        }
    return {
        "passed": True,
        "output": {"steps_completed": 5, "evaluation": "Prompt satisfied."},
        "browserbase_session_id": "mock-session-ok",
    }


def _emit_failure_event(*, test: AgenticTest, run: AgenticTestRun) -> None:
    """Emit a `$agentic_test_result` event so error_tracking + logs can fingerprint it."""
    try:
        with ph_scoped_capture() as capture:
            capture(
                distinct_id=f"agentic_test:{test.id}",
                event="$agentic_test_result",
                properties={
                    "$exception_type": "AgenticTestFailure",
                    "$exception_message": run.error_message or "Agentic test failed",
                    "agentic_test_id": str(test.id),
                    "agentic_test_run_id": str(run.id),
                    "agentic_test_name": test.name,
                    "browserbase_session_id": run.browserbase_session_id,
                    "team_id": test.team_id,
                },
            )
    except Exception as exc:  # noqa: BLE001
        logger.warning("agentic_test_event_emit_failed", error=str(exc))


def _post_slack_alert(*, test: AgenticTest, run: AgenticTestRun) -> None:
    """POST a simple block to the configured Slack incoming webhook."""
    payload = {
        "blocks": [
            {
                "type": "header",
                "text": {"type": "plain_text", "text": f"🚨 Agentic test failed: {test.name}"},
            },
            {
                "type": "section",
                "fields": [
                    {"type": "mrkdwn", "text": f"*URL*\n{test.target_url}"},
                    {"type": "mrkdwn", "text": f"*Run ID*\n`{run.id}`"},
                ],
            },
            {
                "type": "section",
                "text": {"type": "mrkdwn", "text": f"```{run.error_message[:500]}```"},
            },
            {
                "type": "context",
                "elements": [
                    {
                        "type": "mrkdwn",
                        "text": "This test was created automatically. A PostHog Code task will attempt a fix.",
                    }
                ],
            },
        ],
    }
    try:
        requests.post(test.slack_webhook_url, data=json.dumps(payload), timeout=5)
    except Exception as exc:  # noqa: BLE001 — never fail the run on alert errors
        logger.warning("agentic_test_slack_post_failed", error=str(exc))
