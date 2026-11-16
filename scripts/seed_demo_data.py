"""Script para inicializar datos de prueba completos para el SPS (Simulador de Psicología Social).

Genera:
1. Usuario Administrador (admin@sps.edu.co / Admin123456!) con identidades CASES y SCHEDULING.
2. Usuario Docente (docente@sps.edu.co / Docente123456!) con permiso CREAR_CASOS e identidades vinculadas.
3. Usuario Estudiante 1 (estudiante@unihumboldt.edu.co / Estudiante123456!) para simulación en vivo.
4. Usuario Estudiante 2 (estudiante2@unihumboldt.edu.co / Estudiante123456!) con simulación previa.
5. Espacio Académico ("Laboratorio de Psicología Social 301") y docente asignado.
6. Grupo Académico ("Psicología Experimental 2026-I") con los dos estudiantes matriculados.
7. Casos de Simulación:
   - "Dilema de Conformidad Grupal (Experimento Asch)" - PUBLICADO con grafo de transiciones.
   - "Experimento de Obediencia a la Autoridad (Milgram)" - BORRADOR.
8. Sesión programada en curso asociada al caso publicado.
9. Asignación académica vinculando el grupo a la sesión y caso.
10. Convocatorias con códigos de acceso:
   - Estudiante 1: "SPS-ETICA-2026" (ACTIVA, pendiente de realización).
   - Estudiante 2: "SPS-MILGRAM-2026" (ACTIVA, con intento finalizado y retroalimentación docente).
"""

import uuid
from datetime import datetime, timedelta, timezone
from decimal import Decimal
import sqlalchemy as sa

from app.db.models import registrar_modelos_integrados
from app.db.session import get_session_factory
from app.modules.identity.infrastructure.models import UsuarioORM, RolORM, PermisoORM, RolPermisoORM
from app.modules.identity.infrastructure.academic_identity_models import IdentidadAcademicaORM
from app.modules.identity.infrastructure.credentials import obtener_hasheador
from app.modules.identity.infrastructure.academic_base_models import GrupoAcademicoORM, GrupoEstudianteORM, ConsentimientoORM
from app.modules.identity.infrastructure.academic_models import RetroalimentacionDocenteORM
from app.modules.cases.application.services.caso_service import CasoService
from app.modules.cases.domain.builders.constructor_caso import ConstructorCaso
from app.modules.cases.domain.validators.eslabones import construir_cadena_publicacion
from app.modules.cases.infrastructure.repositories.caso_repository import CasoRepository
from app.modules.cases.infrastructure.models import CasoModel, VersionCasoModel
from app.modules.cases.api.schemas.caso_schemas import (
    CasoPayload, DatosCasoSchema, EscenarioSchema, PreguntaSchema,
    OpcionSchema, RubricaSchema, CriterioSchema, NivelSchema
)
from app.modules.scheduling.infrastructure.models import (
    EspacioAcademicoModel, DocenteEspacioAcademicoModel, SesionProgramadaModel, ConvocatoriaModel
)
from app.modules.scheduling.infrastructure.assignment_models import AsignacionCasoModel
from app.modules.scheduling.domain.access_codes import hash_codigo
from app.modules.participation.infrastructure.models import ParticipacionModel, IntentoModel, PasoSimulacionModel

DOCENTE_CASES_ID = uuid.UUID("11111111-1111-4111-8111-111111111111")
DOCENTE_SCHED_ID = uuid.UUID("11111111-1111-4111-8111-222222222222")

ADMIN_CASES_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-111111111111")
ADMIN_SCHED_ID = uuid.UUID("aaaaaaaa-aaaa-4aaa-8aaa-222222222222")

ESTUDIANTE_SCHED_ID = uuid.UUID("33333333-3333-4333-8333-333333333333")
ESTUDIANTE2_SCHED_ID = uuid.UUID("44444444-4444-4444-8444-444444444444")

def seed():
    registrar_modelos_integrados()
    fabrica = get_session_factory()
    hasheador = obtener_hasheador()

    print("=== INICIANDO SEEDING COMPLETO DE DATOS DE PRUEBA ===")

    with fabrica() as s:
        # Sincronizar secuencias PostgreSQL con filas existentes
        for tabla, col in (('rol', 'id_rol'), ('permiso', 'id_permiso'), ('usuario', 'id_usuario')):
            s.execute(sa.text(
                f"SELECT setval(pg_get_serial_sequence('{tabla}', '{col}'), COALESCE((SELECT MAX({col}) FROM {tabla}), 1), true)"
            ))
        s.commit()

        def vincular(id_user, sist, id_acad):
            existe = s.execute(sa.select(IdentidadAcademicaORM).where(
                IdentidadAcademicaORM.id_usuario == id_user,
                IdentidadAcademicaORM.sistema == sist
            )).scalar_one_or_none()
            if not existe:
                s.add(IdentidadAcademicaORM(id_usuario=id_user, sistema=sist, id_academico=id_acad))
                print(f"  + Vinculado usuario {id_user} a {sist}: {id_acad}")

        roles_db = {r.nombre.upper(): r.id_rol for r in s.execute(sa.select(RolORM)).scalars().all()}
        admin_rol_id = roles_db.get("ADMINISTRADOR", 17)
        docente_rol_id = roles_db.get("DOCENTE", 1)
        estudiante_rol_id = roles_db.get("ESTUDIANTE", 2)

        # 1. Asegurar Admin
        admin = s.execute(sa.select(UsuarioORM).where(UsuarioORM.correo == 'admin@sps.edu.co')).scalar_one_or_none()
        if not admin:
            admin = UsuarioORM(
                id_rol=admin_rol_id,
                nombre="Director General Administrador",
                correo="admin@sps.edu.co",
                clave_hash=hasheador.hash("Admin123456!"),
                activo=True
            )
            s.add(admin)
            s.flush()
        vincular(admin.id_usuario, 'CASES', ADMIN_CASES_ID)
        vincular(admin.id_usuario, 'SCHEDULING', ADMIN_SCHED_ID)

        # 2. Asegurar Docente
        docente = s.execute(sa.select(UsuarioORM).where(UsuarioORM.correo == 'docente@sps.edu.co')).scalar_one_or_none()
        if not docente:
            docente = UsuarioORM(
                id_rol=docente_rol_id,
                nombre="Prof. Carlos Mendoza",
                correo="docente@sps.edu.co",
                clave_hash=hasheador.hash("Docente123456!"),
                activo=True
            )
            s.add(docente)
            s.flush()
        
        for cod, desc in (
            ('CREAR_CASOS', 'Permite crear, editar y publicar casos de simulación'),
            ('PROGRAMAR_SESIONES', 'Permite programar y gestionar sesiones académicas'),
            ('GESTIONAR_EVALUACIONES', 'Permite consolidar, rectificar y publicar evaluaciones'),
        ):
            perm = s.execute(sa.select(PermisoORM).where(PermisoORM.codigo == cod)).scalar_one_or_none()
            if not perm:
                perm = PermisoORM(codigo=cod, descripcion=desc)
                s.add(perm)
                s.flush()
            if cod in ('CREAR_CASOS', 'PROGRAMAR_SESIONES'):
                existe_rp = s.execute(sa.select(RolPermisoORM).where(
                    RolPermisoORM.id_rol == docente_rol_id,
                    RolPermisoORM.id_permiso == perm.id_permiso
                )).scalar_one_or_none()
                if not existe_rp:
                    s.add(RolPermisoORM(id_rol=docente_rol_id, id_permiso=perm.id_permiso))

        vincular(docente.id_usuario, 'CASES', DOCENTE_CASES_ID)
        vincular(docente.id_usuario, 'SCHEDULING', DOCENTE_SCHED_ID)

        # 3. Estudiante 1
        est1 = s.execute(sa.select(UsuarioORM).where(UsuarioORM.correo == 'estudiante@unihumboldt.edu.co')).scalar_one_or_none()
        if not est1:
            est1 = UsuarioORM(
                id_rol=estudiante_rol_id,
                nombre="Sofía Estudiante Demo",
                correo="estudiante@unihumboldt.edu.co",
                clave_hash=hasheador.hash("Estudiante123456!"),
                activo=True
            )
            s.add(est1)
            s.flush()
        vincular(est1.id_usuario, 'SCHEDULING', ESTUDIANTE_SCHED_ID)

        # 4. Estudiante 2
        est2 = s.execute(sa.select(UsuarioORM).where(UsuarioORM.correo == 'estudiante2@unihumboldt.edu.co')).scalar_one_or_none()
        if not est2:
            est2 = UsuarioORM(
                id_rol=estudiante_rol_id,
                nombre="Carlos Gómez Morales",
                correo="estudiante2@unihumboldt.edu.co",
                clave_hash=hasheador.hash("Estudiante123456!"),
                activo=True
            )
            s.add(est2)
            s.flush()
        vincular(est2.id_usuario, 'SCHEDULING', ESTUDIANTE2_SCHED_ID)

        # 5. Espacio Académico
        espacio = s.execute(sa.select(EspacioAcademicoModel).where(EspacioAcademicoModel.nombre == "Laboratorio de Psicología Social 301")).scalar_one_or_none()
        if not espacio:
            espacio = EspacioAcademicoModel(nombre="Laboratorio de Psicología Social 301")
            s.add(espacio)
            s.flush()
            print(f"  + Espacio creado: {espacio.nombre}")

        doc_esp = s.execute(sa.select(DocenteEspacioAcademicoModel).where(
            DocenteEspacioAcademicoModel.id_docente == docente.id_usuario,
            DocenteEspacioAcademicoModel.espacio_academico_id == espacio.id
        )).scalar_one_or_none()
        if not doc_esp:
            s.add(DocenteEspacioAcademicoModel(id_docente=docente.id_usuario, espacio_academico_id=espacio.id))

        # 6. Grupo Académico
        grupo = s.execute(sa.select(GrupoAcademicoORM).where(
            GrupoAcademicoORM.id_profesor == docente.id_usuario,
            GrupoAcademicoORM.nombre == "Psicología Experimental 2026-I"
        )).scalar_one_or_none()
        if not grupo:
            grupo = GrupoAcademicoORM(
                id_profesor=docente.id_usuario,
                nombre="Psicología Experimental 2026-I",
                periodo="2026-1"
            )
            s.add(grupo)
            s.flush()

        ahora_naive = datetime.now(timezone.utc).replace(tzinfo=None)
        for est in [est1, est2]:
            m = s.execute(sa.select(GrupoEstudianteORM).where(
                GrupoEstudianteORM.id_grupo == grupo.id_grupo,
                GrupoEstudianteORM.id_estudiante == est.id_usuario
            )).scalar_one_or_none()
            if not m:
                s.add(GrupoEstudianteORM(
                    id_grupo=grupo.id_grupo,
                    id_estudiante=est.id_usuario,
                    fecha_ingreso=ahora_naive
                ))

        s.commit()

    # 7. Crear Casos y Grafo
    with fabrica() as s:
        repo = CasoRepository(s)
        service = CasoService(
            repositorio=repo,
            fabrica_constructor=ConstructorCaso,
            cadena_validacion=construir_cadena_publicacion(),
            recorridos=repo,
        )

        casos_existentes = service.listar(DOCENTE_CASES_ID)
        if not any(c.nombre == "Dilema de Conformidad Grupal (Experimento Asch)" for c in casos_existentes):
            payload1 = CasoPayload(
                case=DatosCasoSchema(
                    nombre="Dilema de Conformidad Grupal (Experimento Asch)",
                    desarrolloSituacional="Un grupo de discusión académica delibera sobre una sanción disciplinaria dudosa impuesta a un estudiante.",
                    contextoHistoria="Asumes el rol de representante estudiantil en el comité disciplinario frente a directivos veteranos.",
                    tiempoEstimadoMin=40,
                ),
                scenarios=[
                    EscenarioSchema(
                        orden=1,
                        contextoSituacional="La comisión directiva vota unánimemente a favor de expulsar al estudiante sin escuchar testigos. Te piden tu voto.",
                        questions=[
                            PreguntaSchema(
                                orden=1,
                                enunciado="¿Cuál es tu postura inicial ante la presión de la votación unánime?",
                                options=[
                                    OpcionSchema(orden=1, texto="Votar a favor para evitar desacuerdo directo con los directivos.", esCorrecta=False, justificacion="Muestra conformidad por complacencia ante presión social.", valoraciones={"Ética": 1}),
                                    OpcionSchema(orden=2, texto="Solicitar formalmente la revisión de testimonios antes de votar.", esCorrecta=True, justificacion="Muestra resistencia constructiva, asertividad y defensa del debido proceso.", valoraciones={"Ética": 5}),
                                    OpcionSchema(orden=3, texto="Abstenerte en silencio sin emitir opinión ni voto.", esCorrecta=False, justificacion="Evasión de la responsabilidad de representación.", valoraciones={"Ética": 2}),
                                ]
                            )
                        ]
                    ),
                    EscenarioSchema(
                        orden=2,
                        contextoSituacional="El decano argumenta que escuchar testigos retrasará el informe 3 semanas y te pide encarecidamente que desistas.",
                        questions=[
                            PreguntaSchema(
                                orden=1,
                                enunciado="¿Cómo respondes ante la insistencia del decano?",
                                options=[
                                    OpcionSchema(orden=1, texto="Mantener la solicitud apelando al debido proceso institucional.", esCorrecta=True, justificacion="Firmeza ética fundada en el marco normativo universitario.", valoraciones={"Ética": 5}),
                                    OpcionSchema(orden=2, texto="Aceptar la expulsión si se compromete a revisar los procesos futuros.", esCorrecta=False, justificacion="Negociación perjudicial del derecho fundamental de defensa.", valoraciones={"Ética": 2}),
                                ]
                            )
                        ]
                    )
                ],
                rubric=RubricaSchema(
                    nombre="Rúbrica de Asertividad y Autonomía Moral",
                    versionRegla="1.0",
                    criterios=[
                        CriterioSchema(
                            nombre="Ética",
                            peso=100,
                            niveles=[
                                NivelSchema(nombre="Sobresaliente", puntaje=5, descriptor="Defiende el debido proceso con argumentos normativos y firmeza asertiva."),
                                NivelSchema(nombre="Aceptable", puntaje=3, descriptor="Resistencia moderada pero cede bajo presión social."),
                                NivelSchema(nombre="Insuficiente", puntaje=1, descriptor="Conformismo inmediato con la mayoría."),
                            ]
                        )
                    ]
                )
            )
            version1 = service.crear_borrador(DOCENTE_CASES_ID, payload1)
            s.commit()

            detalle1 = service.obtener(DOCENTE_CASES_ID, version1.id)
            esc1 = detalle1.escenarios[0]
            esc2 = detalle1.escenarios[1]
            opciones_esc1 = esc1.preguntas[0].opciones
            opciones_esc2 = esc2.preguntas[0].opciones

            service.configurar_recorrido(
                DOCENTE_CASES_ID,
                version1.id,
                inicial_id=esc1.id,
                transiciones=tuple(
                    [(o.id, "ESCENA", esc2.id) for o in opciones_esc1] +
                    [(o.id, "FIN", None) for o in opciones_esc2]
                )
            )
            s.commit()
            service.publicar(DOCENTE_CASES_ID, version1.id)
            s.commit()

        if not any(c.nombre == "Experimento de Obediencia a la Autoridad (Milgram)" for c in casos_existentes):
            payload2 = CasoPayload(
                case=DatosCasoSchema(
                    nombre="Experimento de Obediencia a la Autoridad (Milgram)",
                    desarrolloSituacional="Simulación de instrucciones de un superior jerárquico ante un procedimiento que vulnera protocolos de bienestar.",
                    contextoHistoria="Rol de asistente de laboratorio en una prueba de aprendizaje con descargas simuladas.",
                    tiempoEstimadoMin=30,
                ),
                scenarios=[
                    EscenarioSchema(
                        orden=1,
                        contextoSituacional="El experimentador con bata blanca ordena incrementar el voltaje a pesar de las quejas audibles del sujeto.",
                        questions=[
                            PreguntaSchema(
                                orden=1,
                                enunciado="¿Qué acción tomas ante la orden directa?",
                                options=[
                                    OpcionSchema(orden=1, texto="Detener inmediatamente el ensayo y verificar el estado del sujeto.", esCorrecta=True, justificacion="Prioriza la integridad humana sobre la autoridad.", valoraciones={"Ética": 5}),
                                    OpcionSchema(orden=2, texto="Continuar aplicando la descarga como lo indica el investigador.", esCorrecta=False, justificacion="Obediencia destructiva a la figura de autoridad.", valoraciones={"Ética": 0}),
                                ]
                            )
                        ]
                    )
                ]
            )
            version2 = service.crear_borrador(DOCENTE_CASES_ID, payload2)
            s.commit()

    # 8. Programar Sesión, Asignación, Convocatorias y Participación
    with fabrica() as s:
        docente = s.execute(sa.select(UsuarioORM).where(UsuarioORM.correo == 'docente@sps.edu.co')).scalar_one()
        est1 = s.execute(sa.select(UsuarioORM).where(UsuarioORM.correo == 'estudiante@unihumboldt.edu.co')).scalar_one()
        est2 = s.execute(sa.select(UsuarioORM).where(UsuarioORM.correo == 'estudiante2@unihumboldt.edu.co')).scalar_one()
        espacio = s.execute(sa.select(EspacioAcademicoModel).where(EspacioAcademicoModel.nombre == "Laboratorio de Psicología Social 301")).scalar_one()
        grupo = s.execute(sa.select(GrupoAcademicoORM).where(GrupoAcademicoORM.nombre == "Psicología Experimental 2026-I")).scalar_one()
        ge2 = s.execute(sa.select(GrupoEstudianteORM).where(GrupoEstudianteORM.id_grupo == grupo.id_grupo, GrupoEstudianteORM.id_estudiante == est2.id_usuario)).scalar_one()

        repo = CasoRepository(s)
        service = CasoService(
            repositorio=repo,
            fabrica_constructor=ConstructorCaso,
            cadena_validacion=construir_cadena_publicacion(),
            recorridos=repo,
        )
        casos = service.listar(DOCENTE_CASES_ID)
        caso_publicado = next((c for c in casos if c.estado.value == 'PUBLICADO'), None)

        if caso_publicado:
            caso_orm = s.execute(sa.select(CasoModel).where(CasoModel.docente_creador_id == DOCENTE_CASES_ID)).scalars().first()
            version_orm = s.execute(sa.select(VersionCasoModel).where(VersionCasoModel.id == caso_publicado.version_id)).scalar_one()

            sesion = s.execute(sa.select(SesionProgramadaModel).where(
                SesionProgramadaModel.docente_id == DOCENTE_SCHED_ID,
                SesionProgramadaModel.version_caso_id == caso_publicado.version_id
            )).scalars().first()

            ahora = datetime.now(timezone.utc)
            ahora_naive = ahora.replace(tzinfo=None)

            if not sesion:
                sesion = SesionProgramadaModel(
                    docente_id=DOCENTE_SCHED_ID,
                    espacio_academico_id=espacio.id,
                    version_caso_id=caso_publicado.version_id,
                    fecha_inicio=ahora,
                    fecha_fin=ahora + timedelta(hours=12),
                    tiempo_maximo_minutos=45,
                    lugar="Laboratorio 301 - Campus Principal",
                    mensaje_personalizado="Bienvenido a la simulación del Experimento de Conformidad Grupal.",
                    estado="EN_CURSO"
                )
                s.add(sesion)
                s.flush()
            else:
                sesion.fecha_inicio = ahora
                sesion.fecha_fin = ahora + timedelta(hours=12)
                sesion.estado = "EN_CURSO"
                s.flush()

            asig = s.execute(sa.select(AsignacionCasoModel).where(
                AsignacionCasoModel.sesion_programada_id == sesion.id,
                AsignacionCasoModel.id_grupo == grupo.id_grupo
            )).scalar_one_or_none()

            if not asig:
                asig = AsignacionCasoModel(
                    id_grupo=grupo.id_grupo,
                    id_caso=caso_orm.id_caso,
                    sesion_programada_id=sesion.id,
                    version_caso_id=version_orm.id,
                    apertura=ahora_naive - timedelta(minutes=5),
                    cierre=ahora_naive + timedelta(hours=12),
                    fecha_limite_ingreso=ahora_naive + timedelta(minutes=45),
                    intentos_base=1,
                    tiempo_maximo_min=45,
                    estado="activa"
                )
                s.add(asig)
                s.flush()
            else:
                asig.apertura = ahora_naive - timedelta(minutes=5)
                asig.cierre = ahora_naive + timedelta(hours=12)
                asig.fecha_limite_ingreso = ahora_naive + timedelta(minutes=45)
                s.flush()

            conv1 = s.execute(sa.select(ConvocatoriaModel).where(
                ConvocatoriaModel.sesion_id == sesion.id,
                ConvocatoriaModel.estudiante_id == ESTUDIANTE_SCHED_ID
            )).scalar_one_or_none()

            if not conv1:
                conv1 = ConvocatoriaModel(
                    sesion_id=sesion.id,
                    estudiante_id=ESTUDIANTE_SCHED_ID,
                    codigo_hash=hash_codigo("SPS-ETICA-2026"),
                    estado="ACTIVA"
                )
                s.add(conv1)
                s.flush()

            conv2 = s.execute(sa.select(ConvocatoriaModel).where(
                ConvocatoriaModel.sesion_id == sesion.id,
                ConvocatoriaModel.estudiante_id == ESTUDIANTE2_SCHED_ID
            )).scalar_one_or_none()

            if not conv2:
                conv2 = ConvocatoriaModel(
                    sesion_id=sesion.id,
                    estudiante_id=ESTUDIANTE2_SCHED_ID,
                    codigo_hash=hash_codigo("SPS-MILGRAM-2026"),
                    estado="ACTIVA"
                )
                s.add(conv2)
                s.flush()

            part2 = s.execute(sa.select(ParticipacionModel).where(
                ParticipacionModel.convocatoria_id == conv2.id
            )).scalar_one_or_none()

            if not part2:
                cons2 = ConsentimientoORM(
                    id_estudiante=est2.id_usuario,
                    version_texto="1.0",
                    fecha_aceptacion=ahora_naive - timedelta(hours=2)
                )
                s.add(cons2)
                s.flush()

                part2 = ParticipacionModel(
                    id_asignacion=asig.id_asignacion,
                    id_grupo_estudiante=ge2.id_grupo_estudiante,
                    convocatoria_id=conv2.id,
                    estado="completada",
                    fecha_registro=ahora_naive - timedelta(hours=2),
                    id_consentimiento=cons2.id_consentimiento
                )
                s.add(part2)
                s.flush()

                comienzo = ahora_naive - timedelta(minutes=45)
                registrado = comienzo + timedelta(seconds=120)
                fin_intento = comienzo + timedelta(minutes=25)

                intento2 = IntentoModel(
                    id_participacion=part2.id_participacion,
                    id_consentimiento=cons2.id_consentimiento,
                    numero_intento=1,
                    estado="EN_CURSO",
                    inicio=comienzo,
                    fin=None,
                    duracion_concedida_segundos=Decimal("2700.000000")
                )
                s.add(intento2)
                s.flush()

                detalle = service.obtener(DOCENTE_CASES_ID, version_orm.id)
                esc1 = detalle.escenarios[0]
                preg1 = esc1.preguntas[0]
                opc_correcta = next(o for o in preg1.opciones if o.es_correcta)

                paso = PasoSimulacionModel(
                    id_intento=intento2.id_intento,
                    id_decision=preg1.id,
                    id_opcion=opc_correcta.id,
                    numero_paso=1,
                    registrado_en=registrado,
                    tiempo_segundos=120
                )
                s.add(paso)
                s.flush()

                intento2.estado = "FINALIZADO"
                intento2.fin = fin_intento
                s.flush()

                fb = RetroalimentacionDocenteORM(
                    id_asignacion=asig.id_asignacion,
                    id_participacion=part2.id_participacion,
                    id_profesor=docente.id_usuario,
                    texto="Excelente defensa del debido proceso institucional. Gran criterio ético al solicitar testimonios.",
                    fecha_registro=ahora_naive - timedelta(minutes=30)
                )
                s.add(fb)

            s.commit()

    print("=====================================================")
    print("  DATOS DE PRUEBA COMPLETOS SEEDADOS SATISFACTORIAMENTE")
    print("=====================================================")

if __name__ == '__main__':
    seed()

