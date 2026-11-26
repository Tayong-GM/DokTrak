from django.db.models import Q


def handoff_counts(request):
    """Adds inbox counts and recent hand-off notifications to every template."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return {}
    from .document_model import STATUS_CHOICES, Document, Transfer      # imported here so Django has finished loading apps
    incoming = Transfer.objects.filter(
        recipient=user, recalled=False, received_at__isnull=True, document__assigned_to=user,
    ).count()
    recall_requests = Transfer.objects.filter(
        recipient=user, recalled=False, recall_requested_at__isnull=False,
        recall_decided_at__isnull=True, document__assigned_to=user,
    ).count()

    transfers = Transfer.objects.filter(Q(sender=user) | Q(recipient=user)).select_related(
        "document", "sender", "recipient"
    ).order_by("-sent_at")[:30]
    notifications = []
    for transfer in transfers:
        doc = transfer.document
        if transfer.recipient_id == user.pk:
            sender = transfer.sender.get_full_name() or transfer.sender.username if transfer.sender else "Someone"
            notifications.append({"date": transfer.sent_at, "text": f"{sender} sent you {doc.reference_no}: {doc.title}", "url": "/inbox/"})
            if transfer.recall_requested_at and transfer.recall_decided_at is None and not transfer.recalled:
                notifications.append({"date": transfer.recall_requested_at, "text": f"{sender} asked to recall {doc.reference_no}: {doc.title}", "url": "/inbox/"})
        if transfer.sender_id == user.pk and transfer.received_at:
            recipient = transfer.recipient.get_full_name() or transfer.recipient.username if transfer.recipient else "The recipient"
            notifications.append({"date": transfer.received_at, "text": f"{recipient} received {doc.reference_no}: {doc.title}", "url": "/sent/"})
        if transfer.sender_id == user.pk and transfer.recall_decided_at:
            recipient = transfer.recipient.get_full_name() or transfer.recipient.username if transfer.recipient else "The recipient"
            result = "approved" if transfer.recall_approved else "declined"
            notifications.append({"date": transfer.recall_decided_at, "text": f"{recipient} {result} your recall request for {doc.reference_no}", "url": "/sent/"})
    status_labels = dict(STATUS_CHOICES)
    for doc in Document.objects.filter(assigned_to=user).order_by("-updated_at")[:8]:
        notifications.append({
            "date": doc.updated_at,
            "text": f"{doc.reference_no}: {doc.title} is {status_labels.get(doc.status, doc.status.title())}",
            "url": "/inbox/",
        })
    notifications.sort(key=lambda item: item["date"], reverse=True)
    return {"inbox_new_count": incoming + recall_requests, "notifications": notifications[:8]}
