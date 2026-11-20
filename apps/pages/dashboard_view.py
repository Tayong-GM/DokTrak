from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from .document_model import STATUS_CHOICES, Document, Transfer
from .recent_files_view import attach_labels

ATTENTION_LIMIT = 6
RECENT_LIMIT = 6


def _due_note(d, today):
    """'Overdue by 2 days', 'Due today', 'Due in 3 days' + a css class."""
    n = (d.due_date - today).days
    if n < 0:
        return f"Overdue by {-n} day{'s' if n != -1 else ''}", "late"
    if n == 0:
        return "Due today", "soon"
    return f"Due in {n} day{'s' if n != 1 else ''}", "soon"


@login_required
def dashboard(request):
    today = timezone.localdate()
    docs = Document.objects.filter(is_archived=False)     # active files only

    # ---- counts ----
    counts = dict(docs.values_list("status").annotate(n=Count("id")).order_by())
    total = sum(counts.values())
    overdue = docs.filter(due_date__lt=today).exclude(status="completed").count()
    completed = counts.get("completed", 0)
    returned_to_user = docs.filter(
        assigned_to=request.user, status="returned",
    ).count()
    stats = {
        "total": total,
        "overdue": overdue,
        "returned": returned_to_user,
        "by_status": [
            (v, label, returned_to_user if v == "returned" else counts.get(v, 0))
            for v, label in STATUS_CHOICES
        ],
        "rate": round(completed * 100 / total) if total else 0,
    }

    

    # ---- needs attention: overdue + due within 7 days ----
    attention = list(
        docs.exclude(status="completed")
        .filter(due_date__isnull=False, due_date__lte=today + timedelta(days=7))
        .order_by("due_date")[:ATTENTION_LIMIT]
    )
    attach_labels(attention, status=True, priority=True)
    for d in attention:
        d.due_note, d.due_class = _due_note(d, today)

    recent = list(docs.order_by("-created_at")[:RECENT_LIMIT])
    attach_labels(recent, status=True, doc_type=True)

    inbox_files = list(docs.filter(assigned_to=request.user).order_by("-updated_at")[:5])
    sent_files = list(Transfer.objects.filter(sender=request.user).select_related(
        "document", "recipient").order_by("-sent_at")[:5])
    attach_labels(inbox_files, status=True)
    attach_labels([t.document for t in sent_files], status=True)
    for transfer in sent_files:
        transfer.status_label = transfer.document.status_label

    return render(request, "pages/index.html", {
        "segment": "dashboard",
        "stats": stats,
        "attention": attention,
        "recent": recent,
        "inbox_files": inbox_files,
        "sent_files": sent_files,
    })