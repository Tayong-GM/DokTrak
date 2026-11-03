import copy
import uuid
from datetime import date

from django.contrib import messages
from django.shortcuts import redirect, render

from .create_file_view import _clean_value          # reuse the same field validation
from .scan_document_config import PAGE, SECTIONS


# ---------------------------------------------------------------------------
# WHAT HAPPENS WHEN THE FORM IS VALID: change this function only.
# `data`  -> cleaned values keyed by field name   (data["reference_no"], data["ocr"], ...)
# `files` -> uploaded files keyed by field name   (files["scan_file"])
# Return the scan number shown in the success message.
# ---------------------------------------------------------------------------
def save_scan(data, files, request):
    ref = f"{PAGE['reference_prefix']}-{date.today():%Y}-{uuid.uuid4().hex[:6].upper()}"

    # Example: save to a model
    # Scan.objects.create(scan_no=ref, uploaded_by=request.user, **data)

    # Example: store the upload (needs MEDIA_ROOT set in settings)
    # from django.core.files.storage import default_storage
    # f = files["scan_file"]
    # default_storage.save(f"scans/{ref}/{f.name}", f)

    return ref


def _clean_scan_file(f, upload):
    if not upload:
        return None, ("Please upload a file." if f.get("required") else None)
    exts = [e.strip().lower() for e in f.get("accept", "").split(",") if e.strip().startswith(".")]
    if exts and not any(upload.name.lower().endswith(e) for e in exts):
        return None, f"Allowed file types: {', '.join(exts)}"
    if upload.size > PAGE["max_upload_mb"] * 1024 * 1024:
        return None, f"File is larger than {PAGE['max_upload_mb']} MB."
    return upload, None


def scan_document(request):
    sections = copy.deepcopy(SECTIONS)
    fields = [f for s in sections for f in s["fields"]]
    for f in fields:
        f["options"] = [(str(v), label) for v, label in f.get("options", [])]
        f["error"] = None

    has_errors = False

    if request.method == "POST":
        data, files = {}, {}
        for f in fields:
            name = f["name"]
            if f["type"] == "file":
                value, f["error"] = _clean_scan_file(f, request.FILES.get(name))
                files[name] = value
            else:
                raw = request.POST.get(name)
                value, f["error"] = _clean_value(f, raw)
                data[name] = value
                f["value"] = raw or ""
                f["checked"] = raw in ("on", "true", "1")
            has_errors = has_errors or bool(f["error"])

        if not has_errors:
            ref = save_scan(data, files, request)
            messages.success(request, PAGE["success_message"].format(reference_no=ref))
            return redirect("scan_document")
    else:
        for f in fields:
            default = f.get("default", "")
            if default == "today":
                default = date.today().isoformat()
            f["value"] = default
            f["checked"] = bool(default)

    return render(request, "pages/scan_document.html", {
        "segment": "scan_document",
        "page": PAGE,
        "sections": sections,
        "has_errors": has_errors,
    })
