from datetime import timedelta

from django.db.models import Count
from django.shortcuts import render
from django.utils import timezone

from .document_model import STATUS_CHOICES, Document
from .recent_files_view import _options          # labels come from create_file_config.py

WEEKS = 8                                        # how many weeks the "created per week" chart shows
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

    # ---- chart: files created per week (one query, bucketed in Python) ----
    this_monday = today - timedelta(days=today.weekday())
    first_monday = this_monday - timedelta(weeks=WEEKS - 1)
    weekly = [0] * WEEKS
    for created in docs.filter(created_at__date__gte=first_monday).values_list("created_at", flat=True):
        idx = (timezone.localtime(created).date() - first_monday).days // 7
        if 0 <= idx < WEEKS:
            weekly[idx] += 1
    chart = {
        "weeks": {
            "labels": [(first_monday + timedelta(weeks=i)).strftime("%b %d") for i in range(WEEKS)],
            "values": weekly,
        },
        "status": {
            "labels": [label for _, label in STATUS_CHOICES],
            "values": [counts.get(v, 0) for v, _ in STATUS_CHOICES],
        },
    }

    return render(request, "pages/index.html", {
        "segment": "dashboard",
        "stats": stats,
        "attention": attention,
        "recent": recent,
        "chart": chart,
        "created_this_week": sum(weekly[-1:]),
    })