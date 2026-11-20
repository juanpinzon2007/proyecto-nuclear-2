"""Verifica, corrige y amplía la cobertura global de vistas y disparadores de trazabilidad en PostgreSQL.

Revision ID: 20261120_global_traceability
Revises: 20261119_password_recovery
Create Date: 2026-11-20 13:35:00.000000
"""

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql


revision = "20261120_global_traceability"
down_revision = "20261119_password_recovery"
branch_labels = None
depends_on = None


def upgrade():
    if op.get_bind().dialect.name != "postgresql":
        return

    # 1. Bitácora central e inmutable de trazabilidad global
    op.create_table(
        "auditoria_trazabilidad_global",
        sa.Column("id_evento", sa.BigInteger(), primary_key=True, autoincrement=True),
        sa.Column("modulo", sa.String(length=30), nullable=False),
        sa.Column("tabla_origen", sa.String(length=64), nullable=False),
        sa.Column("operacion", sa.String(length=10), nullable=False),
        sa.Column("registro_id", sa.Text(), nullable=False),
        sa.Column("usuario_id", sa.Integer(), nullable=True),
        sa.Column("sesion_id", sa.Uuid(), nullable=True),
        sa.Column("convocatoria_id", sa.Uuid(), nullable=True),
        sa.Column("version_caso_id", sa.Uuid(), nullable=True),
        sa.Column("intento_id", sa.Integer(), nullable=True),
        sa.Column("resumen", sa.Text(), nullable=False),
        sa.Column("datos_anteriores", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("datos_nuevos", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.Column("tx_id", sa.BigInteger(), nullable=False, server_default=sa.text("txid_current()")),
        sa.Column("registrado_en", sa.DateTime(timezone=True), nullable=False, server_default=sa.text("clock_timestamp()")),
        sa.CheckConstraint("operacion IN ('INSERT', 'UPDATE', 'DELETE')", name="ck_auditoria_global_operacion"),
    )
    op.create_index("ix_auditoria_global_fecha", "auditoria_trazabilidad_global", ["registrado_en"])
    op.create_index("ix_auditoria_global_modulo_tabla", "auditoria_trazabilidad_global", ["modulo", "tabla_origen"])
    op.create_index("ix_auditoria_global_usuario", "auditoria_trazabilidad_global", ["usuario_id"])
    op.create_index("ix_auditoria_global_sesion", "auditoria_trazabilidad_global", ["sesion_id"])
    op.create_index("ix_auditoria_global_convocatoria", "auditoria_trazabilidad_global", ["convocatoria_id"])
    op.create_index("ix_auditoria_global_intento", "auditoria_trazabilidad_global", ["intento_id"])

    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.sps_auditoria_global_inmutable_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            RAISE EXCEPTION 'La bitácora global de trazabilidad es inmutable y solo admite inserciones.'
                USING ERRCODE = '23514';
        END;
        $function$;

        CREATE TRIGGER trg_auditoria_trazabilidad_inmutable
        BEFORE UPDATE OR DELETE ON public.auditoria_trazabilidad_global
        FOR EACH ROW
        EXECUTE FUNCTION public.sps_auditoria_global_inmutable_fn();

        CREATE TRIGGER trg_auditoria_trazabilidad_no_truncar
        BEFORE TRUNCATE ON public.auditoria_trazabilidad_global
        FOR EACH STATEMENT
        EXECUTE FUNCTION public.sps_auditoria_global_inmutable_fn();
        """
    )

    # 2. Refuerzo de buenas prácticas e integridad en funciones existentes (SECURITY INVOKER + search_path)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.sps_validar_usuario_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            rol_nuevo text;
        BEGIN
            NEW.nombre := btrim(NEW.nombre);
            NEW.correo := btrim(NEW.correo);
            IF NEW.nombre IS NULL OR length(NEW.nombre) < 2 THEN
                RAISE EXCEPTION 'El nombre del usuario debe tener al menos 2 caracteres.'
                    USING ERRCODE = '23514';
            END IF;
            IF NEW.correo IS NULL OR NEW.correo = '' OR position('@' in NEW.correo) <= 1 OR position(' ' in NEW.correo) > 0 THEN
                RAISE EXCEPTION 'El correo institucional del usuario no es válido.'
                    USING ERRCODE = '23514';
            END IF;
            IF NEW.clave_hash IS NULL OR length(btrim(NEW.clave_hash)) = 0 THEN
                RAISE EXCEPTION 'La cuenta requiere clave_hash no vacía.'
                    USING ERRCODE = '23514';
            END IF;
            IF TG_OP = 'UPDATE' AND NEW.id_rol IS DISTINCT FROM OLD.id_rol THEN
                SELECT upper(btrim(r.nombre)) INTO rol_nuevo FROM public.rol r WHERE r.id_rol = NEW.id_rol;
                IF rol_nuevo IS DISTINCT FROM 'ESTUDIANTE'
                   AND EXISTS (SELECT 1 FROM public.verificacion_primer_ingreso v WHERE v.id_usuario = NEW.id_usuario) THEN
                    RAISE EXCEPTION 'No se puede cambiar a rol no estudiantil una cuenta con registro de primer ingreso.'
                        USING ERRCODE = '23514';
                END IF;
            END IF;
            RETURN NEW;
        END;
        $function$;

        CREATE OR REPLACE FUNCTION public.sps_validar_verificacion_primer_ingreso_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            rol_nombre text;
        BEGIN
            SELECT upper(btrim(r.nombre))
            INTO rol_nombre
            FROM public.usuario u
            JOIN public.rol r ON r.id_rol = u.id_rol
            WHERE u.id_usuario = NEW.id_usuario
            FOR SHARE OF u;

            IF rol_nombre IS NULL OR rol_nombre <> 'ESTUDIANTE' THEN
                RAISE EXCEPTION 'La verificación de primer ingreso solo aplica a cuentas con rol ESTUDIANTE.'
                    USING ERRCODE = '23514';
            END IF;

            IF NEW.intentos < 0 THEN
                RAISE EXCEPTION 'El contador de intentos OTP no puede ser negativo.'
                    USING ERRCODE = '23514';
            END IF;

            IF TG_OP = 'UPDATE' AND OLD.verificado AND NOT NEW.verificado THEN
                RAISE EXCEPTION 'La verificación única de primer ingreso es irreversible.'
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

        CREATE OR REPLACE FUNCTION public.sps_proteger_borrador_intento_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            objetivo_intento integer;
            estado_actual text;
        BEGIN
            objetivo_intento := CASE WHEN TG_OP = 'DELETE' THEN OLD.id_intento ELSE NEW.id_intento END;
            SELECT estado INTO estado_actual
            FROM public.intento
            WHERE id_intento = objetivo_intento;

            IF estado_actual IS NULL THEN
                RAISE EXCEPTION 'Intento asociado inexistente para el borrador.'
                    USING ERRCODE = '23514';
            END IF;

            IF estado_actual <> 'EN_CURSO' THEN
                RAISE EXCEPTION 'No se pueden % borradores de un intento en estado %.',
                    CASE TG_OP WHEN 'DELETE' THEN 'eliminar' ELSE 'modificar' END,
                    estado_actual
                    USING ERRCODE = '23514';
            END IF;

            IF TG_OP = 'DELETE' THEN
                RETURN OLD;
            END IF;

            IF NEW.actualizado_en IS NULL THEN
                NEW.actualizado_en := now();
            END IF;

            RETURN NEW;
        END;
        $function$;

        DROP TRIGGER IF EXISTS trg_borrador_decision_intento_guard ON public.borrador_decision_intento;
        CREATE TRIGGER trg_borrador_decision_intento_guard
        BEFORE INSERT OR UPDATE OR DELETE ON public.borrador_decision_intento
        FOR EACH ROW
        EXECUTE FUNCTION public.sps_proteger_borrador_intento_fn();

        CREATE TRIGGER trg_borrador_decision_no_truncar
        BEFORE TRUNCATE ON public.borrador_decision_intento
        FOR EACH STATEMENT
        EXECUTE FUNCTION public.sps_auditoria_global_inmutable_fn();

        CREATE OR REPLACE FUNCTION public.sps_validar_recuperacion_contrasena_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            IF NEW.intentos < 0 THEN
                RAISE EXCEPTION 'El contador de intentos de recuperación no puede ser negativo.'
                    USING ERRCODE = '23514';
            END IF;
            IF NEW.intentos >= 5 THEN
                NEW.codigo_hash := NULL;
                NEW.expira_en := NULL;
            END IF;
            RETURN NEW;
        END;
        $function$;
        """
    )

    # 3. Nuevos disparadores de integridad e inmutabilidad en tablas críticas descubiertas sin protección
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.sps_proteger_historial_cambio_decision_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            estado_actual text;
        BEGIN
            IF TG_OP IN ('UPDATE', 'DELETE') THEN
                RAISE EXCEPTION 'RF10: el historial de cambios de decisión es inmutable y no puede alterarse ni eliminarse.'
                    USING ERRCODE = '23514';
            END IF;
            SELECT estado INTO estado_actual FROM public.intento WHERE id_intento = NEW.id_intento;
            IF estado_actual IS NULL OR estado_actual <> 'EN_CURSO' THEN
                RAISE EXCEPTION 'RF10: no se pueden registrar cambios de decisión para un intento en estado %.',
                    COALESCE(estado_actual, 'INEXISTENTE')
                    USING ERRCODE = '23514';
            END IF;
            IF NEW.cambiado_en IS NULL THEN
                NEW.cambiado_en := now();
            END IF;
            RETURN NEW;
        END;
        $function$;

        CREATE TRIGGER trg_historial_cambio_decision_guard
        BEFORE INSERT OR UPDATE OR DELETE ON public.historial_cambio_decision
        FOR EACH ROW
        EXECUTE FUNCTION public.sps_proteger_historial_cambio_decision_fn();

        CREATE TRIGGER trg_historial_cambio_decision_no_truncar
        BEFORE TRUNCATE ON public.historial_cambio_decision
        FOR EACH STATEMENT
        EXECUTE FUNCTION public.sps_auditoria_global_inmutable_fn();

        CREATE OR REPLACE FUNCTION public.sps_proteger_despacho_correo_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            IF TG_OP = 'DELETE' THEN
                IF OLD.estado = 'ACEPTADO_PROVEEDOR' THEN
                    RAISE EXCEPTION 'El comprobante de correo aceptado por el proveedor no puede eliminarse.'
                        USING ERRCODE = '23514';
                END IF;
                RETURN OLD;
            END IF;

            IF OLD.estado IN ('ACEPTADO_PROVEEDOR', 'CANCELADO') AND NEW IS DISTINCT FROM OLD THEN
                RAISE EXCEPTION 'Un despacho de correo en estado terminal % es inmutable.', OLD.estado
                    USING ERRCODE = '23514';
            END IF;
            IF NEW.id_notificacion IS DISTINCT FROM OLD.id_notificacion THEN
                RAISE EXCEPTION 'La identidad del despacho de correo es inmutable.'
                    USING ERRCODE = '23514';
            END IF;
            IF OLD.estado <> 'PENDIENTE' AND NEW.payload_cifrado IS DISTINCT FROM OLD.payload_cifrado THEN
                RAISE EXCEPTION 'La carga cifrada del despacho solo puede auditarse tras su primer intento.'
                    USING ERRCODE = '23514';
            END IF;
            IF NEW.intentos < OLD.intentos THEN
                RAISE EXCEPTION 'El contador de intentos de despacho no puede decrecer.'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $function$;

        CREATE TRIGGER trg_despacho_correo_guard
        BEFORE UPDATE OR DELETE ON public.despacho_correo
        FOR EACH ROW
        EXECUTE FUNCTION public.sps_proteger_despacho_correo_fn();

        CREATE OR REPLACE FUNCTION public.sps_proteger_notificacion_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            IF (NEW.id, NEW.convocatoria_id, NEW.destinatario_id, NEW.tipo, NEW.canal, NEW.mensaje, NEW.creada_en)
               IS DISTINCT FROM
               (OLD.id, OLD.convocatoria_id, OLD.destinatario_id, OLD.tipo, OLD.canal, OLD.mensaje, OLD.creada_en) THEN
                RAISE EXCEPTION 'Los datos estructurales de la notificación son inmutables.'
                    USING ERRCODE = '23514';
            END IF;
            IF OLD.publicacion_evaluacion_id IS NOT NULL
               AND NEW.publicacion_evaluacion_id IS DISTINCT FROM OLD.publicacion_evaluacion_id THEN
                RAISE EXCEPTION 'La referencia de publicación oficial de la notificación es inmutable.'
                    USING ERRCODE = '23514';
            END IF;
            RETURN NEW;
        END;
        $function$;

        CREATE TRIGGER trg_notificacion_guard
        BEFORE UPDATE ON public.notificacion
        FOR EACH ROW
        EXECUTE FUNCTION public.sps_proteger_notificacion_fn();

        CREATE OR REPLACE FUNCTION public.sps_proteger_sesion_programada_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        BEGIN
            IF OLD.estado = 'FINALIZADO' THEN
                IF (
                    NEW.id, NEW.espacio_academico_id, NEW.version_caso_id, NEW.docente_id,
                    NEW.fecha_inicio, NEW.fecha_fin, NEW.tiempo_maximo_minutos,
                    NEW.lugar, NEW.mensaje_personalizado, NEW.estado, NEW.finalizado_en
                ) IS DISTINCT FROM (
                    OLD.id, OLD.espacio_academico_id, OLD.version_caso_id, OLD.docente_id,
                    OLD.fecha_inicio, OLD.fecha_fin, OLD.tiempo_maximo_minutos,
                    OLD.lugar, OLD.mensaje_personalizado, OLD.estado, OLD.finalizado_en
                ) THEN
                    RAISE EXCEPTION 'Una sesión FINALIZADA es inmutable salvo la visibilidad de resultados provisionales.'
                        USING ERRCODE = '23514';
                END IF;
            ELSIF NEW.estado = 'FINALIZADO' THEN
                NEW.finalizado_en := COALESCE(NEW.finalizado_en, now());
            END IF;
            RETURN NEW;
        END;
        $function$;

        CREATE TRIGGER trg_sesion_programada_guard
        BEFORE UPDATE ON public.sesion_programada
        FOR EACH ROW
        EXECUTE FUNCTION public.sps_proteger_sesion_programada_fn();
        """
    )

    # 4. Disparadores AFTER globales de trazabilidad (sin exponer secretos ni interferir en códigos SQLSTATE)
    op.execute(
        """
        CREATE OR REPLACE FUNCTION public.sps_auditar_identidad_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            v_uid integer;
            v_reg text;
            v_resumen text;
            v_antes jsonb := NULL;
            v_despues jsonb := NULL;
        BEGIN
            IF TG_OP = 'UPDATE' AND NEW IS NOT DISTINCT FROM OLD THEN
                RETURN NULL;
            END IF;

            IF TG_TABLE_NAME = 'usuario' THEN
                v_uid := COALESCE(NEW.id_usuario, OLD.id_usuario);
                v_reg := v_uid::text;
                IF TG_OP <> 'INSERT' THEN v_antes := to_jsonb(OLD) - 'clave_hash'; END IF;
                IF TG_OP <> 'DELETE' THEN
                    v_despues := (to_jsonb(NEW) - 'clave_hash') || jsonb_build_object(
                        'clave_actualizada', TG_OP = 'UPDATE' AND NEW.clave_hash IS DISTINCT FROM OLD.clave_hash
                    );
                END IF;
                v_resumen := CASE TG_OP
                    WHEN 'INSERT' THEN format('Cuenta creada para %s (%s)', NEW.nombre, NEW.correo)
                    WHEN 'UPDATE' THEN format('Cuenta actualizada (%s): activo=%s', NEW.correo, NEW.activo)
                    ELSE format('Cuenta eliminada (%s)', OLD.correo)
                END;

            ELSIF TG_TABLE_NAME = 'usuario_permiso' THEN
                v_uid := COALESCE(NEW.id_usuario, OLD.id_usuario);
                v_reg := format('%s:%s', v_uid, COALESCE(NEW.id_permiso, OLD.id_permiso));
                IF TG_OP <> 'INSERT' THEN v_antes := to_jsonb(OLD); END IF;
                IF TG_OP <> 'DELETE' THEN v_despues := to_jsonb(NEW); END IF;
                v_resumen := CASE TG_OP
                    WHEN 'DELETE' THEN format('Permiso individual #%s retirado del usuario #%s', OLD.id_permiso, OLD.id_usuario)
                    ELSE format('Permiso individual #%s %s para usuario #%s', NEW.id_permiso,
                        CASE WHEN NEW.concedido THEN 'concedido' ELSE 'revocado' END, NEW.id_usuario)
                END;

            ELSIF TG_TABLE_NAME = 'rol_permiso' THEN
                v_reg := format('%s:%s', COALESCE(NEW.id_rol, OLD.id_rol), COALESCE(NEW.id_permiso, OLD.id_permiso));
                IF TG_OP <> 'INSERT' THEN v_antes := to_jsonb(OLD); END IF;
                IF TG_OP <> 'DELETE' THEN v_despues := to_jsonb(NEW); END IF;
                v_resumen := format('%s de permiso #%s sobre rol #%s', TG_OP,
                    COALESCE(NEW.id_permiso, OLD.id_permiso), COALESCE(NEW.id_rol, OLD.id_rol));

            ELSIF TG_TABLE_NAME = 'verificacion_primer_ingreso' THEN
                v_uid := COALESCE(NEW.id_usuario, OLD.id_usuario);
                v_reg := COALESCE(NEW.id, OLD.id)::text;
                IF TG_OP <> 'INSERT' THEN v_antes := to_jsonb(OLD) - 'codigo_hash'; END IF;
                IF TG_OP <> 'DELETE' THEN v_despues := to_jsonb(NEW) - 'codigo_hash'; END IF;
                v_resumen := CASE
                    WHEN TG_OP = 'INSERT' THEN format('Estado primer ingreso creado para usuario #%s (verificado=%s)', NEW.id_usuario, NEW.verificado)
                    WHEN TG_OP = 'UPDATE' AND NOT OLD.verificado AND NEW.verificado THEN format('Primer ingreso verificado para usuario #%s', NEW.id_usuario)
                    WHEN TG_OP = 'UPDATE' THEN format('Actualización OTP primer ingreso usuario #%s (intentos=%s)', NEW.id_usuario, NEW.intentos)
                    ELSE format('Eliminado estado primer ingreso de usuario #%s', OLD.id_usuario)
                END;

            ELSIF TG_TABLE_NAME = 'recuperacion_contrasena' THEN
                v_uid := COALESCE(NEW.id_usuario, OLD.id_usuario);
                v_reg := COALESCE(NEW.id, OLD.id)::text;
                IF TG_OP <> 'INSERT' THEN v_antes := to_jsonb(OLD) - 'codigo_hash'; END IF;
                IF TG_OP <> 'DELETE' THEN v_despues := to_jsonb(NEW) - 'codigo_hash'; END IF;
                v_resumen := CASE
                    WHEN TG_OP = 'DELETE' THEN format('Registro de recuperación eliminado usuario #%s', OLD.id_usuario)
                    WHEN TG_OP = 'UPDATE' AND NEW.completado_en IS DISTINCT FROM OLD.completado_en THEN format('Recuperación de contraseña completada usuario #%s', NEW.id_usuario)
                    ELSE format('Gestión OTP recuperación contraseña usuario #%s (intentos=%s)', NEW.id_usuario, NEW.intentos)
                END;

            ELSIF TG_TABLE_NAME = 'identidad_academica' THEN
                v_uid := COALESCE(NEW.id_usuario, OLD.id_usuario);
                v_reg := format('%s:%s', COALESCE(NEW.sistema, OLD.sistema), COALESCE(NEW.id_academico, OLD.id_academico));
                IF TG_OP <> 'INSERT' THEN v_antes := to_jsonb(OLD); END IF;
                IF TG_OP <> 'DELETE' THEN v_despues := to_jsonb(NEW); END IF;
                v_resumen := format('%s vínculo académico %s para usuario #%s', TG_OP, COALESCE(NEW.sistema, OLD.sistema), v_uid);
            END IF;

            INSERT INTO public.auditoria_trazabilidad_global(
                modulo, tabla_origen, operacion, registro_id, usuario_id, resumen, datos_anteriores, datos_nuevos
            ) VALUES (
                'IDENTITY', TG_TABLE_NAME, TG_OP, v_reg, v_uid, v_resumen, v_antes, v_despues
            );
            RETURN NULL;
        END;
        $function$;

        CREATE OR REPLACE FUNCTION public.sps_auditar_academico_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            v_uid integer := NULL;
            v_reg text;
            v_resumen text;
        BEGIN
            IF TG_OP = 'UPDATE' AND NEW IS NOT DISTINCT FROM OLD THEN
                RETURN NULL;
            END IF;

            IF TG_TABLE_NAME = 'espacio_academico' THEN
                v_reg := COALESCE(NEW.id, OLD.id)::text;
                v_resumen := format('%s espacio académico "%s"', TG_OP, COALESCE(NEW.nombre, OLD.nombre));
            ELSIF TG_TABLE_NAME = 'docente_espacio_academico' THEN
                v_uid := COALESCE(NEW.id_docente, OLD.id_docente);
                v_reg := format('%s:%s', v_uid, COALESCE(NEW.espacio_academico_id, OLD.espacio_academico_id));
                v_resumen := format('%s autorización docente #%s en espacio %s', TG_OP, v_uid, COALESCE(NEW.espacio_academico_id, OLD.espacio_academico_id));
            ELSIF TG_TABLE_NAME = 'grupo_academico' THEN
                v_uid := COALESCE(NEW.id_profesor, OLD.id_profesor);
                v_reg := COALESCE(NEW.id_grupo, OLD.id_grupo)::text;
                v_resumen := format('%s grupo "%s" (%s) por profesor #%s', TG_OP, COALESCE(NEW.nombre, OLD.nombre), COALESCE(NEW.periodo, OLD.periodo), v_uid);
            ELSIF TG_TABLE_NAME = 'grupo_estudiante' THEN
                v_uid := COALESCE(NEW.id_estudiante, OLD.id_estudiante);
                v_reg := COALESCE(NEW.id_grupo_estudiante, OLD.id_grupo_estudiante)::text;
                v_resumen := CASE
                    WHEN TG_OP = 'INSERT' THEN format('Estudiante #%s matriculado en grupo #%s', NEW.id_estudiante, NEW.id_grupo)
                    WHEN TG_OP = 'UPDATE' THEN format('Matrícula estudiante #%s en grupo #%s actualizada (activo=%s)', NEW.id_estudiante, NEW.id_grupo, NEW.activo)
                    ELSE format('Matrícula #%s eliminada (estudiante #%s, grupo #%s)', OLD.id_grupo_estudiante, OLD.id_estudiante, OLD.id_grupo)
                END;
            END IF;

            INSERT INTO public.auditoria_trazabilidad_global(
                modulo, tabla_origen, operacion, registro_id, usuario_id, resumen, datos_anteriores, datos_nuevos
            ) VALUES (
                'ACADEMICO', TG_TABLE_NAME, TG_OP, v_reg, v_uid, v_resumen,
                CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD) END,
                CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW) END
            );
            RETURN NULL;
        END;
        $function$;

        CREATE OR REPLACE FUNCTION public.sps_auditar_casos_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            v_uid integer := NULL;
            v_vid uuid := NULL;
            v_docente_uuid uuid := NULL;
            v_reg text;
            v_resumen text;
        BEGIN
            IF TG_OP = 'UPDATE' AND NEW IS NOT DISTINCT FROM OLD THEN
                RETURN NULL;
            END IF;

            IF TG_TABLE_NAME = 'caso' THEN
                v_reg := COALESCE(NEW.id, OLD.id)::text;
                v_docente_uuid := COALESCE(NEW.docente_creador_id, OLD.docente_creador_id);
                v_resumen := format('%s caso %s', TG_OP, v_reg);
            ELSIF TG_TABLE_NAME = 'version_caso' THEN
                v_vid := COALESCE(NEW.id, OLD.id);
                v_reg := v_vid::text;
                SELECT c.docente_creador_id INTO v_docente_uuid FROM public.caso c WHERE c.id = COALESCE(NEW.caso_id, OLD.caso_id);
                v_resumen := CASE
                    WHEN TG_OP = 'INSERT' THEN format('Versión v%s de caso "%s" creada en %s', NEW.numero, NEW.nombre, NEW.estado)
                    WHEN TG_OP = 'UPDATE' AND OLD.estado IS DISTINCT FROM NEW.estado THEN format('Caso "%s" v%s cambió estado %s -> %s', NEW.nombre, NEW.numero, OLD.estado, NEW.estado)
                    WHEN TG_OP = 'UPDATE' THEN format('Borrador "%s" v%s actualizado', NEW.nombre, NEW.numero)
                    ELSE format('Versión "%s" v%s eliminada', OLD.nombre, OLD.numero)
                END;
            ELSIF TG_TABLE_NAME = 'rubrica' THEN
                v_vid := COALESCE(NEW.version_caso_id, OLD.version_caso_id);
                v_reg := COALESCE(NEW.id, OLD.id)::text;
                SELECT c.docente_creador_id INTO v_docente_uuid
                FROM public.version_caso vc JOIN public.caso c ON c.id = vc.caso_id
                WHERE vc.id = v_vid;
                v_resumen := format('%s rúbrica "%s" (%s) en versión %s', TG_OP, COALESCE(NEW.nombre, OLD.nombre), COALESCE(NEW.version_regla, OLD.version_regla), v_vid);
            END IF;

            IF v_docente_uuid IS NOT NULL THEN
                SELECT id_usuario INTO v_uid FROM public.identidad_academica
                WHERE sistema = 'CASES' AND id_academico = v_docente_uuid LIMIT 1;
            END IF;

            INSERT INTO public.auditoria_trazabilidad_global(
                modulo, tabla_origen, operacion, registro_id, usuario_id, version_caso_id, resumen, datos_anteriores, datos_nuevos
            ) VALUES (
                'CASES', TG_TABLE_NAME, TG_OP, v_reg, v_uid, v_vid, v_resumen,
                CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD) END,
                CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW) END
            );
            RETURN NULL;
        END;
        $function$;

        CREATE OR REPLACE FUNCTION public.sps_auditar_programacion_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            v_modulo text := 'SCHEDULING';
            v_uid integer := NULL;
            v_sid uuid := NULL;
            v_cid uuid := NULL;
            v_vid uuid := NULL;
            v_sched_uuid uuid := NULL;
            v_reg text;
            v_resumen text;
            v_antes jsonb := NULL;
            v_despues jsonb := NULL;
        BEGIN
            IF TG_OP = 'UPDATE' AND NEW IS NOT DISTINCT FROM OLD THEN
                RETURN NULL;
            END IF;

            IF TG_TABLE_NAME = 'sesion_programada' THEN
                v_sid := COALESCE(NEW.id, OLD.id);
                v_vid := COALESCE(NEW.version_caso_id, OLD.version_caso_id);
                v_sched_uuid := COALESCE(NEW.docente_id, OLD.docente_id);
                v_reg := v_sid::text;
                v_resumen := CASE
                    WHEN TG_OP = 'INSERT' THEN format('Sesión %s programada (%s)', NEW.id, NEW.estado)
                    WHEN TG_OP = 'UPDATE' AND OLD.estado IS DISTINCT FROM NEW.estado THEN format('Sesión %s cambió estado %s -> %s', NEW.id, OLD.estado, NEW.estado)
                    WHEN TG_OP = 'UPDATE' AND OLD.mostrar_resultados_provisionales IS DISTINCT FROM NEW.mostrar_resultados_provisionales THEN format('Sesión %s visibilidad provisional -> %s', NEW.id, NEW.mostrar_resultados_provisionales)
                    ELSE format('%s sesión programada %s', TG_OP, v_sid)
                END;

            ELSIF TG_TABLE_NAME = 'asignacion_caso' THEN
                v_sid := COALESCE(NEW.sesion_programada_id, OLD.sesion_programada_id);
                v_vid := COALESCE(NEW.version_caso_id, OLD.version_caso_id);
                v_reg := COALESCE(NEW.id_asignacion, OLD.id_asignacion)::text;
                v_antes := CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD) - 'codigo_acceso_hash' END;
                v_despues := CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW) - 'codigo_acceso_hash' END;
                v_resumen := format('%s asignación de grupo #%s a sesión %s', TG_OP, COALESCE(NEW.id_grupo, OLD.id_grupo), v_sid);

            ELSIF TG_TABLE_NAME = 'convocatoria' THEN
                v_cid := COALESCE(NEW.id, OLD.id);
                v_sid := COALESCE(NEW.sesion_id, OLD.sesion_id);
                v_sched_uuid := COALESCE(NEW.estudiante_id, OLD.estudiante_id);
                v_reg := v_cid::text;
                v_antes := CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD) - 'codigo_hash' END;
                v_despues := CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW) - 'codigo_hash' END;
                v_resumen := CASE
                    WHEN TG_OP = 'INSERT' THEN format('Convocatoria %s emitida para sesión %s', NEW.id, NEW.sesion_id)
                    WHEN TG_OP = 'UPDATE' AND OLD.estado IS DISTINCT FROM NEW.estado THEN format('Convocatoria %s estado %s -> %s', NEW.id, OLD.estado, NEW.estado)
                    WHEN TG_OP = 'UPDATE' AND OLD.admision_evento_id IS NULL AND NEW.admision_evento_id IS NOT NULL THEN format('Convocatoria %s habilitada desde sala de espera', NEW.id)
                    WHEN TG_OP = 'UPDATE' AND OLD.espera_registrada_en IS NULL AND NEW.espera_registrada_en IS NOT NULL THEN format('Estudiante registrado en sala de espera convocatoria %s', NEW.id)
                    ELSE format('%s convocatoria %s', TG_OP, v_cid)
                END;

            ELSIF TG_TABLE_NAME = 'notificacion' THEN
                v_modulo := 'CORREOS';
                v_cid := COALESCE(NEW.convocatoria_id, OLD.convocatoria_id);
                v_sched_uuid := COALESCE(NEW.destinatario_id, OLD.destinatario_id);
                v_reg := COALESCE(NEW.id, OLD.id)::text;
                IF v_cid IS NOT NULL THEN
                    SELECT sesion_id INTO v_sid FROM public.convocatoria WHERE id = v_cid;
                END IF;
                v_resumen := format('%s notificación %s/%s (%s)', TG_OP, COALESCE(NEW.tipo, OLD.tipo), COALESCE(NEW.canal, OLD.canal), COALESCE(NEW.estado, OLD.estado));

            ELSIF TG_TABLE_NAME = 'despacho_correo' THEN
                v_modulo := 'CORREOS';
                v_reg := COALESCE(NEW.id_notificacion, OLD.id_notificacion)::text;
                SELECT n.convocatoria_id, n.destinatario_id INTO v_cid, v_sched_uuid
                FROM public.notificacion n WHERE n.id = COALESCE(NEW.id_notificacion, OLD.id_notificacion);
                IF v_cid IS NOT NULL THEN
                    SELECT sesion_id INTO v_sid FROM public.convocatoria WHERE id = v_cid;
                END IF;
                v_antes := CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD) - 'payload_cifrado' END;
                v_despues := CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW) - 'payload_cifrado' END;
                v_resumen := format('%s despacho SMTP %s: %s (intentos=%s)', TG_OP, v_reg, COALESCE(NEW.estado, OLD.estado), COALESCE(NEW.intentos, OLD.intentos));
            END IF;

            IF v_sched_uuid IS NOT NULL THEN
                SELECT id_usuario INTO v_uid FROM public.identidad_academica
                WHERE sistema = 'SCHEDULING' AND id_academico = v_sched_uuid LIMIT 1;
            END IF;

            INSERT INTO public.auditoria_trazabilidad_global(
                modulo, tabla_origen, operacion, registro_id, usuario_id, sesion_id, convocatoria_id, version_caso_id, resumen, datos_anteriores, datos_nuevos
            ) VALUES (
                v_modulo, TG_TABLE_NAME, TG_OP, v_reg, v_uid, v_sid, v_cid, v_vid, v_resumen,
                COALESCE(v_antes, CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD) END),
                COALESCE(v_despues, CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW) END)
            );
            RETURN NULL;
        END;
        $function$;

        CREATE OR REPLACE FUNCTION public.sps_auditar_participacion_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            v_uid integer := NULL;
            v_sid uuid := NULL;
            v_cid uuid := NULL;
            v_vid uuid := NULL;
            v_iid integer := NULL;
            v_pid integer := NULL;
            v_reg text;
            v_resumen text;
        BEGIN
            IF TG_OP = 'UPDATE' AND NEW IS NOT DISTINCT FROM OLD THEN
                RETURN NULL;
            END IF;

            IF TG_TABLE_NAME = 'consentimiento' THEN
                v_uid := COALESCE(NEW.id_estudiante, OLD.id_estudiante);
                v_reg := COALESCE(NEW.id_consentimiento, OLD.id_consentimiento)::text;
                v_resumen := format('%s consentimiento #%s (versión "%s") estudiante #%s', TG_OP, v_reg, COALESCE(NEW.version_texto, OLD.version_texto), v_uid);

            ELSIF TG_TABLE_NAME = 'participacion' THEN
                v_pid := COALESCE(NEW.id_participacion, OLD.id_participacion);
                v_cid := COALESCE(NEW.convocatoria_id, OLD.convocatoria_id);
                v_reg := v_pid::text;
                SELECT ge.id_estudiante INTO v_uid FROM public.grupo_estudiante ge WHERE ge.id_grupo_estudiante = COALESCE(NEW.id_grupo_estudiante, OLD.id_grupo_estudiante);
                SELECT c.sesion_id, sp.version_caso_id INTO v_sid, v_vid
                FROM public.convocatoria c JOIN public.sesion_programada sp ON sp.id = c.sesion_id
                WHERE c.id = v_cid;
                v_resumen := CASE
                    WHEN TG_OP = 'INSERT' THEN format('Participación #%s iniciada (estado=%s)', v_pid, NEW.estado)
                    WHEN TG_OP = 'UPDATE' THEN format('Participación #%s estado %s -> %s', v_pid, OLD.estado, NEW.estado)
                    ELSE format('Participación #%s eliminada', v_pid)
                END;

            ELSIF TG_TABLE_NAME = 'permiso_intento_extra' THEN
                v_uid := COALESCE(NEW.id_profesor, OLD.id_profesor);
                v_pid := COALESCE(NEW.id_participacion, OLD.id_participacion);
                v_reg := COALESCE(NEW.id_permiso_extra, OLD.id_permiso_extra)::text;
                SELECT p.convocatoria_id, c.sesion_id INTO v_cid, v_sid
                FROM public.participacion p JOIN public.convocatoria c ON c.id = p.convocatoria_id
                WHERE p.id_participacion = v_pid;
                v_resumen := format('Permiso intento extra #%s autorizado para participación #%s por docente #%s', v_reg, v_pid, v_uid);

            ELSIF TG_TABLE_NAME = 'intento' THEN
                v_iid := COALESCE(NEW.id_intento, OLD.id_intento);
                v_pid := COALESCE(NEW.id_participacion, OLD.id_participacion);
                v_reg := v_iid::text;
                SELECT p.convocatoria_id, ge.id_estudiante, c.sesion_id, sp.version_caso_id
                INTO v_cid, v_uid, v_sid, v_vid
                FROM public.participacion p
                JOIN public.grupo_estudiante ge ON ge.id_grupo_estudiante = p.id_grupo_estudiante
                JOIN public.convocatoria c ON c.id = p.convocatoria_id
                JOIN public.sesion_programada sp ON sp.id = c.sesion_id
                WHERE p.id_participacion = v_pid;
                v_resumen := CASE
                    WHEN TG_OP = 'INSERT' THEN format('Intento #%s (nro %s) abierto en participación #%s', v_iid, NEW.numero_intento, v_pid)
                    WHEN TG_OP = 'UPDATE' AND OLD.estado IS DISTINCT FROM NEW.estado THEN format('Intento #%s cerrado %s -> %s', v_iid, OLD.estado, NEW.estado)
                    ELSE format('%s intento #%s', TG_OP, v_iid)
                END;

            ELSIF TG_TABLE_NAME = 'historial_cambio_decision' THEN
                v_iid := COALESCE(NEW.id_intento, OLD.id_intento);
                v_reg := COALESCE(NEW.id_historial, OLD.id_historial)::text;
                SELECT p.convocatoria_id, ge.id_estudiante, c.sesion_id, sp.version_caso_id
                INTO v_cid, v_uid, v_sid, v_vid
                FROM public.intento i
                JOIN public.participacion p ON p.id_participacion = i.id_participacion
                JOIN public.grupo_estudiante ge ON ge.id_grupo_estudiante = p.id_grupo_estudiante
                JOIN public.convocatoria c ON c.id = p.convocatoria_id
                JOIN public.sesion_programada sp ON sp.id = c.sesion_id
                WHERE i.id_intento = v_iid;
                v_resumen := CASE
                    WHEN NEW.id_opcion_anterior IS NULL THEN format('Selección inicial de pregunta %s en intento #%s', NEW.id_decision, v_iid)
                    ELSE format('Cambio de decisión pregunta %s (%s -> %s) en intento #%s', NEW.id_decision, NEW.id_opcion_anterior, NEW.id_opcion_nueva, v_iid)
                END;

            ELSIF TG_TABLE_NAME = 'paso_simulacion' THEN
                v_iid := COALESCE(NEW.id_intento, OLD.id_intento);
                v_reg := COALESCE(NEW.id_paso, OLD.id_paso)::text;
                SELECT p.convocatoria_id, ge.id_estudiante, c.sesion_id, sp.version_caso_id
                INTO v_cid, v_uid, v_sid, v_vid
                FROM public.intento i
                JOIN public.participacion p ON p.id_participacion = i.id_participacion
                JOIN public.grupo_estudiante ge ON ge.id_grupo_estudiante = p.id_grupo_estudiante
                JOIN public.convocatoria c ON c.id = p.convocatoria_id
                JOIN public.sesion_programada sp ON sp.id = c.sesion_id
                WHERE i.id_intento = v_iid;
                v_resumen := format('Paso #%s congelado en intento #%s (pregunta %s)', COALESCE(NEW.numero_paso, OLD.numero_paso), v_iid, COALESCE(NEW.id_decision, OLD.id_decision));
            END IF;

            INSERT INTO public.auditoria_trazabilidad_global(
                modulo, tabla_origen, operacion, registro_id, usuario_id, sesion_id, convocatoria_id, version_caso_id, intento_id, resumen, datos_anteriores, datos_nuevos
            ) VALUES (
                'PARTICIPATION', TG_TABLE_NAME, TG_OP, v_reg, v_uid, v_sid, v_cid, v_vid, v_iid, v_resumen,
                CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD) END,
                CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW) END
            );
            RETURN NULL;
        END;
        $function$;

        CREATE OR REPLACE FUNCTION public.sps_auditar_evaluacion_fn()
        RETURNS trigger
        LANGUAGE plpgsql
        SECURITY INVOKER
        SET search_path = pg_catalog, public
        AS $function$
        DECLARE
            v_uid integer := NULL;
            v_sid uuid := NULL;
            v_cid uuid := NULL;
            v_vid uuid := NULL;
            v_iid integer := NULL;
            v_reg text;
            v_resumen text;
            v_antes jsonb := NULL;
            v_despues jsonb := NULL;
        BEGIN
            IF TG_OP = 'UPDATE' AND NEW IS NOT DISTINCT FROM OLD THEN
                RETURN NULL;
            END IF;

            IF TG_TABLE_NAME = 'resultado_intento' THEN
                v_iid := COALESCE(NEW.id_intento, OLD.id_intento);
                v_vid := COALESCE(NEW.version_caso_id, OLD.version_caso_id);
                v_reg := COALESCE(NEW.id_resultado, OLD.id_resultado)::text;
                SELECT p.convocatoria_id, ge.id_estudiante, c.sesion_id INTO v_cid, v_uid, v_sid
                FROM public.intento i
                JOIN public.participacion p ON p.id_participacion = i.id_participacion
                JOIN public.grupo_estudiante ge ON ge.id_grupo_estudiante = p.id_grupo_estudiante
                JOIN public.convocatoria c ON c.id = p.convocatoria_id
                WHERE i.id_intento = v_iid;
                v_antes := CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD) - 'procedencia' END;
                v_despues := CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW) - 'procedencia' END;
                v_resumen := format('Resultado provisional emitido para intento #%s: nota=%s (%s/%s)', v_iid, NEW.nota_final, NEW.modalidad, NEW.ambito);

            ELSIF TG_TABLE_NAME = 'publicacion_evaluacion' THEN
                v_sid := COALESCE(NEW.sesion_id, OLD.sesion_id);
                v_uid := COALESCE(NEW.id_profesor, OLD.id_profesor);
                v_reg := COALESCE(NEW.id, OLD.id)::text;
                v_antes := CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD) - 'fuente_documento' END;
                v_despues := CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW) - 'fuente_documento' END;
                v_resumen := format('Publicación oficial v%s emitida en sesión %s por profesor #%s', NEW.version, v_sid, v_uid);

            ELSIF TG_TABLE_NAME = 'resultado_participacion' THEN
                v_cid := COALESCE(NEW.convocatoria_id, OLD.convocatoria_id);
                v_uid := COALESCE(NEW.id_estudiante, OLD.id_estudiante);
                v_reg := COALESCE(NEW.id_resultado_participacion, OLD.id_resultado_participacion)::text;
                SELECT sesion_id INTO v_sid FROM public.convocatoria WHERE id = v_cid;
                v_antes := CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD) - 'detalle' END;
                v_despues := CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW) - 'detalle' END;
                v_resumen := format('Resultado oficial estudiante #%s: nota=%s (%s)', v_uid, NEW.nota_definitiva, NEW.situacion);

            ELSIF TG_TABLE_NAME = 'ausencia_academica' THEN
                v_cid := COALESCE(NEW.convocatoria_id, OLD.convocatoria_id);
                v_sid := COALESCE(NEW.sesion_id, OLD.sesion_id);
                v_vid := COALESCE(NEW.version_caso_id, OLD.version_caso_id);
                v_uid := COALESCE(NEW.id_estudiante, OLD.id_estudiante);
                v_reg := COALESCE(NEW.id, OLD.id)::text;
                v_resumen := format('Ausencia académica rev.%s (%s) estudiante #%s', NEW.revision, CASE WHEN NEW.confirmada THEN 'CONFIRMADA' ELSE 'RECTIFICADA' END, v_uid);

            ELSIF TG_TABLE_NAME = 'retroalimentacion_docente' THEN
                v_reg := COALESCE(NEW.id_retroalimentacion, OLD.id_retroalimentacion)::text;
                SELECT p.convocatoria_id, ge.id_estudiante, c.sesion_id INTO v_cid, v_uid, v_sid
                FROM public.participacion p
                JOIN public.grupo_estudiante ge ON ge.id_grupo_estudiante = p.id_grupo_estudiante
                JOIN public.convocatoria c ON c.id = p.convocatoria_id
                WHERE p.id_participacion = COALESCE(NEW.id_participacion, OLD.id_participacion);
                v_resumen := format('%s retroalimentación docente en participación #%s', TG_OP, COALESCE(NEW.id_participacion, OLD.id_participacion));
            END IF;

            INSERT INTO public.auditoria_trazabilidad_global(
                modulo, tabla_origen, operacion, registro_id, usuario_id, sesion_id, convocatoria_id, version_caso_id, intento_id, resumen, datos_anteriores, datos_nuevos
            ) VALUES (
                'EVALUACION', TG_TABLE_NAME, TG_OP, v_reg, v_uid, v_sid, v_cid, v_vid, v_iid, v_resumen,
                COALESCE(v_antes, CASE WHEN TG_OP <> 'INSERT' THEN to_jsonb(OLD) END),
                COALESCE(v_despues, CASE WHEN TG_OP <> 'DELETE' THEN to_jsonb(NEW) END)
            );
            RETURN NULL;
        END;
        $function$;
        """
    )

    # Adjuntar los disparadores AFTER globales de forma uniforme sin alterar lógica previa
    audit_bindings = [
        ("usuario", "sps_auditar_identidad_fn"),
        ("usuario_permiso", "sps_auditar_identidad_fn"),
        ("rol_permiso", "sps_auditar_identidad_fn"),
        ("verificacion_primer_ingreso", "sps_auditar_identidad_fn"),
        ("recuperacion_contrasena", "sps_auditar_identidad_fn"),
        ("identidad_academica", "sps_auditar_identidad_fn"),
        ("espacio_academico", "sps_auditar_academico_fn"),
        ("docente_espacio_academico", "sps_auditar_academico_fn"),
        ("grupo_academico", "sps_auditar_academico_fn"),
        ("grupo_estudiante", "sps_auditar_academico_fn"),
        ("caso", "sps_auditar_casos_fn"),
        ("version_caso", "sps_auditar_casos_fn"),
        ("rubrica", "sps_auditar_casos_fn"),
        ("sesion_programada", "sps_auditar_programacion_fn"),
        ("asignacion_caso", "sps_auditar_programacion_fn"),
        ("convocatoria", "sps_auditar_programacion_fn"),
        ("notificacion", "sps_auditar_programacion_fn"),
        ("despacho_correo", "sps_auditar_programacion_fn"),
        ("consentimiento", "sps_auditar_participacion_fn"),
        ("participacion", "sps_auditar_participacion_fn"),
        ("permiso_intento_extra", "sps_auditar_participacion_fn"),
        ("intento", "sps_auditar_participacion_fn"),
        ("historial_cambio_decision", "sps_auditar_participacion_fn"),
        ("paso_simulacion", "sps_auditar_participacion_fn"),
        ("resultado_intento", "sps_auditar_evaluacion_fn"),
        ("publicacion_evaluacion", "sps_auditar_evaluacion_fn"),
        ("resultado_participacion", "sps_auditar_evaluacion_fn"),
        ("ausencia_academica", "sps_auditar_evaluacion_fn"),
        ("retroalimentacion_docente", "sps_auditar_evaluacion_fn"),
    ]
    for tabla, fn in audit_bindings:
        op.execute(
            f"""
            CREATE TRIGGER trg_audit_{tabla}
            AFTER INSERT OR UPDATE OR DELETE ON public.{tabla}
            FOR EACH ROW
            EXECUTE FUNCTION public.{fn}();
            """
        )

    # 5. Actualizar las 4 vistas existentes (preservando sus columnas iniciales) y añadir 5 vistas globales
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
            c.creado_en,
            COUNT(DISTINCT o.id) AS total_opciones,
            COALESCE(BOOL_OR(e.es_inicial), FALSE) AS tiene_grafo_configurado,
            COUNT(DISTINCT sp.id) AS total_sesiones_programadas
        FROM public.caso c
        JOIN public.version_caso v ON v.caso_id = c.id
        LEFT JOIN public.identidad_academica ia
            ON ia.sistema = 'CASES' AND ia.id_academico = c.docente_creador_id
        LEFT JOIN public.usuario u ON u.id_usuario = ia.id_usuario
        LEFT JOIN public.escenario e ON e.version_caso_id = v.id
        LEFT JOIN public.pregunta p ON p.escenario_id = e.id
        LEFT JOIN public.opcion_respuesta o ON o.pregunta_id = p.id
        LEFT JOIN public.rubrica r ON r.version_caso_id = v.id
        LEFT JOIN public.sesion_programada sp ON sp.version_caso_id = v.id
        GROUP BY
            c.id, c.id_caso, v.id, v.numero, v.nombre, v.estado,
            v.tiempo_estimado_min, u.nombre, u.correo, r.id, r.nombre, r.version_regla, c.creado_en;

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
            COUNT(DISTINCT intn.id_intento) FILTER (WHERE intn.estado IN ('FINALIZADO', 'VENCIDO')) AS total_intentos_cerrados,
            sp.espacio_academico_id,
            sp.version_caso_id,
            sp.docente_id,
            COUNT(DISTINCT conv.id) FILTER (WHERE conv.estado = 'RETIRADA') AS total_convocatorias_retiradas,
            COUNT(DISTINCT conv.id) FILTER (WHERE conv.espera_registrada_en IS NOT NULL) AS total_en_espera,
            COUNT(DISTINCT aus.id) FILTER (WHERE aus.confirmada) AS total_ausencias,
            MAX(pe.version) AS ultima_version_publicada,
            sp.mostrar_resultados_provisionales
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
        LEFT JOIN LATERAL (
            SELECT a.*
            FROM public.ausencia_academica a
            WHERE a.convocatoria_id = conv.id
            ORDER BY a.revision DESC
            LIMIT 1
        ) aus ON TRUE
        LEFT JOIN public.publicacion_evaluacion pe ON pe.sesion_id = sp.id
        GROUP BY
            sp.id, sp.estado, ea.nombre, vc.nombre, vc.numero, ga.nombre, ga.periodo,
            ud.nombre, sp.fecha_inicio, sp.fecha_fin, sp.tiempo_maximo_minutos,
            sp.espacio_academico_id, sp.version_caso_id, sp.docente_id, sp.mostrar_resultados_provisionales;

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
            rd.texto AS retroalimentacion_docente,
            (part.id_consentimiento IS NOT NULL) AS consentimiento_aceptado,
            rp.version_publicacion AS version_publicacion_oficial,
            COALESCE(aus.confirmada, FALSE) AS ausencia_confirmada,
            aus.motivo AS ausencia_motivo
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
        LEFT JOIN LATERAL (
            SELECT r.*, pe.version AS version_publicacion
            FROM public.resultado_participacion r
            JOIN public.publicacion_evaluacion pe ON pe.id = r.publicacion_id
            WHERE r.convocatoria_id = conv.id
            ORDER BY pe.version DESC
            LIMIT 1
        ) rp ON TRUE
        LEFT JOIN LATERAL (
            SELECT f.*
            FROM public.retroalimentacion_docente f
            WHERE f.id_participacion = part.id_participacion
            ORDER BY f.fecha_registro DESC, f.id_retroalimentacion DESC
            LIMIT 1
        ) rd ON TRUE
        LEFT JOIN LATERAL (
            SELECT a.*
            FROM public.ausencia_academica a
            WHERE a.convocatoria_id = conv.id
            ORDER BY a.revision DESC
            LIMIT 1
        ) aus ON TRUE;

        CREATE OR REPLACE VIEW public.vw_auditoria_primer_ingreso AS
        SELECT
            u.id_usuario,
            u.nombre,
            u.correo,
            u.activo,
            upper(btrim(r.nombre)) AS rol,
            CASE
                WHEN upper(btrim(r.nombre)) <> 'ESTUDIANTE' THEN 'NO_APLICA'
                WHEN vpi.id IS NULL THEN 'VERIFICADO_LEGACY'
                WHEN vpi.verificado THEN 'VERIFICADO'
                ELSE 'PENDIENTE_PRIMER_INGRESO'
            END AS estado_primer_ingreso,
            vpi.verificado_en,
            COALESCE(vpi.intentos, 0) AS intentos_otp,
            vpi.expira_en,
            MAX(CASE WHEN ia.sistema = 'CASES' THEN ia.id_academico::text END) AS identidad_cases,
            MAX(CASE WHEN ia.sistema = 'SCHEDULING' THEN ia.id_academico::text END) AS identidad_scheduling,
            rc.solicitado_en AS recuperacion_solicitada_en,
            rc.completado_en AS recuperacion_completada_en,
            COALESCE(rc.intentos, 0) AS intentos_recuperacion,
            COUNT(DISTINCT up.id_permiso) AS total_permisos_individuales
        FROM public.usuario u
        JOIN public.rol r ON r.id_rol = u.id_rol
        LEFT JOIN public.verificacion_primer_ingreso vpi ON vpi.id_usuario = u.id_usuario
        LEFT JOIN public.identidad_academica ia ON ia.id_usuario = u.id_usuario
        LEFT JOIN public.recuperacion_contrasena rc ON rc.id_usuario = u.id_usuario
        LEFT JOIN public.usuario_permiso up ON up.id_usuario = u.id_usuario
        GROUP BY
            u.id_usuario, u.nombre, u.correo, u.activo, r.nombre,
            vpi.id, vpi.verificado, vpi.verificado_en, vpi.intentos, vpi.expira_en,
            rc.solicitado_en, rc.completado_en, rc.intentos;

        CREATE OR REPLACE VIEW public.vw_trazabilidad_global AS
        SELECT
            a.id_evento,
            a.registrado_en,
            a.tx_id,
            a.modulo,
            a.tabla_origen,
            a.operacion,
            a.registro_id,
            a.resumen,
            a.usuario_id,
            u.nombre AS usuario_nombre,
            u.correo AS usuario_correo,
            a.sesion_id,
            sp.estado AS sesion_estado,
            a.convocatoria_id,
            a.version_caso_id,
            vc.nombre AS caso_nombre,
            a.intento_id,
            a.datos_anteriores,
            a.datos_nuevos
        FROM public.auditoria_trazabilidad_global a
        LEFT JOIN public.usuario u ON u.id_usuario = a.usuario_id
        LEFT JOIN public.sesion_programada sp ON sp.id = a.sesion_id
        LEFT JOIN public.version_caso vc ON vc.id = COALESCE(a.version_caso_id, sp.version_caso_id)
        ORDER BY a.id_evento DESC;

        CREATE OR REPLACE VIEW public.vw_trazabilidad_estudiante_360 AS
        SELECT
            u.id_usuario AS estudiante_id,
            u.nombre AS estudiante_nombre,
            u.correo AS estudiante_correo,
            u.activo AS cuenta_activa,
            CASE
                WHEN vpi.id IS NULL THEN 'VERIFICADO_LEGACY'
                WHEN vpi.verificado THEN 'VERIFICADO'
                ELSE 'PENDIENTE_PRIMER_INGRESO'
            END AS estado_primer_ingreso,
            vpi.verificado_en,
            ga.id_grupo,
            ga.nombre AS grupo_nombre,
            ga.periodo AS grupo_periodo,
            ge.activo AS matricula_activa,
            conv.id AS convocatoria_id,
            conv.estado AS estado_convocatoria,
            conv.espera_registrada_en,
            sp.id AS sesion_id,
            sp.estado AS estado_sesion,
            vc.nombre AS caso_nombre,
            part.id_participacion,
            part.estado AS estado_participacion,
            (part.id_consentimiento IS NOT NULL) AS consentimiento_aceptado,
            COUNT(DISTINCT intn.id_intento) AS total_intentos,
            MAX(intn.numero_intento) AS ultimo_numero_intento,
            COALESCE((
                SELECT COUNT(*)
                FROM public.historial_cambio_decision h
                JOIN public.intento ix ON ix.id_intento = h.id_intento
                WHERE ix.id_participacion = part.id_participacion
            ), 0) AS total_cambios_decision,
            MAX(ri.nota_final) AS mejor_nota_provisional,
            rp.nota_definitiva AS nota_oficial,
            rp.situacion AS situacion_oficial,
            COALESCE(aus.confirmada, FALSE) AS ausencia_confirmada,
            (rd.id_retroalimentacion IS NOT NULL) AS tiene_retroalimentacion
        FROM public.usuario u
        JOIN public.rol r ON r.id_rol = u.id_rol AND upper(btrim(r.nombre)) = 'ESTUDIANTE'
        LEFT JOIN public.verificacion_primer_ingreso vpi ON vpi.id_usuario = u.id_usuario
        LEFT JOIN public.grupo_estudiante ge ON ge.id_estudiante = u.id_usuario
        LEFT JOIN public.grupo_academico ga ON ga.id_grupo = ge.id_grupo
        LEFT JOIN public.identidad_academica ia ON ia.id_usuario = u.id_usuario AND ia.sistema = 'SCHEDULING'
        LEFT JOIN public.convocatoria conv ON conv.estudiante_id = ia.id_academico
        LEFT JOIN public.sesion_programada sp ON sp.id = conv.sesion_id
        LEFT JOIN public.version_caso vc ON vc.id = sp.version_caso_id
        LEFT JOIN public.participacion part ON part.convocatoria_id = conv.id
        LEFT JOIN public.intento intn ON intn.id_participacion = part.id_participacion
        LEFT JOIN public.resultado_intento ri ON ri.id_intento = intn.id_intento
        LEFT JOIN LATERAL (
            SELECT res_p.*
            FROM public.resultado_participacion res_p
            JOIN public.publicacion_evaluacion pe ON pe.id = res_p.publicacion_id
            WHERE res_p.convocatoria_id = conv.id
            ORDER BY pe.version DESC
            LIMIT 1
        ) rp ON TRUE
        LEFT JOIN LATERAL (
            SELECT a.*
            FROM public.ausencia_academica a
            WHERE a.convocatoria_id = conv.id
            ORDER BY a.revision DESC
            LIMIT 1
        ) aus ON TRUE
        LEFT JOIN LATERAL (
            SELECT f.*
            FROM public.retroalimentacion_docente f
            WHERE f.id_participacion = part.id_participacion
            ORDER BY f.fecha_registro DESC, f.id_retroalimentacion DESC
            LIMIT 1
        ) rd ON TRUE
        GROUP BY
            u.id_usuario, u.nombre, u.correo, u.activo, vpi.id, vpi.verificado, vpi.verificado_en,
            ga.id_grupo, ga.nombre, ga.periodo, ge.activo,
            conv.id, conv.estado, conv.espera_registrada_en,
            sp.id, sp.estado, vc.nombre,
            part.id_participacion, part.estado, part.id_consentimiento,
            rp.nota_definitiva, rp.situacion, aus.confirmada, rd.id_retroalimentacion;

        CREATE OR REPLACE VIEW public.vw_trazabilidad_correos_y_notificaciones AS
        SELECT
            n.id AS notificacion_id,
            n.creada_en,
            n.tipo,
            n.canal,
            n.estado AS estado_notificacion,
            n.convocatoria_id,
            sp.id AS sesion_id,
            vc.nombre AS caso_nombre,
            u.id_usuario AS destinatario_usuario_id,
            u.nombre AS destinatario_nombre,
            u.correo AS destinatario_correo,
            n.mensaje,
            dc.estado AS estado_despacho_smtp,
            dc.intentos AS intentos_smtp,
            dc.ultimo_error,
            dc.ultimo_intento_en,
            dc.aceptado_en,
            n.publicacion_evaluacion_id
        FROM public.notificacion n
        LEFT JOIN public.despacho_correo dc ON dc.id_notificacion = n.id
        LEFT JOIN public.convocatoria c ON c.id = n.convocatoria_id
        LEFT JOIN public.sesion_programada sp ON sp.id = c.sesion_id
        LEFT JOIN public.version_caso vc ON vc.id = sp.version_caso_id
        LEFT JOIN public.identidad_academica ia ON ia.sistema = 'SCHEDULING' AND ia.id_academico = n.destinatario_id
        LEFT JOIN public.usuario u ON u.id_usuario = ia.id_usuario;

        CREATE OR REPLACE VIEW public.vw_trazabilidad_intentos_decisiones AS
        SELECT
            i.id_intento,
            i.id_participacion,
            i.numero_intento,
            i.estado AS estado_intento,
            i.inicio,
            i.fin,
            i.duracion_concedida_segundos,
            p.convocatoria_id,
            c.sesion_id,
            sp.version_caso_id,
            vc.nombre AS caso_nombre,
            ue.id_usuario AS estudiante_id,
            ue.nombre AS estudiante_nombre,
            ue.correo AS estudiante_correo,
            i.id_consentimiento,
            cons.version_texto AS consentimiento_version,
            cons.fecha_aceptacion AS consentimiento_fecha,
            i.id_permiso_extra,
            pe.justificacion AS motivo_intento_extra,
            COUNT(DISTINCT b.id_borrador) AS total_borradores_actuales,
            COUNT(DISTINCT h.id_historial) AS total_cambios_decision,
            COUNT(DISTINCT ps.id_paso) AS total_pasos_congelados,
            ri.nota_final AS nota_provisional,
            ri.modalidad AS modalidad_provisional,
            ri.ambito AS ambito_evaluacion,
            ri.version_regla,
            ri.procedencia_sha256
        FROM public.intento i
        JOIN public.participacion p ON p.id_participacion = i.id_participacion
        JOIN public.convocatoria c ON c.id = p.convocatoria_id
        JOIN public.sesion_programada sp ON sp.id = c.sesion_id
        JOIN public.version_caso vc ON vc.id = sp.version_caso_id
        JOIN public.grupo_estudiante ge ON ge.id_grupo_estudiante = p.id_grupo_estudiante
        JOIN public.usuario ue ON ue.id_usuario = ge.id_estudiante
        JOIN public.consentimiento cons ON cons.id_consentimiento = i.id_consentimiento
        LEFT JOIN public.permiso_intento_extra pe ON pe.id_permiso_extra = i.id_permiso_extra
        LEFT JOIN public.borrador_decision_intento b ON b.id_intento = i.id_intento
        LEFT JOIN public.historial_cambio_decision h ON h.id_intento = i.id_intento
        LEFT JOIN public.paso_simulacion ps ON ps.id_intento = i.id_intento
        LEFT JOIN public.resultado_intento ri ON ri.id_intento = i.id_intento
        GROUP BY
            i.id_intento, i.id_participacion, i.numero_intento, i.estado, i.inicio, i.fin, i.duracion_concedida_segundos,
            p.convocatoria_id, c.sesion_id, sp.version_caso_id, vc.nombre,
            ue.id_usuario, ue.nombre, ue.correo,
            i.id_consentimiento, cons.version_texto, cons.fecha_aceptacion,
            i.id_permiso_extra, pe.justificacion,
            ri.nota_final, ri.modalidad, ri.ambito, ri.version_regla, ri.procedencia_sha256;

        CREATE OR REPLACE VIEW public.vw_matriz_permisos_usuarios AS
        SELECT
            u.id_usuario,
            u.nombre,
            u.correo,
            u.activo,
            upper(btrim(r.nombre)) AS rol,
            ARRAY(
                SELECT p.codigo
                FROM public.rol_permiso rp
                JOIN public.permiso p ON p.id_permiso = rp.id_permiso
                WHERE rp.id_rol = u.id_rol
                ORDER BY p.codigo
            ) AS permisos_rol,
            ARRAY(
                SELECT p.codigo
                FROM public.usuario_permiso up
                JOIN public.permiso p ON p.id_permiso = up.id_permiso
                WHERE up.id_usuario = u.id_usuario AND up.concedido = TRUE
                ORDER BY p.codigo
            ) AS permisos_concedidos_individuales,
            ARRAY(
                SELECT p.codigo
                FROM public.usuario_permiso up
                JOIN public.permiso p ON p.id_permiso = up.id_permiso
                WHERE up.id_usuario = u.id_usuario AND up.concedido = FALSE
                ORDER BY p.codigo
            ) AS permisos_revocados_individuales,
            ARRAY(
                SELECT p.codigo
                FROM public.permiso p
                WHERE (
                    EXISTS (SELECT 1 FROM public.rol_permiso rp WHERE rp.id_rol = u.id_rol AND rp.id_permiso = p.id_permiso)
                    AND NOT EXISTS (SELECT 1 FROM public.usuario_permiso up WHERE up.id_usuario = u.id_usuario AND up.id_permiso = p.id_permiso AND up.concedido = FALSE)
                ) OR EXISTS (
                    SELECT 1 FROM public.usuario_permiso up WHERE up.id_usuario = u.id_usuario AND up.id_permiso = p.id_permiso AND up.concedido = TRUE
                )
                ORDER BY p.codigo
            ) AS permisos_efectivos
        FROM public.usuario u
        JOIN public.rol r ON r.id_rol = u.id_rol;
        """
    )


def downgrade():
    if op.get_bind().dialect.name != "postgresql":
        return

    # Eliminar vistas nuevas y recrear las 4 vistas originales exactas de 20261119_db_views_and_triggers
    op.execute("DROP VIEW IF EXISTS public.vw_matriz_permisos_usuarios;")
    op.execute("DROP VIEW IF EXISTS public.vw_trazabilidad_intentos_decisiones;")
    op.execute("DROP VIEW IF EXISTS public.vw_trazabilidad_correos_y_notificaciones;")
    op.execute("DROP VIEW IF EXISTS public.vw_trazabilidad_estudiante_360;")
    op.execute("DROP VIEW IF EXISTS public.vw_trazabilidad_global;")

    op.execute("DROP VIEW IF EXISTS public.vw_auditoria_primer_ingreso;")
    op.execute("DROP VIEW IF EXISTS public.vw_seguimiento_participacion;")
    op.execute("DROP VIEW IF EXISTS public.vw_resumen_sesiones;")
    op.execute("DROP VIEW IF EXISTS public.vw_catalogo_casos;")

    op.execute(
        """
        CREATE VIEW public.vw_catalogo_casos AS
        SELECT
            c.id AS caso_id, c.id_caso, v.id AS version_id, v.numero AS numero_version,
            v.nombre AS nombre_caso, v.estado, v.tiempo_estimado_min,
            u.nombre AS docente_nombre, u.correo AS docente_correo,
            COUNT(DISTINCT e.id) AS total_escenarios, COUNT(DISTINCT p.id) AS total_preguntas,
            (r.id IS NOT NULL) AS tiene_rubrica, r.nombre AS rubrica_nombre, r.version_regla, c.creado_en
        FROM public.caso c
        JOIN public.version_caso v ON v.caso_id = c.id
        LEFT JOIN public.identidad_academica ia ON ia.sistema = 'CASES' AND ia.id_academico = c.docente_creador_id
        LEFT JOIN public.usuario u ON u.id_usuario = ia.id_usuario
        LEFT JOIN public.escenario e ON e.version_caso_id = v.id
        LEFT JOIN public.pregunta p ON p.escenario_id = e.id
        LEFT JOIN public.rubrica r ON r.version_caso_id = v.id
        GROUP BY c.id, c.id_caso, v.id, v.numero, v.nombre, v.estado, v.tiempo_estimado_min,
                 u.nombre, u.correo, r.id, r.nombre, r.version_regla, c.creado_en;

        CREATE VIEW public.vw_resumen_sesiones AS
        SELECT
            sp.id AS sesion_id, sp.estado AS estado_sesion, ea.nombre AS espacio_nombre,
            vc.nombre AS caso_nombre, vc.numero AS version_numero, ga.nombre AS grupo_nombre,
            ga.periodo AS grupo_periodo, ud.nombre AS docente_nombre,
            sp.fecha_inicio, sp.fecha_fin, sp.tiempo_maximo_minutos,
            COUNT(DISTINCT conv.id) FILTER (WHERE conv.estado = 'ACTIVA') AS total_convocatorias_activas,
            COUNT(DISTINCT part.id_participacion) AS total_participaciones,
            COUNT(DISTINCT intn.id_intento) FILTER (WHERE intn.estado IN ('FINALIZADO', 'VENCIDO')) AS total_intentos_cerrados
        FROM public.sesion_programada sp
        JOIN public.espacio_academico ea ON ea.id = sp.espacio_academico_id
        JOIN public.version_caso vc ON vc.id = sp.version_caso_id
        LEFT JOIN public.asignacion_caso ac ON ac.sesion_programada_id = sp.id
        LEFT JOIN public.grupo_academico ga ON ga.id_grupo = ac.id_grupo
        LEFT JOIN public.identidad_academica ia ON ia.sistema = 'SCHEDULING' AND ia.id_academico = sp.docente_id
        LEFT JOIN public.usuario ud ON ud.id_usuario = ia.id_usuario
        LEFT JOIN public.convocatoria conv ON conv.sesion_id = sp.id
        LEFT JOIN public.participacion part ON part.convocatoria_id = conv.id
        LEFT JOIN public.intento intn ON intn.id_participacion = part.id_participacion
        GROUP BY sp.id, sp.estado, ea.nombre, vc.nombre, vc.numero, ga.nombre, ga.periodo,
                 ud.nombre, sp.fecha_inicio, sp.fecha_fin, sp.tiempo_maximo_minutos;

        CREATE VIEW public.vw_seguimiento_participacion AS
        SELECT
            sp.id AS sesion_id, sp.estado AS estado_sesion, vc.nombre AS caso_nombre,
            conv.id AS convocatoria_id, conv.estado AS estado_convocatoria,
            ue.id_usuario AS estudiante_id, ue.nombre AS estudiante_nombre, ue.correo AS estudiante_correo,
            part.id_participacion, part.estado AS estado_participacion,
            intn.id_intento AS intento_id, intn.numero_intento, intn.estado AS estado_intento,
            ri.nota_final AS nota_provisional, ri.modalidad AS modalidad_provisional,
            rp.nota_definitiva AS nota_oficial, rp.situacion AS situacion_oficial,
            (rd.id_retroalimentacion IS NOT NULL) AS tiene_retroalimentacion, rd.texto AS retroalimentacion_docente
        FROM public.convocatoria conv
        JOIN public.sesion_programada sp ON sp.id = conv.sesion_id
        JOIN public.version_caso vc ON vc.id = sp.version_caso_id
        LEFT JOIN public.identidad_academica ia ON ia.sistema = 'SCHEDULING' AND ia.id_academico = conv.estudiante_id
        LEFT JOIN public.usuario ue ON ue.id_usuario = ia.id_usuario
        LEFT JOIN public.participacion part ON part.convocatoria_id = conv.id
        LEFT JOIN LATERAL (
            SELECT i.* FROM public.intento i WHERE i.id_participacion = part.id_participacion ORDER BY i.numero_intento DESC LIMIT 1
        ) intn ON TRUE
        LEFT JOIN public.resultado_intento ri ON ri.id_intento = intn.id_intento
        LEFT JOIN public.resultado_participacion rp ON rp.convocatoria_id = conv.id
        LEFT JOIN public.retroalimentacion_docente rd ON rd.id_participacion = part.id_participacion;

        CREATE VIEW public.vw_auditoria_primer_ingreso AS
        SELECT
            u.id_usuario, u.nombre, u.correo, u.activo, upper(btrim(r.nombre)) AS rol,
            CASE
                WHEN vpi.id IS NULL THEN 'VERIFICADO_LEGACY'
                WHEN vpi.verificado THEN 'VERIFICADO'
                ELSE 'PENDIENTE_PRIMER_INGRESO'
            END AS estado_primer_ingreso,
            vpi.verificado_en, COALESCE(vpi.intentos, 0) AS intentos_otp, vpi.expira_en,
            MAX(CASE WHEN ia.sistema = 'CASES' THEN ia.id_academico::text END) AS identidad_cases,
            MAX(CASE WHEN ia.sistema = 'SCHEDULING' THEN ia.id_academico::text END) AS identidad_scheduling
        FROM public.usuario u
        JOIN public.rol r ON r.id_rol = u.id_rol
        LEFT JOIN public.verificacion_primer_ingreso vpi ON vpi.id_usuario = u.id_usuario
        LEFT JOIN public.identidad_academica ia ON ia.id_usuario = u.id_usuario
        GROUP BY u.id_usuario, u.nombre, u.correo, u.activo, r.nombre,
                 vpi.id, vpi.verificado, vpi.verificado_en, vpi.intentos, vpi.expira_en;
        """
    )

    tablas_auditadas = [
        "retroalimentacion_docente", "ausencia_academica", "resultado_participacion",
        "publicacion_evaluacion", "resultado_intento", "paso_simulacion",
        "historial_cambio_decision", "intento", "permiso_intento_extra",
        "participacion", "consentimiento", "despacho_correo", "notificacion",
        "convocatoria", "asignacion_caso", "sesion_programada", "rubrica",
        "version_caso", "caso", "grupo_estudiante", "grupo_academico",
        "docente_espacio_academico", "espacio_academico", "identidad_academica",
        "recuperacion_contrasena", "verificacion_primer_ingreso",
        "rol_permiso", "usuario_permiso", "usuario",
    ]
    for tabla in tablas_auditadas:
        op.execute(f"DROP TRIGGER IF EXISTS trg_audit_{tabla} ON public.{tabla};")

    for fn in (
        "sps_auditar_evaluacion_fn",
        "sps_auditar_participacion_fn",
        "sps_auditar_programacion_fn",
        "sps_auditar_casos_fn",
        "sps_auditar_academico_fn",
        "sps_auditar_identidad_fn",
    ):
        op.execute(f"DROP FUNCTION IF EXISTS public.{fn}();")

    op.execute("DROP TRIGGER IF EXISTS trg_sesion_programada_guard ON public.sesion_programada;")
    op.execute("DROP FUNCTION IF EXISTS public.sps_proteger_sesion_programada_fn();")

    op.execute("DROP TRIGGER IF EXISTS trg_notificacion_guard ON public.notificacion;")
    op.execute("DROP FUNCTION IF EXISTS public.sps_proteger_notificacion_fn();")

    op.execute("DROP TRIGGER IF EXISTS trg_despacho_correo_guard ON public.despacho_correo;")
    op.execute("DROP FUNCTION IF EXISTS public.sps_proteger_despacho_correo_fn();")

    op.execute("DROP TRIGGER IF EXISTS trg_historial_cambio_decision_no_truncar ON public.historial_cambio_decision;")
    op.execute("DROP TRIGGER IF EXISTS trg_historial_cambio_decision_guard ON public.historial_cambio_decision;")
    op.execute("DROP FUNCTION IF EXISTS public.sps_proteger_historial_cambio_decision_fn();")

    op.execute("DROP TRIGGER IF EXISTS trg_borrador_decision_no_truncar ON public.borrador_decision_intento;")
    op.execute("DROP TRIGGER IF EXISTS trg_borrador_decision_intento_guard ON public.borrador_decision_intento;")
    op.execute(
        """
        CREATE TRIGGER trg_borrador_decision_intento_guard
        BEFORE INSERT OR UPDATE ON public.borrador_decision_intento
        FOR EACH ROW
        EXECUTE FUNCTION public.sps_proteger_borrador_intento_fn();
        """
    )

    op.execute("DROP TRIGGER IF EXISTS trg_auditoria_trazabilidad_no_truncar ON public.auditoria_trazabilidad_global;")
    op.execute("DROP TRIGGER IF EXISTS trg_auditoria_trazabilidad_inmutable ON public.auditoria_trazabilidad_global;")
    op.execute("DROP FUNCTION IF EXISTS public.sps_auditoria_global_inmutable_fn();")

    op.drop_index("ix_auditoria_global_intento", table_name="auditoria_trazabilidad_global")
    op.drop_index("ix_auditoria_global_convocatoria", table_name="auditoria_trazabilidad_global")
    op.drop_index("ix_auditoria_global_sesion", table_name="auditoria_trazabilidad_global")
    op.drop_index("ix_auditoria_global_usuario", table_name="auditoria_trazabilidad_global")
    op.drop_index("ix_auditoria_global_modulo_tabla", table_name="auditoria_trazabilidad_global")
    op.drop_index("ix_auditoria_global_fecha", table_name="auditoria_trazabilidad_global")
    op.drop_table("auditoria_trazabilidad_global")
