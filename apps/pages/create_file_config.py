"""
EDIT THIS FILE to change what the Create File page asks for.
No template or view changes needed: add, remove or reorder fields here.

FIELD OPTIONS
  name         key used in the submitted data (unique)          [required]
  label        text shown above the input                       [required]
  type         text | textarea | email | number | date |
               select | radio | checkbox | file                 [required]
  required     True/False
  placeholder  hint text inside the input
  help         small grey text under the input
  col          grid width 1-12 (12 = full row, 6 = half, 4 = third)
  default      starting value ("today" works for date fields)
  max_length / min_length   text, textarea, email
  min / max                 number
  not_past     True -> date cannot be earlier than today
  rows                      textarea height
  options      [("value", "Label"), ...]  for select / radio
  accept       ".pdf,.docx,.png"          for file (also the allowed extensions)
  readonly     True/False
"""

PAGE = {
    "title": "Create File",
    "subtitle": "Create the document and send it straight to its destination.",
    "submit_label": "Create & Send",
    "success_message": "File {reference_no} was created successfully.",
    "reference_prefix": "DOK",     # DOK-2026-A1B2C3
    "max_upload_mb": 10,
}

SECTIONS = [
    {
        "title": "Document details",
        "description": "Basic information used to identify the file.",
        "icon": "fa-file-alt",
        "fields": [
            {"name": "title", "label": "Document title", "type": "text", "required": True,
             "max_length": 150, "placeholder": "e.g. Budget request for Q1", "col": 8},
            {"name": "doc_type", "label": "Document type", "type": "select", "required": True, "col": 4,
             "options": [("memo", "Memo"), ("letter", "Letter"), ("report", "Report"),
                         ("request", "Request"), ("contract", "Contract"), ("other", "Other")]},
            {"name": "description", "label": "Description", "type": "textarea", "rows": 4,
             "max_length": 500, "col": 12, "placeholder": "What is this document about?"},
        ],
    },
    {
        "title": "Routing",
        "description": "Choose the person or office that should receive this file.",
        "icon": "fa-route",
        "fields": [
            {"name": "from_office", "label": "From (office / person)", "type": "text",
             "required": True, "max_length": 100, "col": 4},
            {"name": "to_office", "label": "Send directly to", "type": "select",
             "required": True, "col": 4, "placeholder": "Choose a person or office...",
             "options": []},
            {"name": "final_office", "label": "Final recipient", "type": "select",
             "required": True, "col": 4, "placeholder": "Choose a person or office...",
             "options": []},
            {"name": "priority", "label": "Priority / deadline", "type": "radio", "required": True,
             "default": "two_weeks", "col": 12,
             "options": [("two_weeks", "2 Weeks"), ("one_week", "1 Week"),
                         ("three_days", "3 Days"), ("one_day", "1 Day"), ("custom", "Custom")]},
            {"name": "due_date", "label": "Custom due date", "type": "date",
             "col": 4, "hidden": True, "custom_due_date": True},
            {"name": "due_time", "label": "Deadline time (Philippine time)", "type": "time", "required": True,
             "col": 4, "default": "17:00"},
            {"name": "confidential", "label": "Mark this file as confidential", "type": "checkbox", "col": 12,
             "icon": "fa-lock"},
        ],
    },
    {
        "title": "Attachment",
        "description": "Upload the document file (optional).",
        "icon": "fa-paperclip",
        "fields": [
            {"name": "attachment", "label": "File", "type": "file", "accept": ".pdf,.doc,.docx,.png,.jpg,.jpeg",
             "col": 12, "help": "PDF, Word or image."},
        ],
    },
]