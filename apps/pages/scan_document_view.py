import copy
from datetime import date

from django.shortcuts import render

from .create_file_view import _clean_value
from .document_matching import OCRUnavailable, extract_text, find_document_match
from .scan_document_config import PAGE, SECTIONS


# ---------------------------------------------------------------------------
# WHAT HAPPENS WHEN THE FORM IS VALID: change this function only.
# `data`  -> cleaned values keyed by field name   (data["reference_no"], data["ocr"], ...)
# `files` -> uploaded files keyed by field name   (files["scan_file"])
# Return the scan number shown in the success message.
# ---------------------------------------------------------------------------
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
    match = None
    scan_result = None
    scan_error = None

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
            uploaded = files.get("scan_file")
            try:
                scan_result = extract_text(uploaded, uploaded.name)
                if scan_result.strip():
                    match = find_document_match(scan_result)
                else:
                    scan_error = "We couldn't read text from this scan. Try a clearer, well-lit image or a searchable PDF."
            except OCRUnavailable:
                scan_error = "Text recognition isn't available. Install Tesseract OCR on the server and the pytesseract, Pillow, and PyMuPDF packages to search scans."
            except Exception:
                scan_error = "We couldn't read this file. Try a clear image or PDF scan."
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
        "match": match,
        "scan_result": scan_result,
        "scan_error": scan_error,
        "searched": request.method == "POST" and not has_errors,
    })
