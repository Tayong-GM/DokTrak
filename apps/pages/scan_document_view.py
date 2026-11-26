import logging

from django.contrib.auth.decorators import login_required
from django.shortcuts import render
from django.utils import timezone

from .create_file_view import _clean_file, _clean_value, build_form_fields
from .document_matching import UNREADABLE_FILE_ERRORS, OCRUnavailable, extract_text, find_document_match
from .scan_document_config import PAGE, SECTIONS

logger = logging.getLogger(__name__)


@login_required
def scan_document(request):
    sections, fields = build_form_fields(SECTIONS)

    has_errors = False
    match = None
    scan_result = None
    scan_error = None

    if request.method == "POST":
        data, files = {}, {}
        for f in fields:
            name = f["name"]
            if f["type"] == "file":
                # Uses this page's own upload limit, not the Create File one.
                value, f["error"] = _clean_file(f, request.FILES.get(name), PAGE["max_upload_mb"])
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
            except UNREADABLE_FILE_ERRORS:
                logger.exception("Could not read scan %r", uploaded.name)
                scan_error = "We couldn't read this file. Try a clear image or PDF scan."
    else:
        for f in fields:
            default = f.get("default", "")
            if default == "today":
                default = timezone.localdate().isoformat()
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
