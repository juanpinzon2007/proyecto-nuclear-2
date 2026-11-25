"""Pruebas reales en PostgreSQL 17 de integridad, seguridad y trazabilidad global de vistas y disparadores."""

from datetime import UTC, datetime, timedelta
import hashlib
import json
import os
from uuid import uuid4

from alembic import command
import pytest
import sqlalchemy as sa
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from tests.identity.academic_identity_support import config_alembic, motor_postgresql_desechable

pytestmark = pytest.mark.skipif(
    os.getenv("SPS_TEST_IDENTITY_MAPPING_DOCKER") != "1",
    reason="Requiere contenedor PostgreSQL 17 desechable opt-in (SPS_TEST_IDENTITY_MAPPING_DOCKER=1).",
)


@pytest.fixture(scope="module")
def pg_trazabilidad():
    with motor_postgresql_desechable() as engine:
        with engine.begin() as conn:
            command.upgrade(config_alembic(conn), "head")
        yield engine


def test_migracion_upgrade_downgrade_y_seguridad_funciones_pg(pg_trazabilidad):
    with pg_trazabilidad.begin() as conn:
        # Verificar round-trip limpio downgrade -> upgrade sobre PostgreSQL 17 real
        command.downgrade(config_alembic(conn), "20261119_password_recovery")
        vistas_previas = set(
            conn.scalars(
                text("SELECT table_name FROM information_schema.views WHERE table_schema='public'")
            ).all()
        )
        assert "vw_trazabilidad_global" not in vistas_previas
        assert {"vw_catalogo_casos", "vw_resumen_sesiones", "vw_seguimiento_participacion", "vw_auditoria_primer_ingreso"} <= vistas_previas

        command.upgrade(config_alembic(conn), "head")

        vistas_actuales = set(
            conn.scalars(
                text("SELECT table_name FROM information_schema.views WHERE table_schema='public'")
            ).all()
        )
        assert {
            "vw_catalogo_casos",
            "vw_resumen_sesiones",
            "vw_seguimiento_participacion",
            "vw_auditoria_primer_ingreso",
            "vw_trazabilidad_global",
            "vw_trazabilidad_estudiante_360",
            "vw_trazabilidad_correos_y_notificaciones",
            "vw_trazabilidad_intentos_decisiones",
            "vw_matriz_permisos_usuarios",
        } <= vistas_actuales

        # Buenas prácticas: todas las funciones sps_* son SECURITY INVOKER con search_path fijo
        funciones = conn.execute(
            text(
                "SELECT proname, prosecdef, proconfig "
                "FROM pg_proc p JOIN pg_namespace n ON n.oid = p.pronamespace "
                "WHERE n.nspname = 'public' AND proname LIKE 'sps_%'"
            )
        ).all()
        assert len(funciones) >= 18
        for nombre, secdef, config in funciones:
            assert secdef is False, f"{nombre} no debe ser SECURITY DEFINER"
            assert config is not None and any("search_path=" in item for item in config), (
                f"{nombre} debe fijar search_path"
            )

        # Cobertura global de triggers (incluyendo TRUNCATE en pg_trigger)
        tablas_con_triggers = set(
            conn.scalars(
                text(
                    "SELECT DISTINCT c.relname "
                    "FROM pg_trigger t "
                    "JOIN pg_class c ON c.oid = t.tgrelid "
                    "JOIN pg_namespace n ON n.oid = c.relnamespace "
                    "WHERE n.nspname = 'public' AND NOT t.tgisinternal"
                )
            ).all()
        )
        tablas_esperadas = {
            "auditoria_trazabilidad_global",
            "usuario",
            "usuario_permiso",
            "rol_permiso",
            "verificacion_primer_ingreso",
            "recuperacion_contrasena",
            "identidad_academica",
            "espacio_academico",
            "docente_espacio_academico",
            "grupo_academico",
            "grupo_estudiante",
            "caso",
            "version_caso",
            "rubrica",
            "sesion_programada",
            "asignacion_caso",
            "convocatoria",
            "notificacion",
            "despacho_correo",
            "consentimiento",
            "participacion",
            "permiso_intento_extra",
            "intento",
            "borrador_decision_intento",
            "historial_cambio_decision",
            "paso_simulacion",
            "resultado_intento",
            "publicacion_evaluacion",
            "resultado_participacion",
            "ausencia_academica",
            "retroalimentacion_docente",
        }
        faltantes = tablas_esperadas - tablas_con_triggers
        assert not faltantes, f"Faltan triggers en tablas: {sorted(faltantes)}"


def _sembrar_escenario_completo(conn):
    ahora = datetime.now(UTC)
    ahora_naive = ahora.replace(tzinfo=None)

    conn.execute(
        text(
            "INSERT INTO rol (id_rol, nombre, descripcion) VALUES "
            "(1, 'DOCENTE', 'Docente'), (2, 'ESTUDIANTE', 'Estudiante'), (3, 'ADMINISTRADOR', 'Admin')"
        )
    )
    conn.execute(
        text(
            "INSERT INTO permiso (id_permiso, codigo, descripcion) VALUES "
            "(1, 'CREAR_CASOS', 'Crear casos'), (2, 'VER_RESULTADOS', 'Ver resultados')"
        )
    )
    conn.execute(text("INSERT INTO rol_permiso (id_rol, id_permiso) VALUES (1, 1)"))

    conn.execute(
        text(
            "INSERT INTO usuario (id_usuario, id_rol, nombre, correo, clave_hash, activo) VALUES "
            "(10, 3, '  Admin Principal  ', '  admin@sps.edu.co ', 'hash-admin-1', true), "
            "(20, 1, 'Prof. Laura Gómez', 'laura.docente@sps.edu.co', 'hash-doc-1', true), "
            "(30, 2, 'Juan Estudiante', 'juan.est@sps.edu.co', 'hash-est-1', true)"
        )
    )
    conn.execute(
        text(
            "INSERT INTO usuario_permiso (id_usuario, id_permiso, concedido) VALUES "
            "(20, 1, false), (20, 2, true)"
        )
    )
    conn.execute(
        text(
            "INSERT INTO verificacion_primer_ingreso (id_usuario, verificado, codigo_hash, intentos, creado_en) "
            "VALUES (30, false, 'secreto-otp-hash', 1, :ahora)"
        ),
        {"ahora": ahora},
    )
    conn.execute(
        text(
            "UPDATE verificacion_primer_ingreso SET verificado = true WHERE id_usuario = 30"
        )
    )
    conn.execute(
        text(
            "INSERT INTO recuperacion_contrasena (id_usuario, codigo_hash, expira_en, intentos, solicitado_en) "
            "VALUES (20, 'secreto-rec-hash', :exp, 0, :ahora)"
        ),
        {"exp": ahora + timedelta(minutes=15), "ahora": ahora},
    )

    doc_cases_uuid = uuid4()
    doc_sched_uuid = uuid4()
    est_sched_uuid = uuid4()
    conn.execute(
        text(
            "INSERT INTO identidad_academica (sistema, id_academico, id_usuario) VALUES "
            "('CASES', :dc, 20), ('SCHEDULING', :ds, 20), ('SCHEDULING', :es, 30)"
        ),
        {"dc": doc_cases_uuid, "ds": doc_sched_uuid, "es": est_sched_uuid},
    )

    espacio_id = uuid4()
    conn.execute(
        text("INSERT INTO espacio_academico (id, nombre) VALUES (:id, 'Laboratorio 101')"),
        {"id": espacio_id},
    )
    conn.execute(
        text("INSERT INTO docente_espacio_academico (id_docente, espacio_academico_id) VALUES (20, :e)"),
        {"e": espacio_id},
    )
    conn.execute(
        text(
            "INSERT INTO grupo_academico (id_grupo, id_profesor, nombre, periodo) "
            "VALUES (100, 20, 'Grupo A', '2026-2')"
        )
    )
    conn.execute(
        text(
            "INSERT INTO grupo_estudiante (id_grupo_estudiante, id_grupo, id_estudiante, fecha_ingreso, activo) "
            "VALUES (1000, 100, 30, :f, true)"
        ),
        {"f": ahora_naive},
    )

    caso_id = uuid4()
    version_id = uuid4()
    esc_id = uuid4()
    preg_id = uuid4()
    op1_id = uuid4()
    op2_id = uuid4()
    rub_id = uuid4()
    crit_id = uuid4()
    niv_id = uuid4()
    conn.execute(
        text("INSERT INTO caso (id, id_caso, docente_creador_id, creado_en) VALUES (:id, 50, :d, :f)"),
        {"id": caso_id, "d": doc_cases_uuid, "f": ahora},
    )
    conn.execute(
        text(
            "INSERT INTO version_caso (id, caso_id, numero, nombre, desarrollo_situacional, contexto_historia, tiempo_estimado_min, estado) "
            "VALUES (:id, :cid, 1, 'Caso Trazabilidad', 'Dev', 'Hist', 30, 'BORRADOR')"
        ),
        {"id": version_id, "cid": caso_id},
    )
    conn.execute(
        text(
            "INSERT INTO escenario (id, version_caso_id, orden, contexto_situacional, es_inicial) "
            "VALUES (:id, :vid, 1, 'Escena 1', true)"
        ),
        {"id": esc_id, "vid": version_id},
    )
    conn.execute(
        text("INSERT INTO pregunta (id, escenario_id, orden, enunciado) VALUES (:id, :eid, 1, '¿Decisión?')"),
        {"id": preg_id, "eid": esc_id},
    )
    conn.execute(
        text(
            "INSERT INTO opcion_respuesta (id, pregunta_id, orden, texto, es_correcta, justificacion, tipo_transicion) VALUES "
            "(:o1, :pid, 1, 'Opción 1', true, 'Bien', 'FIN'), "
            "(:o2, :pid, 2, 'Opción 2', false, 'Mal', 'FIN')"
        ),
        {"o1": op1_id, "o2": op2_id, "pid": preg_id},
    )
    conn.execute(
        text("INSERT INTO rubrica (id, version_caso_id, nombre, version_regla) VALUES (:id, :vid, 'Rúbrica V1', 'RUBRICA_V1')"),
        {"id": rub_id, "vid": version_id},
    )
    conn.execute(
        text("INSERT INTO criterio_rubrica (id, rubrica_id, nombre, peso) VALUES (:id, :rid, 'Ética', 100.00)"),
        {"id": crit_id, "rid": rub_id},
    )
    conn.execute(
        text("INSERT INTO nivel_rubrica (id, criterio_id, nombre, puntaje, descriptor) VALUES (:id, :cid, 'Alto', 5.00, 'Óptimo')"),
        {"id": niv_id, "cid": crit_id},
    )
    conn.execute(
        text(
            "INSERT INTO valoracion_opcion (opcion_id, criterio_id, puntaje) VALUES (:o1, :cid, 5.00), (:o2, :cid, 1.00)"
        ),
        {"o1": op1_id, "cid": crit_id, "o2": op2_id},
    )
    conn.execute(
        text("UPDATE version_caso SET estado = 'PUBLICADO' WHERE id = :vid"),
        {"vid": version_id},
    )

    sesion_id = uuid4()
    conv_id = uuid4()
    notif_id = uuid4()
    conn.execute(
        text(
            "INSERT INTO sesion_programada (id, espacio_academico_id, version_caso_id, docente_id, fecha_inicio, fecha_fin, tiempo_maximo_minutos, estado) "
            "VALUES (:id, :esp, :vid, :doc, :fi, :ff, 25, 'EN_CURSO')"
        ),
        {"id": sesion_id, "esp": espacio_id, "vid": version_id, "doc": doc_sched_uuid, "fi": ahora, "ff": ahora + timedelta(hours=2)},
    )
    conn.execute(
        text(
            "INSERT INTO asignacion_caso (id_asignacion, id_grupo, id_caso, apertura, cierre, fecha_limite_ingreso, intentos_base, tiempo_maximo_min, codigo_acceso_hash, estado, sesion_programada_id, version_caso_id) "
            "VALUES (500, 100, 50, :ap, :ci, :lim, 1, 25, 'hash-asig', 'ACTIVA', :sid, :vid)"
        ),
        {"ap": ahora_naive, "ci": ahora_naive + timedelta(hours=2), "lim": ahora_naive + timedelta(hours=1), "sid": sesion_id, "vid": version_id},
    )
    conn.execute(
        text(
            "INSERT INTO convocatoria (id, sesion_id, estudiante_id, codigo_hash, estado) "
            "VALUES (:id, :sid, :es, 'hash-convocatoria-secreto', 'ACTIVA')"
        ),
        {"id": conv_id, "sid": sesion_id, "es": est_sched_uuid},
    )
    conn.execute(
        text(
            "INSERT INTO notificacion (id, convocatoria_id, destinatario_id, tipo, canal, mensaje, estado, creada_en) "
            "VALUES (:id, :cid, :es, 'CONVOCATORIA', 'CORREO', 'Convocado al caso', 'PENDIENTE', :ahora)"
        ),
        {"id": notif_id, "cid": conv_id, "es": est_sched_uuid, "ahora": ahora},
    )
    conn.execute(
        text(
            "INSERT INTO despacho_correo (id_notificacion, payload_cifrado, estado, intentos) "
            "VALUES (:nid, :cifrado, 'PENDIENTE', 0)"
        ),
        {"nid": notif_id, "cifrado": b"payload-fernet-cifrado"},
    )
    conn.execute(
        text(
            "UPDATE despacho_correo SET estado = 'ACEPTADO_PROVEEDOR', intentos = 1, aceptado_en = :ahora WHERE id_notificacion = :nid"
        ),
        {"nid": notif_id, "ahora": ahora},
    )

    doc_ver_id = 1
    orig_bytes = b"documento-original-consentimiento"
    evid_bytes = b"evidencia-aprobacion-comite"
    texto_cons = "Texto consentimiento"
    sha_orig = hashlib.sha256(orig_bytes).hexdigest()
    sha_txt = hashlib.sha256(texto_cons.encode("utf-8")).hexdigest()
    sha_evid = hashlib.sha256(evid_bytes).hexdigest()
    conn.execute(
        text(
            "INSERT INTO documento_consentimiento_version (id_version_documento, referencia, documento_id, version, original, tipo_media, texto, sha256_original, sha256_texto, autoridad_aprobadora, aprobado_en, evidencia_aprobacion, sha256_aprobacion, publicado_por, publicado_en, vigente_desde) "
            "VALUES (:id, 'REF-1', 'DOC-1', '1.0', :orig, 'text/plain', :txt, :so, :st, 'Comite', :ahora, :evid, :se, 10, :ahora, :ahora)"
        ),
        {
            "id": doc_ver_id,
            "orig": orig_bytes,
            "txt": texto_cons,
            "so": sha_orig,
            "st": sha_txt,
            "evid": evid_bytes,
            "se": sha_evid,
            "ahora": ahora,
        },
    )
    conn.execute(
        text(
            "INSERT INTO seleccion_consentimiento (id_asignacion, id_version_documento, seleccionado_por, seleccionado_en) "
            "VALUES (500, :dv, 20, :ahora)"
        ),
        {"dv": doc_ver_id, "ahora": ahora},
    )
    conn.execute(
        text(
            "INSERT INTO consentimiento (id_consentimiento, id_estudiante, version_texto, fecha_aceptacion, id_version_documento, aceptacion_explicita, huella_aceptada) "
            "VALUES (700, 30, 'REF-1', :f, :dv, true, :st)"
        ),
        {"f": ahora_naive, "dv": doc_ver_id, "st": sha_txt},
    )
    conn.execute(
        text(
            "INSERT INTO participacion (id_participacion, id_asignacion, id_grupo_estudiante, convocatoria_id, estado, fecha_registro, id_consentimiento) "
            "VALUES (800, 500, 1000, :cid, 'en_progreso', :f, 700)"
        ),
        {"cid": conv_id, "f": ahora_naive},
    )
    conn.execute(
        text(
            "INSERT INTO intento (id_intento, id_participacion, id_consentimiento, numero_intento, estado, inicio, duracion_concedida_segundos) "
            "VALUES (900, 800, 700, 1, 'EN_CURSO', :f, 1500.000000)"
        ),
        {"f": ahora_naive},
    )

    # RF-10: Guardar borrador, modificarlo y eliminar huérfano mientras intento está EN_CURSO
    conn.execute(
        text(
            "INSERT INTO borrador_decision_intento (id_borrador, id_intento, id_decision, id_opcion, actualizado_en) "
            "VALUES (1, 900, :pid, :o2, :ahora)"
        ),
        {"pid": preg_id, "o2": op2_id, "ahora": ahora},
    )
    conn.execute(
        text(
            "INSERT INTO historial_cambio_decision (id_intento, id_decision, id_opcion_anterior, id_opcion_nueva, cambiado_en) "
            "VALUES (900, :pid, NULL, :o2, :ahora), (900, :pid, :o2, :o1, :ahora)"
        ),
        {"pid": preg_id, "o1": op1_id, "o2": op2_id, "ahora": ahora},
    )
    conn.execute(
        text(
            "UPDATE borrador_decision_intento SET id_opcion = :o1 WHERE id_borrador = 1"
        ),
        {"o1": op1_id},
    )
    # Limpieza de borrador permitida durante EN_CURSO y re-inserción antes de envío
    conn.execute(text("DELETE FROM borrador_decision_intento WHERE id_borrador = 1"))
    conn.execute(
        text(
            "INSERT INTO borrador_decision_intento (id_borrador, id_intento, id_decision, id_opcion, actualizado_en) "
            "VALUES (2, 900, :pid, :o1, :ahora)"
        ),
        {"pid": preg_id, "o1": op1_id, "ahora": ahora},
    )

    conn.execute(
        text(
            "INSERT INTO paso_simulacion (id_paso, id_intento, id_decision, id_opcion, numero_paso, registrado_en, tiempo_segundos) "
            "VALUES (950, 900, :pid, :o1, 1, :f, 45)"
        ),
        {"pid": preg_id, "o1": op1_id, "f": ahora_naive + timedelta(seconds=45)},
    )
    conn.execute(
        text(
            "UPDATE intento SET estado = 'FINALIZADO', fin = :fin WHERE id_intento = 900"
        ),
        {"fin": ahora_naive + timedelta(minutes=10)},
    )
    conn.execute(
        text("UPDATE participacion SET estado = 'completada' WHERE id_participacion = 800")
    )
    conn.execute(
        text("UPDATE sesion_programada SET estado = 'FINALIZADO' WHERE id = :sid"),
        {"sid": sesion_id},
    )
    conn.execute(
        text(
            "UPDATE sesion_programada SET mostrar_resultados_provisionales = true, visibilidad_docente_id = 20, visibilidad_actualizada_en = :ahora "
            "WHERE id = :sid"
        ),
        {"sid": sesion_id, "ahora": ahora},
    )

    proc_sha = hashlib.sha256(b"{}").hexdigest()
    conn.execute(
        text(
            "INSERT INTO resultado_intento (id_resultado, id_intento, nota_final, fecha_calculo, id_caso, caso_id, version_caso_id, rubrica_id, version_regla, modalidad, ambito, politica_id, politica_version, politica_hash, procedencia, procedencia_sha256) "
            "VALUES (1100, 900, 95.50, :ahora, 50, :cid, :vid, :rid, 'RUBRICA_V1', 'COMPLETA', 'RUBRICA_V1', 'pol-1', '1.0', repeat('b', 64), '{}', :psha)"
        ),
        {"ahora": ahora, "cid": caso_id, "vid": version_id, "rid": rub_id, "psha": proc_sha},
    )
    conn.execute(
        text(
            "INSERT INTO resultado_criterio (id_resultado_criterio, id_resultado, rubrica_id, id_criterio, id_nivel, puntaje_obtenido) "
            "VALUES (1200, 1100, :rid, :crit, :niv, 5.00)"
        ),
        {"rid": rub_id, "crit": crit_id, "niv": niv_id},
    )

    # Dos publicaciones oficiales (v1 y v2) para verificar ausencia de duplicación en vw_seguimiento_participacion
    pub1_id = uuid4()
    pub2_id = uuid4()
    fila_snap = {
        "convocatoria_id": str(conv_id),
        "id_estudiante": 30,
        "id_asignacion": 500,
        "id_participacion": 800,
        "id_resultado_intento": 1100,
        "id_ausencia": None,
        "situacion": "COMPLETA",
        "nota": "95.50",
    }
    detalle_json = json.dumps(fila_snap, sort_keys=True, separators=(",", ":"))
    fuente_v1 = json.dumps({"version": 1, "filas": [fila_snap]}, sort_keys=True, separators=(",", ":"))
    fuente_v2 = json.dumps({"version": 2, "filas": [fila_snap]}, sort_keys=True, separators=(",", ":"))
    sha_v1 = hashlib.sha256(fuente_v1.encode("utf-8")).hexdigest()
    sha_v2 = hashlib.sha256(fuente_v2.encode("utf-8")).hexdigest()

    conn.execute(
        text(
            "INSERT INTO publicacion_evaluacion (id, sesion_id, id_profesor, version, fecha, fuente_documento, fuente_sha256) VALUES "
            "(:p1, :sid, 20, 1, :ahora, :d1, :s1), "
            "(:p2, :sid, 20, 2, :ahora, :d2, :s2)"
        ),
        {"p1": pub1_id, "p2": pub2_id, "sid": sesion_id, "ahora": ahora, "d1": fuente_v1, "s1": sha_v1, "d2": fuente_v2, "s2": sha_v2},
    )
    conn.execute(
        text(
            "INSERT INTO resultado_participacion (publicacion_id, convocatoria_id, id_participacion, id_estudiante, id_asignacion, id_resultado_intento, situacion, nota_definitiva, detalle) VALUES "
            "(:p1, :cid, 800, 30, 500, 1100, 'COMPLETA', 95.50, :det), "
            "(:p2, :cid, 800, 30, 500, 1100, 'COMPLETA', 95.50, :det)"
        ),
        {"p1": pub1_id, "p2": pub2_id, "cid": conv_id, "det": detalle_json},
    )

    notif_cal_1 = uuid4()
    notif_cal_2 = uuid4()
    conn.execute(
        text(
            "INSERT INTO notificacion (id, convocatoria_id, destinatario_id, tipo, canal, mensaje, estado, creada_en, publicacion_evaluacion_id) VALUES "
            "(:n1, :cid, :es, 'CALIFICACION', 'INTERNA', 'Notas v1', 'PENDIENTE', :ahora, :p1), "
            "(:n2, :cid, :es, 'CALIFICACION', 'INTERNA', 'Notas v2', 'PENDIENTE', :ahora, NULL)"
        ),
        {"n1": notif_cal_1, "n2": notif_cal_2, "cid": conv_id, "es": est_sched_uuid, "ahora": ahora, "p1": pub1_id},
    )
    conn.execute(
        text("UPDATE notificacion SET publicacion_evaluacion_id = :pub WHERE id = :id"),
        {"pub": pub2_id, "id": notif_cal_2},
    )
    conn.execute(
        text(
            "INSERT INTO evento_auditoria (id, sesion_id, tipo, origen, descripcion, creado_en) VALUES "
            "(:e1, :sid, 'RESULTADOS_PUBLICADOS', 'DOCENTE', :desc1, :ahora), "
            "(:e2, :sid, 'RESULTADOS_PUBLICADOS', 'DOCENTE', :desc2, :ahora)"
        ),
        {
            "e1": uuid4(),
            "e2": uuid4(),
            "sid": sesion_id,
            "desc1": json.dumps({"publicacion_id": str(pub1_id)}),
            "desc2": json.dumps({"publicacion_id": str(pub2_id)}),
            "ahora": ahora,
        },
    )

    return {
        "preg_id": preg_id,
        "op1_id": op1_id,
        "sesion_id": sesion_id,
        "notif_id": notif_id,
        "notif_cal_id": notif_cal_2,
        "pub1_id": pub1_id,
        "conv_id": conv_id,
    }


def _esperar_check_23514(conn, sql_stmt: str, params: dict | None = None):
    with pytest.raises(IntegrityError) as exc:
        with conn.begin_nested():
            conn.execute(text(sql_stmt), params or {})
    assert exc.value.orig.sqlstate == "23514"


def test_disparadores_integridad_trazabilidad_y_vistas_globales(pg_trazabilidad):
    with pg_trazabilidad.begin() as conn:
        ctx = _sembrar_escenario_completo(conn)

        # 1. Validar vistas completas y ausencia de duplicados multi-publicación
        seg = conn.execute(text("SELECT * FROM vw_seguimiento_participacion")).mappings().all()
        assert len(seg) == 1
        assert float(seg[0]["nota_oficial"]) == 95.50
        assert seg[0]["version_publicacion_oficial"] == 2
        assert seg[0]["consentimiento_aceptado"] is True

        cat = conn.execute(text("SELECT * FROM vw_catalogo_casos")).mappings().all()
        assert len(cat) == 1
        assert cat[0]["total_opciones"] == 2
        assert cat[0]["tiene_grafo_configurado"] is True
        assert cat[0]["total_sesiones_programadas"] == 1

        ses = conn.execute(text("SELECT * FROM vw_resumen_sesiones")).mappings().all()
        assert len(ses) == 1
        assert ses[0]["ultima_version_publicada"] == 2
        assert ses[0]["mostrar_resultados_provisionales"] is True

        aud_ing = {
            row["id_usuario"]: row
            for row in conn.execute(text("SELECT * FROM vw_auditoria_primer_ingreso")).mappings().all()
        }
        assert aud_ing[10]["estado_primer_ingreso"] == "NO_APLICA"
        assert aud_ing[20]["estado_primer_ingreso"] == "NO_APLICA"
        assert aud_ing[20]["recuperacion_solicitada_en"] is not None
        assert aud_ing[30]["estado_primer_ingreso"] == "VERIFICADO"

        matriz = {
            row["id_usuario"]: row
            for row in conn.execute(text("SELECT * FROM vw_matriz_permisos_usuarios")).mappings().all()
        }
        assert matriz[20]["permisos_rol"] == ["CREAR_CASOS"]
        assert matriz[20]["permisos_concedidos_individuales"] == ["VER_RESULTADOS"]
        assert matriz[20]["permisos_revocados_individuales"] == ["CREAR_CASOS"]
        assert matriz[20]["permisos_efectivos"] == ["VER_RESULTADOS"]

        v360 = conn.execute(text("SELECT * FROM vw_trazabilidad_estudiante_360")).mappings().all()
        assert len(v360) == 1
        assert v360[0]["total_cambios_decision"] == 2
        assert float(v360[0]["nota_oficial"]) == 95.50

        vcorr = conn.execute(text("SELECT * FROM vw_trazabilidad_correos_y_notificaciones")).mappings().all()
        assert len(vcorr) == 3

        vint = conn.execute(text("SELECT * FROM vw_trazabilidad_intentos_decisiones")).mappings().all()
        assert len(vint) == 1
        assert vint[0]["total_cambios_decision"] == 2
        assert vint[0]["total_borradores_actuales"] == 1

        # El cambio de la vista conserva su contrato sobre datos existentes.
        consulta_intentos = text("SELECT * FROM vw_trazabilidad_intentos_decisiones ORDER BY id_intento")
        command.downgrade(config_alembic(conn), "20261120_global_traceability")
        assert conn.execute(consulta_intentos).mappings().all() == vint
        command.upgrade(config_alembic(conn), "head")
        assert conn.execute(consulta_intentos).mappings().all() == vint

        vglob = conn.execute(text("SELECT * FROM vw_trazabilidad_global")).mappings().all()
        modulos_registrados = {row["modulo"] for row in vglob}
        assert {"IDENTITY", "ACADEMICO", "CASES", "SCHEDULING", "CORREOS", "PARTICIPATION", "EVALUACION"} <= modulos_registrados

        # 2. Verificar sanitización estricta de secretos en auditoría global
        secret_hits = conn.scalar(
            text(
                "SELECT COUNT(*) FROM auditoria_trazabilidad_global "
                "WHERE (datos_anteriores ?| array['clave_hash','codigo_hash','payload_cifrado','codigo_acceso_hash']) "
                "   OR (datos_nuevos ?| array['clave_hash','codigo_hash','payload_cifrado','codigo_acceso_hash'])"
            )
        )
        assert secret_hits == 0

        # 3. Verificar bloqueos de integridad e inmutabilidad en TODOS los disparadores nuevos/endurecidos
        _esperar_check_23514(
            conn,
            "INSERT INTO usuario (id_usuario, id_rol, nombre, correo, clave_hash, activo) VALUES (99, 2, 'X', 'x@sps.edu.co', 'h', true)",
        )
        _esperar_check_23514(conn, "UPDATE usuario SET id_rol = 1 WHERE id_usuario = 30")
        _esperar_check_23514(conn, "UPDATE verificacion_primer_ingreso SET verificado = false WHERE id_usuario = 30")
        _esperar_check_23514(conn, "INSERT INTO verificacion_primer_ingreso (id_usuario, verificado, creado_en) VALUES (20, false, now())")

        _esperar_check_23514(conn, "UPDATE borrador_decision_intento SET reflexion_estudiante = 'tarde' WHERE id_borrador = 2")
        _esperar_check_23514(conn, "DELETE FROM borrador_decision_intento WHERE id_borrador = 2")
        _esperar_check_23514(conn, "TRUNCATE TABLE borrador_decision_intento")

        _esperar_check_23514(
            conn,
            "INSERT INTO historial_cambio_decision (id_intento, id_decision, id_opcion_anterior, id_opcion_nueva, cambiado_en) "
            "VALUES (900, :p, NULL, :o, now())",
            {"p": ctx["preg_id"], "o": ctx["op1_id"]},
        )
        _esperar_check_23514(conn, "UPDATE historial_cambio_decision SET id_opcion_nueva = :o", {"o": ctx["op1_id"]})
        _esperar_check_23514(conn, "DELETE FROM historial_cambio_decision")
        _esperar_check_23514(conn, "TRUNCATE TABLE historial_cambio_decision")

        _esperar_check_23514(conn, "UPDATE despacho_correo SET estado = 'PENDIENTE' WHERE id_notificacion = :nid", {"nid": ctx["notif_id"]})
        _esperar_check_23514(conn, "DELETE FROM despacho_correo WHERE id_notificacion = :nid", {"nid": ctx["notif_id"]})

        _esperar_check_23514(conn, "UPDATE notificacion SET mensaje = 'alterado' WHERE id = :nid", {"nid": ctx["notif_id"]})
        _esperar_check_23514(
            conn,
            "UPDATE notificacion SET publicacion_evaluacion_id = :p1 WHERE id = :nid",
            {"p1": ctx["pub1_id"], "nid": ctx["notif_cal_id"]},
        )

        _esperar_check_23514(conn, "UPDATE sesion_programada SET estado = 'EN_CURSO' WHERE id = :sid", {"sid": ctx["sesion_id"]})
        _esperar_check_23514(conn, "UPDATE auditoria_trazabilidad_global SET resumen = 'alterado'")
        _esperar_check_23514(conn, "DELETE FROM auditoria_trazabilidad_global")
        _esperar_check_23514(conn, "TRUNCATE TABLE auditoria_trazabilidad_global")
