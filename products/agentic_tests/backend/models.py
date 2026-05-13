"""Django models for agentic_tests."""

from django.db import models

from posthog.models.utils import UUIDTModel


class AgenticTest(UUIDTModel):
    """
    A single agentic test: an LLM-generated natural-language prompt that an agent
    executes against `target_url` via browserbase. Pass/fail comes from the agent's
    own evaluation of whether the prompt was satisfied.

    The `prompt` itself is owned by the generation step (a teammate's piece);
    this model is the storage and management surface around it.
    """

    class Status(models.TextChoices):
        ACTIVE = "active", "Active"
        PAUSED = "paused", "Paused"
        PROPOSED = "proposed", "Proposed"

    team = models.ForeignKey("posthog.Team", on_delete=models.CASCADE, related_name="agentic_tests")
    created_by = models.ForeignKey("posthog.User", on_delete=models.SET_NULL, null=True, related_name="+")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    name = models.CharField(max_length=255)
    description = models.TextField(blank=True, default="")
    target_url = models.URLField(max_length=2048)
    prompt = models.TextField(help_text="Natural-language instructions for the browser agent.")

    status = models.CharField(max_length=20, choices=Status, default=Status.PROPOSED)

    slack_webhook_url = models.URLField(max_length=2048, blank=True, default="")
    create_issue_on_failure = models.BooleanField(default=True)

    source_replay_id = models.CharField(max_length=255, null=True, blank=True)
    last_run_at = models.DateTimeField(null=True, blank=True)

    class Meta:
        db_table = "posthog_agentictest"
        indexes = [
            models.Index(fields=["team", "status"]),
        ]


class AgenticTestRun(UUIDTModel):
    class Status(models.TextChoices):
        RUNNING = "running", "Running"
        PASSED = "passed", "Passed"
        FAILED = "failed", "Failed"
        TIMEOUT = "timeout", "Timeout"
        ERROR = "error", "Error"

    agentic_test = models.ForeignKey(AgenticTest, on_delete=models.CASCADE, related_name="runs")
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, choices=Status, default=Status.RUNNING)
    duration_ms = models.IntegerField(null=True, blank=True)

    output = models.JSONField(default=dict, blank=True, help_text="Raw response from the browser agent.")
    error_message = models.TextField(blank=True, default="")

    browserbase_session_id = models.CharField(max_length=255, blank=True, default="")
    screenshot_url = models.URLField(max_length=2048, blank=True, default="")
    issue_id = models.CharField(max_length=255, null=True, blank=True)

    class Meta:
        db_table = "posthog_agentictestrun"
        indexes = [
            models.Index(fields=["agentic_test", "-started_at"]),
        ]
