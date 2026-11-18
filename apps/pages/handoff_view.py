"""Inbox (files sent to you) and Sent (files you sent to others) + the actions between them."""
from django.contrib import messages
from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.core.paginator import Paginator
from django.db import transaction
from django.db.models import F, Max, Q
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.utils.http import url_has_allowed_host_and_scheme
from django.views.decorators.http import require_POST

from .document_model import REVIEW_STATUS_CHOICES, STATUS_CHOICES, Document, Transfer
from .recent_files_view import _options          # priority / type labels from create_file_config.py

User = get_user_model()
PAGE_SIZE = 9


# ---------------------------------------------------------------------------
# helpers
# ---------------------------------------------------------------------------
def display_name(user):
    return (user.get_full_name() or user.get_username()) if user else "Unknown user"


def _people(me):
    """Everyone you can send a file to: (id, label)."""
    people = []
    for u in User.objects.filter(is_active=True).exclude(pk=me.pk).order_by("first_name", "username"):
        name = display_name(u)
        people.append((u.pk, name if name == u.get_username() else f"{name} (@{u.get_username()})"))
    return people


def _recipient(request):
    try:
        pk = int(request.POST.get("recipient", ""))
    except ValueError:
        return None
    return User.objects.filter(pk=pk, is_active=True).exclude(pk=request.user.pk).first()


def _remark(request):
    return request.POST.get("remark", "").strip()[:300]


def _back(request, default="inbox"):
    nxt = request.POST.get("next", "")
    if nxt and url_has_allowed_host_and_scheme(nxt, allowed_hosts={request.get_host()}):
        return redirect(nxt)
    return redirect(default)


def _mark_received(doc, user):
    return Transfer.objects.filter(
        document=doc, recipient=user, recalled=False, received_at__isnull=True,
    ).update(received_at=timezone.now())


def _hand_off(doc, sender, recipient, remark, kind, status):
    with transaction.atomic():
        Transfer.objects.create(document=doc, sender=sender, recipient=recipient,
                                remark=remark, kind=kind, prev_status=doc.status)
        doc.assigned_to = recipient
        doc.status = status
        doc.save(update_fields=["assigned_to", "status", "updated_at"])


def _holdable(me):
    """Files you currently hold and may send: yours that nobody has, or ones assigned to you."""
    return Document.objects.filter(Q(assigned_to=me) | Q(created_by=me, assigned_to__isnull=True))


def _pager_context(request, paginator, page_obj):
    params = request.GET.copy()
    params.pop("page", None)
    return {
        "page_range": paginator.get_elided_page_range(page_obj.number, on_each_side=1, on_ends=1),
        "qs": params.urlencode(),
    }


# ---------------------------------------------------------------------------
# INBOX: files other people sent to you
# ---------------------------------------------------------------------------
@login_required
def inbox(request):
    me = request.user
    q = request.GET.get("q", "").strip()
    status = request.GET.get("status", "")
    tab = request.GET.get("tab", "")

    new_ids = set(
        Transfer.objects.filter(recipient=me, recalled=False, received_at__isnull=True, document__assigned_to=me)
        .values_list("document_id", flat=True)
    )
    mine = Document.objects.filter(assigned_to=me)
    stats = {
        "total": mine.count(),
        "new": len(new_ids),
        "in_progress": mine.filter(status="in_progress").count(),
        "completed": mine.filter(status="completed").count(),
        "returned": mine.filter(status="returned").count(),
    }

    qs = mine.select_related("reviewed_by").annotate(latest_sent=Max("transfers__sent_at", filter=Q(transfers__recipient=me, transfers__recalled=False)))
    if tab == "new":
        qs = qs.filter(pk__in=new_ids)
    if status:
        qs = qs.filter(status=status)
    if q:
        qs = qs.filter(Q(title__icontains=q) | Q(reference_no__icontains=q) | Q(description__icontains=q))
    qs = qs.order_by(F("latest_sent").desc(nulls_last=True), "-updated_at")

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))
    docs = list(page_obj)

    incoming = {}                                    # latest hand-off to you, per file
    for t in Transfer.objects.filter(document__in=docs, recipient=me, recalled=False).select_related("sender"):
        incoming.setdefault(t.document_id, t)        # Transfer is ordered newest first

    status_labels, priority_labels = dict(STATUS_CHOICES), dict(_options("priority"))
    for d in docs:
        t = incoming.get(d.pk)
        d.incoming = t
        d.is_new = bool(t and t.received_at is None)
        d.sender_name = display_name(t.sender) if t else ""
        d.sender_initial = (d.sender_name[:1] or "?").upper()
        d.status_label = status_labels.get(d.status, d.status.title())
        d.priority_label = priority_labels.get(d.priority, d.priority.title())
        d.reviewed_by_name = display_name(d.reviewed_by)

    return render(request, "pages/inbox.html", {
        "segment": "inbox",
        "page_obj": page_obj,
        "result_count": paginator.count,
        "stats": stats,
        "filters": {"q": q, "status": status, "tab": tab},
        "has_filters": bool(q or status or tab),
        "people": _people(me),
        "work_statuses": [(v, l) for v, l in STATUS_CHOICES if v != "returned"],
        "review_statuses": REVIEW_STATUS_CHOICES,
        **_pager_context(request, paginator, page_obj),
    })


@login_required
@require_POST
def receive_file(request, pk):
    doc = get_object_or_404(Document, pk=pk, assigned_to=request.user)
    if _mark_received(doc, request.user):
        if doc.status == "pending":
            doc.status = "in_progress"
            doc.save(update_fields=["status", "updated_at"])
        if doc.status == "in_progress":
            messages.success(request, f"{doc.reference_no} received and moved to In progress.")
        else:
            messages.success(request, f"{doc.reference_no} marked as received.")
    return _back(request)


@login_required
@require_POST
def inbox_status(request, pk):
    doc = get_object_or_404(Document, pk=pk, assigned_to=request.user)
    status = request.POST.get("status", "")
    if status not in dict(STATUS_CHOICES) or status == "returned":
        messages.error(request, "Please choose a valid status. Use Return to send a file back.")
        return _back(request)
    _mark_received(doc, request.user)                # working on it counts as receiving it
    doc.status = status
    doc.save(update_fields=["status", "updated_at"])
    messages.success(request, f"{doc.reference_no} is now {dict(STATUS_CHOICES)[status]}.")
    return _back(request)


@login_required
@require_POST
def review_file(request, pk):
    doc = get_object_or_404(Document, pk=pk, assigned_to=request.user, is_archived=False)
    incoming = Transfer.objects.filter(
        document=doc, recipient=request.user, recalled=False,
    ).first()
    review_status = request.POST.get("review_status", "")
    if not incoming or not incoming.received_at:
        messages.error(request, "Receive the file before reviewing it.")
    elif review_status not in dict(REVIEW_STATUS_CHOICES):
        messages.error(request, "Choose Approved, Rejected, or Checked.")
    else:
        doc.review_status = review_status
        doc.reviewed_by = request.user
        doc.reviewed_at = timezone.now()
        doc.save(update_fields=["review_status", "reviewed_by", "reviewed_at", "updated_at"])
        messages.success(request, f"{doc.reference_no} review updated to {dict(REVIEW_STATUS_CHOICES)[review_status]}.")
    return _back(request)


@login_required
@require_POST
def forward_file(request, pk):
    """Forward a file you hold to someone else, or (with return=1) send it back to who sent it to you."""
    me = request.user
    doc = get_object_or_404(Document, pk=pk, assigned_to=me)
    remark = _remark(request)

    if request.POST.get("return"):
        last = doc.transfers.filter(recipient=me, recalled=False).select_related("sender").first()
        target = last.sender if last and last.sender and last.sender.is_active else None
        kind, status = "return", "returned"
        if target is None:
            messages.error(request, "There is nobody to return this file to.")
            return _back(request)
    else:
        target = _recipient(request)
        kind, status = "forward", "pending"
        if target is None:
            messages.error(request, "Please choose who to send this file to.")
            return _back(request)
        if doc.status == "completed":
            messages.error(request, "Completed files can't be forwarded.")
            return _back(request)

    _mark_received(doc, me)
    _hand_off(doc, me, target, remark, kind, status)
    verb = "returned to" if kind == "return" else "forwarded to"
    messages.success(request, f"{doc.reference_no} was {verb} {display_name(target)}.")
    return _back(request)


# ---------------------------------------------------------------------------
# SENT: files you sent to other people
# ---------------------------------------------------------------------------
@login_required
def sent(request):
    me = request.user
    q = request.GET.get("q", "").strip()
    state = request.GET.get("state", "")

    base = Transfer.objects.filter(sender=me)
    stats = {
        "total": base.count(),
        "waiting": base.filter(received_at__isnull=True, recalled=False).count(),
        "received": base.filter(received_at__isnull=False, recalled=False).count(),
        "recalled": base.filter(recalled=True).count(),
    }

    qs = base.select_related("document", "document__assigned_to", "recipient")
    if state == "waiting":
        qs = qs.filter(received_at__isnull=True, recalled=False)
    elif state == "received":
        qs = qs.filter(received_at__isnull=False, recalled=False)
    elif state == "recalled":
        qs = qs.filter(recalled=True)
    if q:
        qs = qs.filter(
            Q(document__title__icontains=q) | Q(document__reference_no__icontains=q)
            | Q(recipient__username__icontains=q) | Q(recipient__first_name__icontains=q) | Q(recipient__last_name__icontains=q)
        )

    paginator = Paginator(qs, PAGE_SIZE)
    page_obj = paginator.get_page(request.GET.get("page"))

    status_labels = dict(STATUS_CHOICES)
    for t in page_obj:
        d = t.document
        t.recipient_name = display_name(t.recipient)
        t.recipient_initial = (t.recipient_name[:1] or "?").upper()
        t.doc_status_label = status_labels.get(d.status, d.status.title())
        t.can_recall = (not t.recalled and t.received_at is None and d.assigned_to_id == t.recipient_id)
        t.holder_name = display_name(d.assigned_to) if d.assigned_to_id and d.assigned_to_id != t.recipient_id else ""

    return render(request, "pages/sent.html", {
        "segment": "sent",
        "page_obj": page_obj,
        "result_count": paginator.count,
        "stats": stats,
        "filters": {"q": q, "state": state},
        "has_filters": bool(q or state),
        "people": _people(me),
        "sendable": _holdable(me).exclude(status="completed").order_by("-created_at")[:300],
        "preselect": request.GET.get("send", ""),
        **_pager_context(request, paginator, page_obj),
    })


@login_required
@require_POST
def send_file(request):
    me = request.user
    try:
        doc = _holdable(me).filter(pk=int(request.POST.get("file", ""))).first()
    except ValueError:
        doc = None
    target = _recipient(request)

    if doc is None:
        messages.error(request, "Choose one of your own files to send.")
    elif doc.status == "completed":
        messages.error(request, "Completed files can't be sent.")
    elif target is None:
        messages.error(request, "Please choose who to send the file to.")
    else:
        kind = "forward" if doc.assigned_to_id == me.pk else "send"
        _mark_received(doc, me)
        _hand_off(doc, me, target, _remark(request), kind, "pending")
        messages.success(request, f"{doc.reference_no} was sent to {display_name(target)}.")
    return redirect("sent")


@login_required
@require_POST
def recall_transfer(request, pk):
    """Take back a file the other person hasn't received yet."""
    t = get_object_or_404(
        Transfer.objects.select_related("document"),
        pk=pk, sender=request.user, recalled=False, received_at__isnull=True,
    )
    doc = t.document
    if doc.assigned_to_id != t.recipient_id:
        messages.error(request, "This file has already moved on and can't be recalled.")
        return redirect("sent")

    held_before = doc.transfers.filter(recipient=request.user, recalled=False, received_at__isnull=False).exists()
    with transaction.atomic():
        t.recalled = True
        t.save(update_fields=["recalled"])
        doc.assigned_to = request.user if held_before else None
        if t.prev_status:
            doc.status = t.prev_status
        doc.save(update_fields=["assigned_to", "status", "updated_at"])
    messages.success(request, f"{doc.reference_no} was recalled.")
    return redirect("sent")
