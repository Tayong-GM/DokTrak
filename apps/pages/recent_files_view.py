import copy
from datetime import date

from django.contrib import messages
from django.core.paginator import Paginator
from django.db.models import F, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .create_file_config import PAGE as CREATE_PAGE, SECTIONS
from .create_file_view import _clean_file, _clean_value      # same validation as Create File
from .document_model import STATUS_CHOICES, Document

PAGE_SIZE = 9
SORTS = {
    "new": ("Newest first", ["-created_at"]),
    "old": ("Oldest first", ["created_at"]),
    "due": ("Due soon", [F("due_date").asc(nulls_last=True), "-created_at"]),
    "title": ("Title A-Z", ["title"]),
}


def _options(field_name):
    """Options of a field in create_file_config.py, so labels always match the form."""
    for section in SECTIONS:
        for f in section["fields"]:
            if f["name"] == field_name:
                return [(str(v), label) for v, label in f.get("options", [])]
    return []


def _safe_next(request, default="recent_files"):
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return nxt
    return default


# ---------------------------------------------------------------------------
# LIST
# ---------------------------------------------------------------------------
def recent_files(request):
    today = timezone.localdate()
    qs = Document.objects.all()

    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    dtype = request.GET.get("type", "")
    priority = request.GET.get("priority", "")
    sort = request.GET.get("sort", "new")
    if sort not in SORTS:
        sort = "new"

    if q:
        qs = qs.filter(
            Q(title__icontains=q) | Q(reference_no__icontains=q) | Q(description__icontains=q)
            | Q(from_office__icontains=q) | Q(to_office__icontains=q)
        )
    if status == "overdue":
        qs = qs.filter(due_date__lt=today).exclude(status="completed")
    elif status:
        qs = qs.filter(status=status)
    if dtype:
        qs = qs.filter(doc_type=dtype)
    if priority:
        qs = qs.filter(priority=priority)
    qs = qs.order_by(*SORTS[sort][1])

    # summary cards (always over all files, not just the filtered ones)
    all_docs = Document.objects.all()
    stats = {
        "total": all_docs.count(),
        "overdue": all_docs.filter(due_date__lt=today).exclude(status="completed").count(),
    }
    for value, _ in STATUS_CHOICES:
        stats[value] = all_docs.filter(status=value).count()

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    type_labels, priority_labels = dict(_options("doc_type")), dict(_options("priority"))
    status_labels = dict(STATUS_CHOICES)
    for d in page_obj:
        d.type_label = type_labels.get(d.doc_type, d.doc_type.title())
        d.priority_label = priority_labels.get(d.priority, d.priority.title())
        d.status_label = status_labels.get(d.status, d.status.title())

    params = request.GET.copy()
    params.pop("page", None)

    return render(request, "pages/recent_files.html", {
        "segment": "recent_files",
        "page_obj": page_obj,
        "page_range": paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1),
        "result_count": paginator.count,
        "stats": stats,
        "filters": {"q": q, "status": status, "type": dtype, "priority": priority, "sort": sort},
        "has_filters": bool(q or status or dtype or priority),
        "qs": params.urlencode(),
        "type_options": _options("doc_type"),
        "priority_options": _options("priority"),
        "status_options": STATUS_CHOICES,
        "sort_options": [(k, v[0]) for k, v in SORTS.items()],
    })


# ---------------------------------------------------------------------------
# EDIT  (re-uses the Create File form + config, pre-filled with the saved values)
# ---------------------------------------------------------------------------
LOCKED = {"id", "reference_no", "created_by", "created_at", "updated_at"}


def edit_file(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    model_fields = {f.name: f for f in Document._meta.fields}

    sections = copy.deepcopy(SECTIONS)
    fields = [f for s in sections for f in s["fields"]]
    for f in fields:
        f["options"] = [(str(v), label) for v, label in f.get("options", [])]
        f["error"] = None
        f.pop("not_past", None)                       # old files may already be past their due date
        if f["type"] == "file":
            f["required"] = False
            if doc.attachment:
                f["help"] = f"Current file: {doc.attachment_name}. Upload a new one to replace it."

    has_errors = False
    if request.method == "POST":
        data, new_files = {}, {}
        for f in fields:
            name = f["name"]
            if f["type"] == "file":
                value, f["error"] = _clean_file(f, request.FILES.get(name))
                new_files[name] = value
            else:
                raw = request.POST.get(name)
                value, f["error"] = _clean_value(f, raw)
                data[name] = value
                f["value"] = raw or ""
                f["checked"] = raw in ("on", "true", "1")
            has_errors = has_errors or bool(f["error"])

        if not has_errors:
            for name, value in data.items():
                mf = model_fields.get(name)
                if mf is None or name in LOCKED:
                    continue
                if value == "" and mf.null:
                    value = None
                setattr(doc, name, value)
            for name, upload in new_files.items():
                if upload and name in model_fields:
                    getattr(doc, name).delete(save=False)     # remove the old file from storage
                    setattr(doc, name, upload)
            doc.save()
            messages.success(request, f"File {doc.reference_no} was updated.")
            return redirect("recent_files")
    else:
        for f in fields:
            value = getattr(doc, f["name"], "") if f["type"] != "file" else ""
            if isinstance(value, date):
                value = value.isoformat()
            f["value"] = "" if value is None else value
            f["checked"] = bool(value)

    page = {**CREATE_PAGE, "title": "Edit File", "subtitle": f"Update the details of {doc.reference_no}.",
            "submit_label": "Save changes"}
    return render(request, "pages/create_file.html", {
        "segment": "recent_files", "page": page, "sections": sections, "has_errors": has_errors,
    })


# ---------------------------------------------------------------------------
# DELETE / QUICK STATUS CHANGE  (POST only)
# ---------------------------------------------------------------------------
@require_POST
def delete_file(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    ref = doc.reference_no
    if doc.attachment:
        doc.attachment.delete(save=False)                 # don't leave orphan files on disk
    doc.delete()
    messages.success(request, f"File {ref} was deleted.")
    return redirect(_safe_next(request))


@require_POST
def update_file_status(request, pk):
    doc = get_object_or_404(Document, pk=pk)
    status = request.POST.get("status", "")
    if status in dict(STATUS_CHOICES):
        doc.status = status
        doc.save(update_fields=["status", "updated_at"])
        messages.success(request, f"{doc.reference_no} marked as {dict(STATUS_CHOICES)[status]}.")
    else:
        messages.error(request, "Invalid status.")
    return redirect(_safe_next(request))
