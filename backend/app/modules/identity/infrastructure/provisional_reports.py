"""Exportación provisional (.xlsx / .pdf) para sesiones activas o pendientes de publicación oficial."""

from datetime import UTC, datetime
from io import BytesIO
from math import ceil
from uuid import UUID
from xml.sax.saxutils import escape

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.modules.cases.infrastructure.models.caso import VersionCasoModel
from app.modules.identity.domain.entities import ContextoAcceso, Rol
from app.modules.identity.domain.errors import AccesoDenegado, RecursoNoDisponible
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.models import UsuarioORM
from app.modules.identity.infrastructure.report_exporters import FONT_LOCK, XLSX
from app.modules.identity.infrastructure.repositories import id_entero
from app.modules.participation.infrastructure.academic_results_models import AusenciaAcademicaModel
from app.modules.participation.infrastructure.models import IntentoModel, ParticipacionModel
from app.modules.participation.infrastructure.result_models import ResultadoIntentoModel
from app.modules.scheduling.infrastructure.models import (
    ConvocatoriaModel,
    EspacioAcademicoModel,
    SesionProgramadaModel,
)


def _resolver_datos_sesion(db: Session, usuario: ContextoAcceso, id_sesion: UUID) -> dict:
    if not usuario.roles.intersection({Rol.DOCENTE, Rol.ADMINISTRADOR}):
        raise AccesoDenegado()

    sesion = db.get(SesionProgramadaModel, id_sesion)
    if sesion is None:
        raise RecursoNoDisponible()

    if Rol.ADMINISTRADOR not in usuario.roles:
        doc_uuid = db.scalar(
            select(IdentidadAcademicaORM.id_academico).where(
                IdentidadAcademicaORM.id_usuario == id_entero(usuario.id_usuario),
                IdentidadAcademicaORM.sistema == "SCHEDULING",
            )
        )
        if doc_uuid is None or doc_uuid != sesion.docente_id:
            raise AccesoDenegado()

    espacio = db.get(EspacioAcademicoModel, sesion.espacio_academico_id)
    version = db.get(VersionCasoModel, sesion.version_caso_id)

    convs = list(
        db.scalars(
            select(ConvocatoriaModel).where(ConvocatoriaModel.sesion_id == sesion.id).order_by(ConvocatoriaModel.id)
        ).all()
    )

    filas: list[dict] = []
    for conv in convs:
        uid = db.scalar(
            select(IdentidadAcademicaORM.id_usuario).where(
                IdentidadAcademicaORM.id_academico == conv.estudiante_id,
                IdentidadAcademicaORM.sistema == "SCHEDULING",
            )
        )
        est = db.get(UsuarioORM, uid) if uid is not None else None
        part = db.scalar(select(ParticipacionModel).where(ParticipacionModel.convocatoria_id == conv.id))
        intentos = (
            list(
                db.scalars(
                    select(IntentoModel)
                    .where(IntentoModel.id_participacion == part.id_participacion)
                    .order_by(IntentoModel.numero_intento.desc())
                ).all()
            )
            if part is not None
            else []
        )
        ultimo_int = intentos[0] if intentos else None
        res_int = (
            db.scalar(
                select(ResultadoIntentoModel).where(ResultadoIntentoModel.id_intento == ultimo_int.id_intento)
            )
            if ultimo_int is not None
            else None
        )
        aus = db.scalar(
            select(AusenciaAcademicaModel)
            .where(AusenciaAcademicaModel.convocatoria_id == conv.id)
            .order_by(AusenciaAcademicaModel.revision.desc())
            .limit(1)
        )
        ausente = bool(aus and aus.confirmada)
        if conv.estado == "RETIRADA":
            situacion = "RETIRADA"
        elif ausente:
            situacion = "AUSENTE"
        elif res_int is not None:
            situacion = f"{ultimo_int.estado} ({res_int.modalidad})"
        elif ultimo_int is not None:
            situacion = ultimo_int.estado
        else:
            situacion = "PENDIENTE"

        nota_txt = "0.00" if ausente else (f"{float(res_int.nota_final):.2f}" if res_int is not None else "--")
        filas.append(
            {
                "estudiante": est.nombre if est else str(conv.estudiante_id),
                "correo": est.correo if est else "",
                "convocatoria": conv.estado,
                "participacion": part.id_participacion if part is not None else "--",
                "intentos": len(intentos),
                "situacion": situacion,
                "nota": nota_txt,
            }
        )

    filas.sort(key=lambda f: f["estudiante"].casefold())
    return {
        "sesion_id": str(sesion.id),
        "estado_sesion": sesion.estado,
        "caso": version.nombre if version else str(sesion.version_caso_id),
        "espacio": espacio.nombre if espacio else str(sesion.espacio_academico_id),
        "lugar": sesion.lugar or "Virtual",
        "generado_utc": datetime.now(UTC).strftime("%Y-%m-%d %H:%M:%S UTC"),
        "filas": filas,
    }


def _exportar_xlsx(datos: dict) -> bytes:
    from openpyxl import Workbook
    from openpyxl.styles import Alignment, Font, PatternFill
    from openpyxl.utils import get_column_letter

    wb = Workbook()
    ws_meta = wb.active
    ws_meta.title = "Resumen"
    ws_meta.append(["Campo", "Valor"])
    for k, v in [
        ("Tipo de reporte", "Provisional / Seguimiento en curso (sin acta oficial congelada)"),
        ("Sesión", datos["sesion_id"]),
        ("Estado sesión", datos["estado_sesion"]),
        ("Caso", datos["caso"]),
        ("Espacio académico", datos["espacio"]),
        ("Lugar", datos["lugar"]),
        ("Generado en", datos["generado_utc"]),
        ("Total convocados", len(datos["filas"])),
    ]:
        ws_meta.append([k, v])

    ws = wb.create_sheet("Resultados Provisionales")
    headers = ["Estudiante", "Correo", "Convocatoria", "Participación", "Intentos", "Situación", "Nota (provisional)"]
    ws.append(headers)
    for f in datos["filas"]:
        ws.append([f["estudiante"], f["correo"], f["convocatoria"], f["participacion"], f["intentos"], f["situacion"], f["nota"]])

    for sheet in (ws_meta, ws):
        for row in sheet:
            for c in row:
                if isinstance(c.value, str):
                    c.data_type = "s"
                    if c.value.lstrip().startswith(("=", "+", "-", "@", "\t", "\r", "\n")):
                        c.quotePrefix = True
                if c.row == 1:
                    c.font = Font(bold=True, color="FFFFFF")
                    c.fill = PatternFill("solid", fgColor="102836")
                c.alignment = Alignment(vertical="top", wrap_text=True)
        for col in range(1, sheet.max_column + 1):
            vals = [str(sheet.cell(n, col).value or "") for n in range(1, sheet.max_row + 1)]
            sheet.column_dimensions[get_column_letter(col)].width = min(48, max(16, max(map(len, vals)) + 3))
        sheet.freeze_panes = "A2"

    out = BytesIO()
    wb.save(out)
    return out.getvalue()


def _exportar_pdf(datos: dict) -> bytes:
    from importlib.resources import files
    from reportlab.lib import colors
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.lib.styles import ParagraphStyle
    from reportlab.pdfbase import pdfmetrics
    from reportlab.pdfbase.ttfonts import TTFont
    from reportlab.platypus import LongTable, Paragraph, SimpleDocTemplate, Spacer, TableStyle

    with FONT_LOCK:
        if "SPSVera" not in pdfmetrics.getRegisteredFontNames():
            carpeta = files("reportlab").joinpath("fonts")
            pdfmetrics.registerFont(TTFont("SPSVera", str(carpeta.joinpath("Vera.ttf"))))
            pdfmetrics.registerFont(TTFont("SPSVeraBold", str(carpeta.joinpath("VeraBd.ttf"))))

    normal = ParagraphStyle("cuerpo", fontName="SPSVera", fontSize=8, leading=11, spaceAfter=4)
    titulo = ParagraphStyle("titulo", parent=normal, fontName="SPSVeraBold", fontSize=15, leading=19, spaceAfter=8)
    sub = ParagraphStyle("sub", parent=normal, fontName="SPSVeraBold", fontSize=10, leading=14, spaceBefore=8, spaceAfter=6)
    cell = ParagraphStyle("celda", parent=normal, fontSize=7, leading=9, spaceAfter=0)

    out = BytesIO()
    doc = SimpleDocTemplate(
        out,
        pagesize=landscape(A4),
        rightMargin=28,
        leftMargin=28,
        topMargin=28,
        bottomMargin=30,
        title="Simulador SPS - Reporte Provisional de Sesión",
    )
    p = lambda x, s=normal: Paragraph(escape(str(x)) if x is not None else "", s)

    story = [
        p("Simulador SPS — Reporte Provisional de Sesión", titulo),
        p(f"Caso: {datos['caso']} · Espacio: {datos['espacio']}"),
        p(f"Sesión: {datos['sesion_id']} · Estado: {datos['estado_sesion']} · Lugar: {datos['lugar']}"),
        p(f"Generado: {datos['generado_utc']} (Nota: documento informativo previo o complementario al acta oficial)"),
        Spacer(1, 8),
        p("Participaciones y notas registradas", sub),
    ]

    if not datos["filas"]:
        story.append(p("No hay convocatorias registradas en esta sesión todavía."))
    else:
        headers = ["Estudiante", "Correo", "Convocatoria", "Part.", "Intentos", "Situación", "Nota"]
        rows = [
            [
                f["estudiante"],
                f["correo"],
                f["convocatoria"],
                f["participacion"],
                f["intentos"],
                f["situacion"],
                f["nota"],
            ]
            for f in datos["filas"]
        ]
        table_data = [[p(h, cell) for h in headers]] + [[p(c, cell) for c in row] for row in rows]
        t = LongTable(table_data, colWidths=[150, 175, 80, 50, 55, 165, 65], repeatRows=1, hAlign="LEFT")
        t.setStyle(
            TableStyle(
                [
                    ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#102836")),
                    ("TEXTCOLOR", (0, 0), (-1, 0), colors.white),
                    ("GRID", (0, 0), (-1, -1), 0.35, colors.HexColor("#9AA5AA")),
                    ("VALIGN", (0, 0), (-1, -1), "TOP"),
                    ("LEFTPADDING", (0, 0), (-1, -1), 5),
                    ("RIGHTPADDING", (0, 0), (-1, -1), 5),
                    ("TOPPADDING", (0, 0), (-1, -1), 5),
                    ("BOTTOMPADDING", (0, 0), (-1, -1), 5),
                ]
            )
        )
        story.append(t)

    doc.build(story)
    return out.getvalue()


def generar_reporte_provisional(
    db: Session, usuario: ContextoAcceso, id_sesion: str, formato: str
) -> tuple[bytes, str, str]:
    try:
        sid = UUID(id_sesion)
    except (ValueError, TypeError):
        raise RecursoNoDisponible() from None

    datos = _resolver_datos_sesion(db, usuario, sid)
    if formato == "xlsx":
        return _exportar_xlsx(datos), XLSX, f"reporte-provisional-{sid}.xlsx"
    return _exportar_pdf(datos), "application/pdf", f"reporte-provisional-{sid}.pdf"
