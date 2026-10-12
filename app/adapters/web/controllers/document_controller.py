import io
from flask import Blueprint, current_app, flash, g, redirect, render_template, request, send_file, url_for
from app.adapters.web.security import permission_required
from app.domain.errors import Duplicate, PossibleRevision, ValidationError
from app.application.dto import UploadCommand

documents = Blueprint("documents", __name__)

def service():
    return current_app.extensions["documents"]

@documents.get("/")
@permission_required("read")
def catalog():
    filters = {k: request.args.get(k, "").strip() for k in ("q", "modulo", "curso_academico", "estado_declarado")}
    selected = service().list(g.user, filters)
    return render_template("documents/catalog.html", records=selected, filters=filters)

@documents.route("/programaciones/nueva", methods=["GET", "POST"])
@permission_required("upload")
def upload():
    errors, candidates = {}, []
    if request.method == "POST":
        try:
            storage = request.files.get("archivo")
            fields = ("titulo", "ensenanza", "modulo", "curso_academico", "estado_declarado", "procedencia", "observaciones")
            command = UploadCommand(
                metadata={k: request.form.get(k, "") for k in fields},
                stream=storage.stream if storage else None,
                filename=storage.filename if storage else "",
                relation={k: request.form.get(k, "") for k in ("relacion_id", "relacion_tipo", "relacion_motivo")})
            record = service().create(g.user, command)
            flash("Programación guardada correctamente. Esto no implica aprobación oficial ni publicación en un RAG.", "success")
            return redirect(url_for("documents.detail", document_id=record["id"]))
        except ValidationError as exc:
            errors = exc.errors
        except Duplicate as exc:
            return render_template("documents/duplicate.html", record=exc.record, mismatch=exc.mismatch), 409
        except PossibleRevision as exc:
            candidates = exc.candidates
            errors["relacion"] = "Ya existe documentación del mismo módulo y curso. Indica la relación y vuelve a seleccionar el archivo para confirmar."
    return render_template("documents/upload.html", form=request.form, errors=errors, candidates=candidates), (422 if errors else 200)

@documents.get("/programaciones/<document_id>")
@permission_required("read")
def detail(document_id):
    return render_template("documents/detail.html", record=service().get(g.user, document_id))

@documents.get("/programaciones/<document_id>/descargar")
@permission_required("read")
def download(document_id):
    result = service().download(g.user, document_id)
    return send_file(io.BytesIO(result.content), as_attachment=True, download_name=result.filename,
                     mimetype=result.mime, max_age=0)
