"""Adaptador binario: inspección estructural, sin OCR ni conversión."""
import hashlib
import io
import zipfile
from pathlib import PurePosixPath
from pypdf import PdfReader
from docx import Document
from app.domain.document import ValidatedFile
from app.domain.errors import ValidationError

def validate_file(stream, filename, max_bytes):
    if stream is None or not filename:
        raise ValidationError({"archivo": "Selecciona un archivo."})
    filename = PurePosixPath(filename.replace("\\", "/")).name
    if len(filename) > 200 or any(ord(c) < 32 or ord(c) == 127 for c in filename):
        raise ValidationError({"archivo": "El nombre del archivo no es válido (máximo 200 caracteres)."})
    extension = filename.rsplit(".", 1)[-1].lower() if "." in filename else ""
    if extension not in ("pdf", "docx", "txt"):
        raise ValidationError({"archivo": "Solo se permiten PDF, DOCX y TXT."})
    content = stream.read(max_bytes + 1)
    if not content:
        raise ValidationError({"archivo": "El archivo está vacío."})
    if len(content) > max_bytes:
        raise ValidationError({"archivo": "El archivo supera el tamaño máximo permitido."})
    try:
        if extension == "pdf":
            if not content.startswith(b"%PDF-"):
                raise ValueError()
            pdf = PdfReader(io.BytesIO(content), strict=True)
            if pdf.is_encrypted:
                raise ValidationError({"archivo": "No se admiten PDF cifrados o con contraseña."})
            if not len(pdf.pages):
                raise ValueError()
            for page in pdf.pages:
                # Recorre la estructura; no exige texto ni realiza OCR.
                _ = page.mediabox
            mime = "application/pdf"
        elif extension == "docx":
            if not zipfile.is_zipfile(io.BytesIO(content)):
                raise ValueError()
            with zipfile.ZipFile(io.BytesIO(content)) as archive:
                infos = archive.infolist()
                if len(infos) > 2000 or sum(i.file_size for i in infos) > 80 * 1024 * 1024:
                    raise ValidationError({"archivo": "El DOCX descomprimido supera los límites del piloto."})
                names = archive.namelist()
                if "word/document.xml" not in names or "[Content_Types].xml" not in names:
                    raise ValueError()
                if any("vbaproject" in n.lower() for n in names) or b"macroenabled" in archive.read("[Content_Types].xml").lower():
                    raise ValidationError({"archivo": "El DOCX contiene componentes o una declaración de macros, no admitidos en esta versión. Exporta una copia a PDF y revisa su contenido antes de subirla."})
                embedded = [i for i in infos if not i.is_dir() and i.filename.lower().startswith("word/embeddings/")]
                if embedded:
                    raise ValidationError({"archivo": "El DOCX contiene objetos incrustados (por ejemplo, de Paint o Excel). Esto no significa necesariamente que tenga macros. Esta versión no admite esos objetos. Exporta una copia a PDF y comprueba que se vea todo, o sustituye los objetos por imágenes normales en una copia del DOCX. El original no se ha guardado ni modificado."})
                if archive.testzip():
                    raise ValueError()
            Document(io.BytesIO(content))
            mime = "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
        else:
            text = content.decode("utf-8-sig")
            if not text.strip() or any(ord(c) < 32 and c not in "\n\r\t" for c in text):
                raise ValueError()
            mime = "text/plain"
    except ValidationError:
        raise
    except Exception as exc:
        raise ValidationError({"archivo": "El contenido no corresponde al formato, es ilegible o está corrupto. Los TXT deben estar en UTF-8."}) from exc
    return ValidatedFile(content, filename, extension, mime, hashlib.sha256(content).hexdigest())


class DocumentFileValidator:
    validate = staticmethod(validate_file)
