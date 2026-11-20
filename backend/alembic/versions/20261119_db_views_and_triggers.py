"""Agrega vistas académicas y disparadores de integridad operativa en PostgreSQL.

Revision ID: 20261119_db_views_and_triggers
Revises: 20261119_student_first_login_otp
Create Date: 2026-11-19 07:45:00.000000
"""

from alembic import op


revision = "20261119_db_views_and_triggers"
down_revision = "20261119_student_first_login_otp"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return

    # 1. Disparador de integridad básica en usuario
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.sps_validar_usuario_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        BEGIN
            NEW.nombre := btrim(NEW.nombre);
            NEW.correo := btrim(NEW.correo);
            IF length(NEW.nombre) < 2 THEN
                RAISE EXCEPTION 'El nombre del usuario debe tener al menos 2 caracteres.'
                    USING ERRCODE = '23514';
            END IF;
            IF NEW.correo = '' OR position('@' in NEW.correo) <= 1 THEN
                RAISE EXCEPTION 'El correo institucional del usuario no es válido.'
                    USING ERRCODE = '23514';
            END IF;
            IF length(btrim(NEW.clave_hash)) = 0 THEN
                RAISE EXCEPTION 'La cuenta requiere clave_hash no vacía.'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $function$;

        CREATE TRIGGER trg_usuario_integridad
        BEFORE INSERT OR UPDATE ON public.usuario
        FOR EACH ROW
        EXECUTE FUNCTION public.sps_validar_usuario_fn();
        """
    )

    # 2. Disparador de verificación única en primer ingreso estudiantil
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.sps_validar_verificacion_primer_ingreso_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            rol_nombre text;
        BEGIN
            SELECT upper(btrim(r.nombre))
            INTO rol_nombre
            FROM public.usuario u
            JOIN public.rol r ON r.id_rol = u.id_rol
            WHERE u.id_usuario = NEW.id_usuario;

            IF rol_nombre IS NULL OR rol_nombre <> 'ESTUDIANTE' THEN
                RAISE EXCEPTION 'La verificación de primer ingreso solo aplica a cuentas con rol ESTUDIANTE.'
                    USING ERRCODE = '23514';
            END IF;

            IF NEW.intentos < 0 THEN
                RAISE EXCEPTION 'El contador de intentos OTP no puede ser negativo.'
                    USING ERRCODE = '23514';
            END IF;

            IF NEW.verificado THEN
                IF NEW.verificado_en IS NULL THEN
                    NEW.verificado_en := now();
                END IF;
                NEW.codigo_hash := NULL;
                NEW.expira_en := NULL;
                NEW.intentos := 0;
            END IF;

            RETURN NEW;
        END;
        $function$;

        CREATE TRIGGER trg_verificacion_primer_ingreso_guard
        BEFORE INSERT OR UPDATE ON public.verificacion_primer_ingreso
        FOR EACH ROW
        EXECUTE FUNCTION public.sps_validar_verificacion_primer_ingreso_fn();
        """
    )

    # 3. Disparador de inmutabilidad de borradores cuando el intento ya cerró (RF-10)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.sps_proteger_borrador_intento_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        AS $function$
        DECLARE
            estado_actual text;
        BEGIN
            SELECT estado INTO estado_actual
            FROM public.intento
            WHERE id_intento = NEW.id_intento;

            IF estado_actual IS NULL THEN
                RAISE EXCEPTION 'Intento asociado inexistente para el borrador.'
                    USING ERRCODE = '23514';
            END IF;

            IF estado_actual <> 'EN_CURSO' THEN
                RAISE EXCEPTION 'No se pueden modificar borradores de un intento en estado %.', estado_actual
                    USING ERRCODE = '23514';
            END IF;

            IF NEW.actualizado_en IS NULL THEN
                NEW.actualizado_en := now();
            END IF;

            RETURN NEW;
        END;
        $function$;

        CREATE TRIGGER trg_borrador_decision_intento_guard
        BEFORE INSERT OR UPDATE ON public.borrador_decision_intento
        FOR EACH ROW
        EXECUTE FUNCTION public.sps_proteger_borrador_intento_fn();
        """
    )

    # 4. Vistas académicas y de auditoría
    op.execute(
        """
        CREATE OR REPLACE VIEW public.vw_catalogo_casos AS
        SELECT
            c.id AS caso_id,
            c.id_caso,
            v.id AS version_id,
            v.numero AS numero_version,
            v.nombre AS nombre_caso,
            v.estado,
            v.tiempo_estimado_min,
            u.nombre AS docente_nombre,
            u.correo AS docente_correo,
            COUNT(DISTINCT e.id) AS total_escenarios,
            COUNT(DISTINCT p.id) AS total_preguntas,
            (r.id IS NOT NULL) AS tiene_rubrica,
            r.nombre AS rubrica_nombre,
            r.version_regla,
            c.creado_en
        FROM public.caso c
        JOIN public.version_caso v ON v.caso_id = c.id
        LEFT JOIN public.identidad_academica ia
            ON ia.sistema = 'CASES' AND ia.id_academico = c.docente_creador_id
        LEFT JOIN public.usuario u ON u.id_usuario = ia.id_usuario
        LEFT JOIN public.escenario e ON e.version_caso_id = v.id
        LEFT JOIN public.pregunta p ON p.escenario_id = e.id
        LEFT JOIN public.rubrica r ON r.version_caso_id = v.id
        GROUP BY
            c.id, c.id_caso, v.id, v.numero, v.nombre, v.estado,
            v.tiempo_estimado_min, u.nombre, u.correo, r.id, r.nombre, r.version_regla, c.creado_en;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW public.vw_resumen_sesiones AS
        SELECT
            sp.id AS sesion_id,
            sp.estado AS estado_sesion,
            ea.nombre AS espacio_nombre,
            vc.nombre AS caso_nombre,
            vc.numero AS version_numero,
            ga.nombre AS grupo_nombre,
            ga.periodo AS grupo_periodo,
            ud.nombre AS docente_nombre,
            sp.fecha_inicio,
            sp.fecha_fin,
            sp.tiempo_maximo_minutos,
            COUNT(DISTINCT conv.id) FILTER (WHERE conv.estado = 'ACTIVA') AS total_convocatorias_activas,
            COUNT(DISTINCT part.id_participacion) AS total_participaciones,
            COUNT(DISTINCT intn.id_intento) FILTER (WHERE intn.estado IN ('FINALIZADO', 'VENCIDO')) AS total_intentos_cerrados
        FROM public.sesion_programada sp
        JOIN public.espacio_academico ea ON ea.id = sp.espacio_academico_id
        JOIN public.version_caso vc ON vc.id = sp.version_caso_id
        LEFT JOIN public.asignacion_caso ac ON ac.sesion_programada_id = sp.id
        LEFT JOIN public.grupo_academico ga ON ga.id_grupo = ac.id_grupo
        LEFT JOIN public.identidad_academica ia
            ON ia.sistema = 'SCHEDULING' AND ia.id_academico = sp.docente_id
        LEFT JOIN public.usuario ud ON ud.id_usuario = ia.id_usuario
        LEFT JOIN public.convocatoria conv ON conv.sesion_id = sp.id
        LEFT JOIN public.participacion part ON part.convocatoria_id = conv.id
        LEFT JOIN public.intento intn ON intn.id_participacion = part.id_participacion
        GROUP BY
            sp.id, sp.estado, ea.nombre, vc.nombre, vc.numero, ga.nombre, ga.periodo,
            ud.nombre, sp.fecha_inicio, sp.fecha_fin, sp.tiempo_maximo_minutos;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW public.vw_seguimiento_participacion AS
        SELECT
            sp.id AS sesion_id,
            sp.estado AS estado_sesion,
            vc.nombre AS caso_nombre,
            conv.id AS convocatoria_id,
            conv.estado AS estado_convocatoria,
            ue.id_usuario AS estudiante_id,
            ue.nombre AS estudiante_nombre,
            ue.correo AS estudiante_correo,
            part.id_participacion,
            part.estado AS estado_participacion,
            intn.id_intento AS intento_id,
            intn.numero_intento,
            intn.estado AS estado_intento,
            ri.nota_final AS nota_provisional,
            ri.modalidad AS modalidad_provisional,
            rp.nota_definitiva AS nota_oficial,
            rp.situacion AS situacion_oficial,
            (rd.id_retroalimentacion IS NOT NULL) AS tiene_retroalimentacion,
            rd.texto AS retroalimentacion_docente
        FROM public.convocatoria conv
        JOIN public.sesion_programada sp ON sp.id = conv.sesion_id
        JOIN public.version_caso vc ON vc.id = sp.version_caso_id
        LEFT JOIN public.identidad_academica ia
            ON ia.sistema = 'SCHEDULING' AND ia.id_academico = conv.estudiante_id
        LEFT JOIN public.usuario ue ON ue.id_usuario = ia.id_usuario
        LEFT JOIN public.participacion part ON part.convocatoria_id = conv.id
        LEFT JOIN LATERAL (
            SELECT i.*
            FROM public.intento i
            WHERE i.id_participacion = part.id_participacion
            ORDER BY i.numero_intento DESC
            LIMIT 1
        ) intn ON TRUE
        LEFT JOIN public.resultado_intento ri ON ri.id_intento = intn.id_intento
        LEFT JOIN public.resultado_participacion rp ON rp.convocatoria_id = conv.id
        LEFT JOIN public.retroalimentacion_docente rd ON rd.id_participacion = part.id_participacion;
        """
    )

    op.execute(
        """
        CREATE OR REPLACE VIEW public.vw_auditoria_primer_ingreso AS
        SELECT
            u.id_usuario,
            u.nombre,
            u.correo,
            u.activo,
            upper(btrim(r.nombre)) AS rol,
            CASE
                WHEN vpi.id IS NULL THEN 'VERIFICADO_LEGACY'
                WHEN vpi.verificado THEN 'VERIFICADO'
                ELSE 'PENDIENTE_PRIMER_INGRESO'
            END AS estado_primer_ingreso,
            vpi.verificado_en,
            COALESCE(vpi.intentos, 0) AS intentos_otp,
            vpi.expira_en,
            MAX(CASE WHEN ia.sistema = 'CASES' THEN ia.id_academico::text END) AS identidad_cases,
            MAX(CASE WHEN ia.sistema = 'SCHEDULING' THEN ia.id_academico::text END) AS identidad_scheduling
        FROM public.usuario u
        JOIN public.rol r ON r.id_rol = u.id_rol
        LEFT JOIN public.verificacion_primer_ingreso vpi ON vpi.id_usuario = u.id_usuario
        LEFT JOIN public.identidad_academica ia ON ia.id_usuario = u.id_usuario
        GROUP BY
            u.id_usuario, u.nombre, u.correo, u.activo, r.nombre,
            vpi.id, vpi.verificado, vpi.verificado_en, vpi.intentos, vpi.expira_en;
        """
    )


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return

    op.execute("DROP VIEW IF EXISTS public.vw_auditoria_primer_ingreso;")
    op.execute("DROP VIEW IF EXISTS public.vw_seguimiento_participacion;")
    op.execute("DROP VIEW IF EXISTS public.vw_resumen_sesiones;")
    op.execute("DROP VIEW IF EXISTS public.vw_catalogo_casos;")

    op.execute("DROP TRIGGER IF EXISTS trg_borrador_decision_intento_guard ON public.borrador_decision_intento;")
    op.execute("DROP FUNCTION IF EXISTS public.sps_proteger_borrador_intento_fn();")

    op.execute("DROP TRIGGER IF EXISTS trg_verificacion_primer_ingreso_guard ON public.verificacion_primer_ingreso;")
    op.execute("DROP FUNCTION IF EXISTS public.sps_validar_verificacion_primer_ingreso_fn();")

    op.execute("DROP TRIGGER IF EXISTS trg_usuario_integridad ON public.usuario;")
    op.execute("DROP FUNCTION IF EXISTS public.sps_validar_usuario_fn();")
