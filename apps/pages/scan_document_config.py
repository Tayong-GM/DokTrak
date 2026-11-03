"""
EDIT THIS FILE to change what the Scan Document page asks for.
Same field options as create_file_config.py (name, label, type, required,
placeholder, help, col, default, max_length, options, accept, ...).
"""

PAGE = {
    "title": "Scan Document",
    "subtitle": "Upload or capture a paper document and link it to a file.",
    "submit_label": "Save Scan",
    "success_message": "Scan {reference_no} was saved.",
    "reference_prefix": "SCN",      # SCN-2026-A1B2C3
    "max_upload_mb": 15,
}

SECTIONS = [
    {
        "title": "Scanned file",
        "description": "Choose a scan or take a photo of the document (on a phone, the picker offers the camera).",
        "icon": "fa-camera",
        "fields": [
            {"name": "scan_file", "label": "Scan", "type": "file", "required": True, "col": 12,
             "accept": ".pdf,.png,.jpg,.jpeg,.tif,.tiff", "help": "PDF or image."},
        ],
    },
    {
        "title": "Details",
        "description": "Link the scan to an existing file so it can be tracked.",
        "icon": "fa-link",
        "fields": [
            {"name": "reference_no", "label": "File reference no.", "type": "text", "max_length": 30,
             "col": 6, "placeholder": "e.g. DOK-2026-A1B2C3", "help": "Leave blank to save the scan without linking it."},
            {"name": "scan_title", "label": "Scan title", "type": "text", "max_length": 150, "col": 6,
             "placeholder": "e.g. Signed copy, page 1-3"},
            {"name": "scan_type", "label": "Scan type", "type": "radio", "required": True,
             "default": "original", "col": 8,
             "options": [("original", "Original"), ("copy", "Copy"), ("signed", "Signed"), ("attachment", "Attachment")]},
            {"name": "scan_date", "label": "Date scanned", "type": "date", "default": "today", "col": 4},
            {"name": "ocr", "label": "Extract text from this scan (OCR)", "type": "checkbox", "col": 12},
            {"name": "notes", "label": "Notes", "type": "textarea", "rows": 3, "max_length": 300, "col": 12},
        ],
    },
]
