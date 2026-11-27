import os

from django.conf import settings
from django.db import models
from django.utils import timezone

# Workflow statuses. The system sets them; nobody picks one by hand:
#   pending      -> sent / forwarded, waiting for the recipient to receive it
#   in_progress  -> received, being handled
#   returned     -> returned to the previous sender (until they receive it)
#   completed    -> documented by the final recipient (locked)
STATUS_CHOICES = [
    ("pending", "Pending"),
    ("in_progress", "In progress"),
    ("completed", "Completed"),
    ("returned", "Returned"),
]
REVIEW_STATUS_CHOICES = [
    ("approved", "Approved"),
    ("rejected", "Rejected"),
    ("checked", "Checked"),
]

_NOT_GIVEN = object()


class Document(models.Model):
    """A tracked file created from the Create File page.

    doc_type and priority are plain text on purpose: their allowed values live in
    create_file_config.py, so changing those options never needs a migration.
    """
    reference_no = models.CharField(max_length=30, unique=True)
    title = models.CharField(max_length=150)
    doc_type = models.CharField(max_length=30, blank=True)
    description = models.TextField(blank=True)
    from_office = models.CharField(max_length=100, blank=True)
    to_office = models.CharField(max_length=100, blank=True)
    final_office = models.CharField(max_length=100, blank=True)
    priority = models.CharField(max_length=20, default="normal")
    due_date = models.DateField(null=True, blank=True)
    due_time = models.TimeField(null=True, blank=True)
    confidential = models.BooleanField(default=False)
    is_archived = models.BooleanField(default=False)
    archived_at = models.DateTimeField(null=True, blank=True)
    status = models.CharField(max_length=20, default="pending")
    completed_at = models.DateTimeField(null=True, blank=True)
    review_status = models.CharField(max_length=20, blank=True, choices=REVIEW_STATUS_CHOICES)
    reviewed_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.SET_NULL,
        related_name="reviewed_documents",
    )
    reviewed_at = models.DateTimeField(null=True, blank=True)
    attachment = models.FileField(upload_to="documents/%Y/%m/", blank=True)
    created_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="+",
    )

    assigned_to = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="assigned_documents",
    )
    # The office that ends the route by marking the file as documented.
    # Empty on files created before this field existed: any holder may document those.
    final_recipient = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="final_documents",
    )
    documented_by = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True,
        on_delete=models.SET_NULL, related_name="documented_files",
    )

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["is_archived", "status"], name="doc_arch_status_idx"),
            models.Index(fields=["assigned_to", "is_archived", "status"], name="doc_inbox_idx"),
            models.Index(fields=["due_date"], name="doc_due_idx"),
        ]

    def __str__(self):
        return f"{self.reference_no} - {self.title}"

    @property
    def is_overdue(self):
        if not self.due_date or self.status == "completed":
            return False
        today = timezone.localdate()
        if self.due_date < today:
            return True
        return bool(self.due_date == today and self.due_time and self.due_time < timezone.localtime().time())

    @property
    def attachment_name(self):
        return os.path.basename(self.attachment.name) if self.attachment else ""

    # ------------------------------------------------------------------
    # Pipeline rules. Every "may this happen?" check lives here and returns
    # None when allowed, or the message to show. Views only ask and display.
    # Flow: send > receive > (decide) > forward / return, ends with "document".
    # ------------------------------------------------------------------
    @property
    def is_locked(self):
        return self.status == "completed"

    @property
    def has_been_received(self):
        """True once any live (not recalled) hand-off of this file has been received."""
        if hasattr(self, "received_flag"):          # set by a queryset annotation, saves queries
            return self.received_flag
        return self.transfers.filter(recalled=False, received_at__isnull=False).exists()

    def latest_incoming(self, user):
        """The newest live hand-off of this file to `user`."""
        return self.transfers.filter(recipient=user, recalled=False).select_related("sender").first()

    def _incoming_for(self, user, incoming):
        return self.latest_incoming(user) if incoming is _NOT_GIVEN else incoming

    @staticmethod
    def _recall_waiting(incoming):
        return bool(incoming and incoming.recall_requested_at and incoming.recall_decided_at is None)

    def has_decision_by(self, user, incoming=_NOT_GIVEN):
        """True if `user` recorded a review decision after receiving this hand-off."""
        incoming = self._incoming_for(user, incoming)
        return bool(
            incoming and incoming.received_at and self.review_status
            and self.reviewed_by_id == user.pk and self.reviewed_at
            and self.reviewed_at >= incoming.received_at
        )

    def review_error(self, user, review_status):
        if self.is_locked:
            return "Documented files are locked and can't be reviewed."
        incoming = self.latest_incoming(user)
        if not incoming or not incoming.received_at:
            return "Receive the file before reviewing it."
        if review_status not in dict(REVIEW_STATUS_CHOICES):
            return "Choose Approved, Rejected, or Checked."
        return None

    def send_error(self, user, incoming=_NOT_GIVEN):
        """May `user` send / forward this file on?"""
        if self.is_locked:
            return "Documented files are locked and can't be sent or forwarded."
        if self.assigned_to_id == user.pk:           # holding it through a hand-off
            incoming = self._incoming_for(user, incoming)
            if not incoming or not incoming.received_at:
                return "Receive the file before sending it on."
            if self._recall_waiting(incoming):
                return "Respond to the pending recall request before forwarding this file."
        return None

    def return_error(self, user, incoming=_NOT_GIVEN):
        """May `user` return this file to whoever sent it to them?"""
        if self.is_locked:
            return "Documented files are locked and can't be returned."
        incoming = self._incoming_for(user, incoming)
        if not incoming or not incoming.received_at:
            return "Receive the file before returning it."
        if self._recall_waiting(incoming):
            return "Respond to the pending recall request before returning this file."
        if self.created_by_id == user.pk:
            return "You created this file, so send it on instead of returning it."
        if incoming.sender is None or not incoming.sender.is_active:
            return "There is nobody to return this file to."
        if not self.has_decision_by(user, incoming):
            return "Record a review decision (Approved, Rejected or Checked) before returning this file."
        return None

    def document_error(self, user, incoming=_NOT_GIVEN):
        """May `user` mark this file as documented (the last step)?"""
        if self.is_locked:
            return "This file is already documented."
        incoming = self._incoming_for(user, incoming)
        if not incoming or not incoming.received_at:
            return "Receive the file before marking it as documented."
        if self._recall_waiting(incoming):
            return "Respond to the pending recall request first."
        if self.final_recipient_id not in (None, user.pk):
            return f"Only {self.final_office or 'the final recipient'} can mark this file as documented."
        return None

    def _creator_error(self, user, verb, past):
        if self.created_by_id != user.pk:
            return f"Only the person who created this file can {verb} it."
        if self.has_been_received:
            return f"This file has already been received, so it can't be {past}."
        return None

    def edit_error(self, user):
        return self._creator_error(user, "edit", "edited")

    def delete_error(self, user):
        return self._creator_error(user, "delete", "deleted")

    def archive_error(self, user):
        if user.pk not in (self.created_by_id, self.assigned_to_id):
            return "Only the creator or the current holder can archive this file."
        return None


class Transfer(models.Model):
    """One hand-off of a file from one user to another."""
    document = models.ForeignKey(Document, on_delete=models.CASCADE, related_name="transfers")
    sender = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                               on_delete=models.SET_NULL, related_name="sent_transfers")
    recipient = models.ForeignKey(settings.AUTH_USER_MODEL, null=True, blank=True,
                                  on_delete=models.SET_NULL, related_name="received_transfers")
    kind = models.CharField(max_length=10, default="send")      # send / forward / return
    remark = models.CharField(max_length=300, blank=True)
    prev_status = models.CharField(max_length=20, blank=True)   # restored if the sender recalls it
    sent_at = models.DateTimeField(auto_now_add=True)
    received_at = models.DateTimeField(null=True, blank=True)
    recalled = models.BooleanField(default=False)
    recall_requested_at = models.DateTimeField(null=True, blank=True)
    recall_decided_at = models.DateTimeField(null=True, blank=True)
    recall_approved = models.BooleanField(null=True, blank=True)

    class Meta:
        ordering = ["-sent_at"]
        indexes = [
            models.Index(fields=["recipient", "recalled", "received_at"], name="xfer_recipient_idx"),
            models.Index(fields=["sender", "recalled", "received_at"], name="xfer_sender_idx"),
        ]

    def __str__(self):
        return f"{self.document.reference_no}: {self.sender} -> {self.recipient}"

    def save(self, *args, **kwargs):
        # Never store an empty prev_status: fall back to the document's current status.
        # Callers create the Transfer before changing doc.status, so this is the old status.
        if not self.prev_status and self.document_id:
            self.prev_status = self.document.status
        super().save(*args, **kwargs)

    def recall_error(self):
        if self.recalled:
            return "This file was already recalled."
        if self.document.status == "completed":
            return "Documented files are locked and can't be recalled."
        if self.recall_requested_at and self.recall_decided_at is None:
            return "A recall request is already waiting for the recipient."
        if self.document.assigned_to_id != self.recipient_id:
            return "This file has already moved on and can't be recalled."
        latest = self.document.transfers.filter(recipient_id=self.recipient_id, recalled=False).first()
        if not latest or latest.pk != self.pk:
            return "This file has already moved on and can't be recalled."
        return None