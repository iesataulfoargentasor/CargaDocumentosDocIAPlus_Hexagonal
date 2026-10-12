"""Reglas puras del catálogo; no dependen de HTTP ni almacenamiento."""
from app.domain.errors import ValidationError

def validate_metadata(form, catalog, center):
    fields = ("titulo", "ensenanza", "modulo", "curso_academico", "estado_declarado", "procedencia", "observaciones")
    result = {k: form.get(k, "").strip() for k in fields}
    errors = {}
    if not 5 <= len(result["titulo"]) <= 150:
        errors["titulo"] = "Escribe un título de entre 5 y 150 caracteres."
    teaching = catalog["ensenanzas"].get(result["ensenanza"])
    if not teaching:
        errors["ensenanza"] = "Selecciona una enseñanza del catálogo."
    if not teaching or result["modulo"] not in teaching["modulos"]:
        errors["modulo"] = "El módulo debe pertenecer a la enseñanza seleccionada."
    if result["curso_academico"] not in catalog["cursos"]:
        errors["curso_academico"] = "Selecciona un curso permitido."
    if result["estado_declarado"] not in ("borrador", "final"):
        errors["estado_declarado"] = "Indica si es borrador o documento final."
    if not 3 <= len(result["procedencia"]) <= 200:
        errors["procedencia"] = "Indica la procedencia (3–200 caracteres)."
    if len(result["observaciones"]) > 2000:
        errors["observaciones"] = "Máximo 2000 caracteres."
    if errors:
        raise ValidationError(errors)
    return {"centro": center, **result}
