from datetime import timedelta

from django.contrib.auth.decorators import login_required
from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from .document_model import STATUS_CHOICES, Document, Transfer
from .recent_files_view import _options          # labels come from create_file_config.py

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
    docs = Document.objects.all()

    # ---- counts ----
    counts = dict(docs.values_list("status").annotate(n=Count("id")).order_by())
    total = sum(counts.values())
    overdue = docs.filter(due_date__lt=today).exclude(status="completed").count()
    completed = counts.get("completed", 0)
    stats = {
        "total": total,
        "overdue": overdue,
        "by_status": [(v, label, counts.get(v, 0)) for v, label in STATUS_CHOICES],
        "rate": round(completed * 100 / total) if total else 0,
    }

    labels = {"priority": dict(_options("priority")), "status": dict(STATUS_CHOICES),
              "type": dict(_options("doc_type"))}

    # ---- needs attention: overdue + due within 7 days ----
    attention = list(
        docs.exclude(status="completed")
        .filter(due_date__isnull=False, due_date__lte=today + timedelta(days=7))
        .order_by("due_date")[:ATTENTION_LIMIT]
    )
    for d in attention:
        d.due_note, d.due_class = _due_note(d, today)
        d.status_label = labels["status"].get(d.status, d.status.title())
        d.priority_label = labels["priority"].get(d.priority, d.priority.title())

    # ---- recent files ----
    recent = list(docs.order_by("-created_at")[:RECENT_LIMIT])
    for d in recent:
        d.status_label = labels["status"].get(d.status, d.status.title())
        d.type_label = labels["type"].get(d.doc_type, d.doc_type.title())

    inbox_files, sent_files = [], []
    if request.user.is_authenticated:
        inbox_files = list(Document.objects.filter(assigned_to=request.user).order_by("-updated_at")[:5])
        sent_files = list(Transfer.objects.filter(sender=request.user).select_related(
            "document", "recipient").order_by("-sent_at")[:5])
        for f in inbox_files:
            f.status_label = labels["status"].get(f.status, f.status.title())
        for transfer in sent_files:
            transfer.status_label = labels["status"].get(transfer.document.status, transfer.document.status.title())

    return render(request, "pages/index.html", {
        "segment": "dashboard",
        "stats": stats,
        "attention": attention,
        "recent": recent,
        "inbox_files": inbox_files,
        "sent_files": sent_files,
    })
