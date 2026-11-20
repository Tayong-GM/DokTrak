import copy
import uuid
from datetime import date

from django.contrib.auth import get_user_model
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.db import transaction
from django.shortcuts import redirect, render

from .create_file_config import PAGE, SECTIONS
from .document_model import Document, Transfer
from .models import DepartmentProfile


# ---------------------------------------------------------------------------
# WHAT HAPPENS WHEN THE FORM IS VALID: change this function only.
# `data`  -> cleaned values keyed by field name   (data["title"], data["priority"], ...)
# `files` -> uploaded files keyed by field name   (files["attachment"])
# Return the reference number to show in the success message.
# ---------------------------------------------------------------------------
def save_document(data, files, request, recipient):
    ref = f"{PAGE['reference_prefix']}-{date.today():%Y}-{uuid.uuid4().hex[:6].upper()}"
    model_fields = {f.name for f in Document._meta.fields}
    values = {k: v for k, v in data.items() if k in model_fields}
    values["from_office"] = (request.user.get_full_name().strip() or request.user.get_username())[:100]
    values["due_date"] = values.get("due_date") or None
    if files.get("attachment"):
        values["attachment"] = files["attachment"]
    with transaction.atomic():
        document = Document.objects.create(
            reference_no=ref,
            created_by=request.user,
            assigned_to=recipient,
            **values,
        )
        Transfer.objects.create(
            document=document, sender=request.user, recipient=recipient,
            kind="send", prev_status=document.status,
        )
    return ref


# ---------------------------------------------------------------------------
# Generic validation: driven by the field config, no need to edit per field.
# ---------------------------------------------------------------------------
def _clean_value(f, raw):
    t = f["type"]

    if t == "checkbox":
        checked = raw in ("on", "true", "1")
        if f.get("required") and not checked:
            return checked, "This must be checked."
        return checked, None

    raw = (raw or "").strip()
    if not raw:
        return "", ("This field is required." if f.get("required") else None)

    if t in ("text", "textarea", "email"):
        if f.get("max_length") and len(raw) > f["max_length"]:
            return raw, f"Maximum {f['max_length']} characters."
        if f.get("min_length") and len(raw) < f["min_length"]:
            return raw, f"Minimum {f['min_length']} characters."
        if t == "email":
            try:
                validate_email(raw)
            except ValidationError:
                return raw, "Enter a valid email address."
        return raw, None

    if t == "number":
        try:
            num = float(raw)
        except ValueError:
            return raw, "Enter a valid number."
        if f.get("min") is not None and num < f["min"]:
            return raw, f"Must be at least {f['min']}."
        if f.get("max") is not None and num > f["max"]:
            return raw, f"Must be at most {f['max']}."
        return (int(num) if num.is_integer() else num), None

    if t == "date":
        try:
            d = date.fromisoformat(raw)
        except ValueError:
            return raw, "Enter a valid date."
        if f.get("not_past") and d < date.today():
            return raw, "Date cannot be in the past."
        return d, None

    if t in ("select", "radio"):
        if raw not in {v for v, _ in f["options"]}:
            return raw, "Choose a valid option."
        return raw, None

    return raw, None


def _clean_file(f, upload, max_upload_mb=None):
    max_upload_mb = max_upload_mb or PAGE["max_upload_mb"]
    if not upload:
        return None, ("Please upload a file." if f.get("required") else None)
    exts = [e.strip().lower() for e in f.get("accept", "").split(",") if e.strip().startswith(".")]
    if exts and not any(upload.name.lower().endswith(e) for e in exts):
        return None, f"Allowed file types: {', '.join(exts)}"
    if upload.size > max_upload_mb * 1024 * 1024:
        return None, f"File is larger than {max_upload_mb} MB."
    return upload, None


def build_form_fields(sections, *, not_past=None, overrides=None):
    """Deep-copy the config sections and prepare their fields for rendering.

    not_past=True  -> keep the rule and set the date input's `min` to today
    not_past=False -> drop the rule (e.g. editing old files already past due)
    not_past=None  -> leave the rule untouched
    overrides      -> {field_name: {attr: value}} applied to the copies, so per-request
                      details (help text, required, ...) are declared up front instead
                      of patched onto the fields afterwards.
    Returns (sections, fields), where fields is the flat list of the copied fields.
    """
    sections = copy.deepcopy(sections)
    fields = [f for s in sections for f in s["fields"]]
    overrides = overrides or {}
    for f in fields:
        f["options"] = [(str(v), label) for v, label in f.get("options", [])]
        f["error"] = None
        if f["type"] == "date" and f.get("not_past"):
            if not_past is True:
                f["min"] = date.today().isoformat()
            elif not_past is False:
                f.pop("not_past")
        f.update(overrides.get(f["name"], {}))
    return sections, fields


@login_required
def create_file(request):
    destination_suggestions = []
    destination_users = {}

    sender_name = request.user.get_full_name().strip() or request.user.get_username()
    User = get_user_model()
    users = list(User.objects.filter(is_active=True).exclude(pk=request.user.pk).only(
        "username", "first_name", "last_name"
    ).order_by("first_name", "last_name", "username"))
    name_counts = {}
    for user in users:
        display = user.get_full_name().strip() or user.get_username()
        name_counts[display] = name_counts.get(display, 0) + 1
    for user in users:
        display = user.get_full_name().strip() or user.get_username()
        value = f"{display} (@{user.get_username()})" if name_counts[display] > 1 else display
        if len(value) > 100:
            value = user.get_username()[:100]
        destination_suggestions.append({"value": value, "label": f"User · @{user.get_username()}"})
        destination_users[value] = user
    departments = DepartmentProfile.objects.filter(user__is_active=True).exclude(
        department="",
    ).exclude(user=request.user).select_related("user").order_by("department", "user_id")
    department_members = {}
    for profile in departments:
        department_members.setdefault(profile.department[:100], []).append(profile.user)
    for department, members in department_members.items():
        if len(members) == 1 and department not in destination_users:
            destination_suggestions.append({"value": department, "label": "Office"})
            destination_users[department] = members[0]

    # Built after the sender and destinations exist, so their details are declared up front.
    sections, fields = build_form_fields(SECTIONS, not_past=True, overrides={
        "from_office": {
            "value": sender_name[:100],
            "readonly": True,
            "help": "Filled automatically with the signed-in sender.",
        },
        "to_office": {
            "suggestions": destination_suggestions,
            "help": "Choose a registered person or office. The file will be delivered to their inbox as soon as it is created.",
        },
    })

    has_errors = False
    duplicate_warning = False

    if request.method == "POST":
        data, files = {}, {}
        for f in fields:
            name = f["name"]
            if f["type"] == "file":
                value, f["error"] = _clean_file(f, request.FILES.get(name))
                files[name] = value
            else:
                raw = request.POST.get(name)
                value, f["error"] = _clean_value(f, raw)
                data[name] = value
                f["value"] = raw or ""
                f["checked"] = raw in ("on", "true", "1")
            has_errors = has_errors or bool(f["error"])

        if not has_errors:
            destination = data.get("to_office", "").strip()
            recipient = destination_users.get(destination)
            if recipient is None:
                to_field = next(f for f in fields if f["name"] == "to_office")
                to_field["error"] = "Choose a person, or an office with exactly one active registered member, so the file can be delivered."
                has_errors = True

        if not has_errors:
            duplicate_warning = Document.objects.filter(title__iexact=data.get("title", "")).exists()
            confirmed_duplicate = request.POST.get("confirm_duplicate") == "1"
            if not (duplicate_warning and not confirmed_duplicate):
                ref = save_document(data, files, request, recipient)
                messages.success(request, f"File {ref} was created and sent to {recipient.get_full_name().strip() or recipient.get_username()}.")
                return redirect("create_file")
    else:
        for f in fields:
            default = f.get("default", "")
            if default == "today":
                default = date.today().isoformat()
            if f["name"] == "from_office":
                default = sender_name[:100]
            f["value"] = default
            f["checked"] = bool(default)

    return render(request, "pages/create_file.html", {
        "segment": "create_file",
        "page": PAGE,
        "sections": sections,
        "has_errors": has_errors,
        "duplicate_warning": duplicate_warning,
    })