import copy
import uuid
from datetime import date

from django.contrib import messages
from django.core.exceptions import ValidationError
from django.core.validators import validate_email
from django.shortcuts import redirect, render

from .create_file_config import PAGE, SECTIONS


# ---------------------------------------------------------------------------
# WHAT HAPPENS WHEN THE FORM IS VALID: change this function only.
# `data`  -> cleaned values keyed by field name   (data["title"], data["priority"], ...)
# `files` -> uploaded files keyed by field name   (files["attachment"])
# Return the reference number to show in the success message.
# ---------------------------------------------------------------------------
def save_document(data, files, request):
    ref = f"{PAGE['reference_prefix']}-{date.today():%Y}-{uuid.uuid4().hex[:6].upper()}"

    # Example: save to a model
    # Document.objects.create(reference_no=ref, created_by=request.user, **data)

    # Example: store the upload (needs MEDIA_ROOT set in settings)
    # from django.core.files.storage import default_storage
    # f = files.get("attachment")
    # if f:
    #     default_storage.save(f"documents/{ref}/{f.name}", f)

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


def _clean_file(f, upload):
    if not upload:
        return None, ("Please upload a file." if f.get("required") else None)
    exts = [e.strip().lower() for e in f.get("accept", "").split(",") if e.strip().startswith(".")]
    if exts and not any(upload.name.lower().endswith(e) for e in exts):
        return None, f"Allowed file types: {', '.join(exts)}"
    if upload.size > PAGE["max_upload_mb"] * 1024 * 1024:
        return None, f"File is larger than {PAGE['max_upload_mb']} MB."
    return upload, None


def create_file(request):
    sections = copy.deepcopy(SECTIONS)
    fields = [f for s in sections for f in s["fields"]]
    for f in fields:
        f["options"] = [(str(v), label) for v, label in f.get("options", [])]
        f["error"] = None
        if f["type"] == "date" and f.get("not_past"):
            f["min"] = date.today().isoformat()

    has_errors = False

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
            ref = save_document(data, files, request)
            messages.success(request, PAGE["success_message"].format(reference_no=ref))
            return redirect("create_file")
    else:
        for f in fields:
            default = f.get("default", "")
            if default == "today":
                default = date.today().isoformat()
            f["value"] = default
            f["checked"] = bool(default)

    return render(request, "pages/create_file.html", {
        "segment": "create_file",
        "page": PAGE,
        "sections": sections,
        "has_errors": has_errors,
    })