"""
EDIT THIS FILE to change what the Scan Document page asks for.
Same field options as create_file_config.py (name, label, type, required,
placeholder, help, col, default, max_length, options, accept, ...).
"""

PAGE = {
    "title": "Scan Document",
    "subtitle": "Upload or capture a paper document to find its matching saved file.",
    "submit_label": "Find Matching File",
    "max_upload_mb": 15,
}

SECTIONS = [
    {
        "title": "Scanned file",
        "description": "Choose a scan or take a photo of the document (on a phone, the picker offers the camera).",
        "icon": "fa-camera",
        "fields": [
            {"name": "scan_file", "label": "Scan", "type": "file", "required": True, "col": 12,
             "accept": ".pdf,.docx,.png,.jpg,.jpeg,.tif,.tiff", "help": "PDF, Word document (.docx), or image."},
        ],
    },
]
