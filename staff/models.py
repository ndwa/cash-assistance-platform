from app_ccf.encoder import ApplicationEncoder
from app_ccf.models import Application
from datetime import datetime, timezone
from django.db import models
from django.contrib.postgres.fields import JSONField


class AdminAction(models.Model):
    """
    Represents and action taken by an administrator on an Application.

    Captures the application details before and after the change.
    """

    class AdminActionType(models.TextChoices):
        MANUAL_EDIT = 'manual_edit'

    application = models.ForeignKey(Application, on_delete=models.CASCADE)
    user = models.CharField(max_length=20)
    date = models.DateTimeField(auto_now_add=True)
    action_type = models.CharField(
        max_length=40,
        choices=AdminActionType.choices
    )
    initial_app_json = JSONField(encoder=ApplicationEncoder)
    final_app_json = JSONField(encoder=ApplicationEncoder)

    @property
    def initial_app(self):
        """The Application before the action."""
        return Application(**self.initial_app_json)

    @property
    def final_app(self):
        """The Application after the action."""
        return Application(**self.final_app_json)

    @property
    def changed_fields(self):
        """The model fields that changed during the transaction.

        Returns:
            A list of 3-tuples of:
                - The field name
                - The initial value
                - The final value
        """
        changes = []
        for field in self.initial_app_json:
            initial_value = getattr(self.initial_app, field)
            final_value = getattr(self.final_app, field)
            if initial_value != final_value:
                changes.append((field, initial_value, final_value))
        return changes
