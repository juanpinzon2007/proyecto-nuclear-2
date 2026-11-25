"""Cuenta independientemente los registros de decisión de cada intento."""

from alembic import op

revision = "20261124_decision_counts"
down_revision = "20261120_global_traceability"
branch_labels = None
depends_on = None


def _reemplazar_vista(conteos, uniones, agrupacion=""):
    op.execute(f"""
        CREATE OR REPLACE VIEW public.vw_trazabilidad_intentos_decisiones AS
        SELECT
            i.id_intento, i.id_participacion, i.numero_intento,
            i.estado AS estado_intento, i.inicio, i.fin, i.duracion_concedida_segundos,
            p.convocatoria_id, c.sesion_id, sp.version_caso_id, vc.nombre AS caso_nombre,
            ue.id_usuario AS estudiante_id, ue.nombre AS estudiante_nombre,
            ue.correo AS estudiante_correo, i.id_consentimiento,
            cons.version_texto AS consentimiento_version,
            cons.fecha_aceptacion AS consentimiento_fecha,
            i.id_permiso_extra, pe.justificacion AS motivo_intento_extra,
            {conteos},
            ri.nota_final AS nota_provisional, ri.modalidad AS modalidad_provisional,
            ri.ambito AS ambito_evaluacion, ri.version_regla, ri.procedencia_sha256
        FROM public.intento i
        JOIN public.participacion p ON p.id_participacion = i.id_participacion
        JOIN public.convocatoria c ON c.id = p.convocatoria_id
        JOIN public.sesion_programada sp ON sp.id = c.sesion_id
        JOIN public.version_caso vc ON vc.id = sp.version_caso_id
        JOIN public.grupo_estudiante ge ON ge.id_grupo_estudiante = p.id_grupo_estudiante
        JOIN public.usuario ue ON ue.id_usuario = ge.id_estudiante
        JOIN public.consentimiento cons ON cons.id_consentimiento = i.id_consentimiento
        LEFT JOIN public.permiso_intento_extra pe ON pe.id_permiso_extra = i.id_permiso_extra
        LEFT JOIN public.resultado_intento ri ON ri.id_intento = i.id_intento
        {uniones}
        {agrupacion}
    """)


def upgrade():
    _reemplazar_vista(
        """
        (SELECT COUNT(*) FROM public.borrador_decision_intento b
         WHERE b.id_intento = i.id_intento) AS total_borradores_actuales,
        (SELECT COUNT(*) FROM public.historial_cambio_decision h
         WHERE h.id_intento = i.id_intento) AS total_cambios_decision,
        (SELECT COUNT(*) FROM public.paso_simulacion ps
         WHERE ps.id_intento = i.id_intento) AS total_pasos_congelados
        """,
        "",
    )


def downgrade():
    _reemplazar_vista(
        """
        COUNT(DISTINCT b.id_borrador) AS total_borradores_actuales,
        COUNT(DISTINCT h.id_historial) AS total_cambios_decision,
        COUNT(DISTINCT ps.id_paso) AS total_pasos_congelados
        """,
        """
        LEFT JOIN public.borrador_decision_intento b ON b.id_intento = i.id_intento
        LEFT JOIN public.historial_cambio_decision h ON h.id_intento = i.id_intento
        LEFT JOIN public.paso_simulacion ps ON ps.id_intento = i.id_intento
        """,
        """
        GROUP BY i.id_intento, i.id_participacion, i.numero_intento, i.estado,
            i.inicio, i.fin, i.duracion_concedida_segundos, p.convocatoria_id, c.sesion_id,
            sp.version_caso_id, vc.nombre, ue.id_usuario, ue.nombre, ue.correo, i.id_consentimiento,
            cons.version_texto, cons.fecha_aceptacion, i.id_permiso_extra, pe.justificacion,
            ri.nota_final, ri.modalidad, ri.ambito, ri.version_regla, ri.procedencia_sha256
        """,
    )
