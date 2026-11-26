import os

from django.conf import settings
from django.db import models
from django.utils import timezone

# Workflow statuses shown on the Recent Files page (edit freely; no migration needed).
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
# Manual status changes allowed from each status (via the Inbox status dropdown).
# "returned" is never a target here: it is only set by the Return action.
ALLOWED_STATUS_TRANSITIONS = {
    "pending": {"in_progress", "completed"},
    "in_progress": {"pending", "completed"},
    "completed": {"in_progress"},          # reopen; remove this line to make completed final
    "returned": {"in_progress", "completed"},
}


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
    
    def can_move_to(self, status):
        return status == self.status or status in ALLOWED_STATUS_TRANSITIONS.get(self.status, set())

    def status_change_error(self, new_status):
        """None if the holder may set this status, else a message to show."""
        if new_status not in dict(STATUS_CHOICES) or new_status == "returned":
            return "Please choose a valid status. Use Return to send a file back."
        if not self.can_move_to(new_status):
            labels = dict(STATUS_CHOICES)
            return f"A {labels.get(self.status, self.status)} file can't be moved to {labels[new_status]}."
        return None

    def latest_incoming(self, user):
        """The newest live hand-off of this file to `user`."""
        return self.transfers.filter(recipient=user, recalled=False).select_related("sender").first()

    def review_error(self, user, review_status):
        incoming = self.latest_incoming(user)
        if not incoming or not incoming.received_at:
            return "Receive the file before reviewing it."
        if review_status not in dict(REVIEW_STATUS_CHOICES):
            return "Choose Approved, Rejected, or Checked."
        return None

    def send_error(self):
        if self.status == "completed":
            return "Completed files can't be sent or forwarded."
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
        if self.recall_requested_at and self.recall_decided_at is None:
            return "A recall request is already waiting for the recipient."
        if self.document.assigned_to_id != self.recipient_id:
            return "This file has already moved on and can't be recalled."
        latest = self.document.transfers.filter(recipient_id=self.recipient_id, recalled=False).first()
        if not latest or latest.pk != self.pk:
            return "This file has already moved on and can't be recalled."
        return None
