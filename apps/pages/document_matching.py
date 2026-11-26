"""Extract text from uploaded documents and find matching saved attachments."""
import logging
import os
import re
import zipfile
from io import BytesIO
from pathlib import Path

from .document_model import Document

logger = logging.getLogger(__name__)


class OCRUnavailable(Exception):
    pass


# Errors that mean "this file can't be read", not "there is a bug in our code":
#   OSError      -> missing/corrupt files, PIL.UnidentifiedImageError, Tesseract not found
#   ValueError   -> bad image/PDF data
#   RuntimeError -> PyMuPDF (fitz) FileDataError and pytesseract TesseractError
#   BadZipFile   -> corrupt .docx
# Plus python-docx's PackageNotFoundError and Pillow's DecompressionBombError when installed.
# Anything else (TypeError, KeyError, database errors, ...) is a real bug and should surface.
UNREADABLE_FILE_ERRORS = (OSError, ValueError, RuntimeError, zipfile.BadZipFile)
try:
    from docx.opc.exceptions import PackageNotFoundError
    UNREADABLE_FILE_ERRORS += (PackageNotFoundError,)
except ImportError:
    pass
try:
    from PIL import Image as _PILImage
    UNREADABLE_FILE_ERRORS += (_PILImage.DecompressionBombError,)
except ImportError:
    pass


def _ocr_image(image):
    try:
        import pytesseract
        from PIL import Image, ImageOps
    except ImportError as exc:
        raise OCRUnavailable from exc
    configured_tesseract = os.environ.get("TESSERACT_CMD")
    if configured_tesseract:
        pytesseract.pytesseract.tesseract_cmd = configured_tesseract
    try:
        image = ImageOps.grayscale(image)
        image = ImageOps.autocontrast(image)
        return pytesseract.image_to_string(image, config="--psm 6")
    except Exception as exc:
        if "tesseract" in str(exc).lower() or "not found" in str(exc).lower():
            raise OCRUnavailable from exc
        raise


def extract_text(upload, filename):
    """Read searchable text where possible, then OCR image pages as needed."""
    suffix = Path(filename).suffix.lower()
    content = upload.read()
    upload.seek(0)

    if suffix == ".pdf":
        try:
            import fitz
        except ImportError:
            return ""
        text_pages = []
        with fitz.open(stream=content, filetype="pdf") as pdf:
            for page in pdf:
                text = page.get_text("text")
                if len(text.strip()) >= 20:
                    text_pages.append(text)
                else:
                    pix = page.get_pixmap(matrix=fitz.Matrix(1.5, 1.5), alpha=False)
                    from PIL import Image
                    text_pages.append(_ocr_image(Image.open(BytesIO(pix.tobytes("png")))))
        return "\n".join(text_pages)

    if suffix == ".docx":
        try:
            from docx import Document as WordDocument
            word = WordDocument(BytesIO(content))
            return "\n".join(p.text for p in word.paragraphs)
        except ImportError:
            return ""

    if suffix in {".png", ".jpg", ".jpeg", ".tif", ".tiff", ".bmp", ".webp"}:
        from PIL import Image
        with Image.open(BytesIO(content)) as image:
            return _ocr_image(image.copy())
    return ""


_STOP_WORDS = {
    "about", "after", "again", "against", "also", "among", "and", "are", "because", "been",
    "before", "being", "between", "both", "but", "can", "could", "document", "from", "have",
    "into", "more", "most", "must", "other", "shall", "should", "that", "their", "there",
    "these", "they", "this", "those", "through", "under", "until", "upon", "used", "were",
    "what", "when", "where", "which", "while", "with", "within", "would", "your",
}


def _tokens(text):
    return {token for token in re.findall(r"[a-z0-9][a-z0-9-]{2,}", text.lower()) if token not in _STOP_WORDS}


def find_document_match(scan_text):
    scan_tokens = _tokens(scan_text)
    if len(scan_tokens) < 3:
        return None
    best, best_score = None, 0
    for doc in Document.objects.filter(is_archived=False).exclude(attachment="").iterator():
        try:
            with doc.attachment.open("rb") as attachment:
                attachment_text = extract_text(attachment, doc.attachment.name)
        except OCRUnavailable:
            raise
        except UNREADABLE_FILE_ERRORS:
            # One unreadable attachment shouldn't stop the search: log it and move on.
            logger.warning("Skipping unreadable attachment of %s", doc.reference_no, exc_info=True)
            continue
        attachment_tokens = _tokens(attachment_text)
        if not attachment_tokens:
            continue
        shared = scan_tokens & attachment_tokens
        score = len(shared) / min(len(scan_tokens), len(attachment_tokens))
        reference_found = doc.reference_no.lower() in scan_text.lower()
        if reference_found:
            score = 1.0
        if (reference_found or len(shared) >= 3) and score > best_score:
            best, best_score = doc, score
    return best if best_score >= 0.12 else None