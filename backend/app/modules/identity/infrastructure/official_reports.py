"""Lector RF-16: reutiliza autorización, verificación y snapshot canónico oficial."""
from datetime import UTC
from decimal import Decimal
from uuid import UUID
from sqlalchemy import select
from app.modules.identity.application.official_reports import FiltrosReporte, PublicacionReporte
from app.modules.identity.domain.errors import AccesoDenegado, IntegracionPendiente, RecursoNoDisponible
from app.modules.participation.infrastructure.academic_cycle import CicloAcademicoSQL
from app.modules.participation.infrastructure.academic_results_models import PublicacionEvaluacionModel as Pub
from app.modules.participation.infrastructure.models import IntentoModel as I
from app.modules.participation.infrastructure.errors import MapeoPersistenciaPendiente


class ConsultaReporteOficialSQLAlchemy:
    def __init__(self, ciclo: CicloAcademicoSQL):
        self.ciclo = ciclo

    def consultar(self, id_sesion: UUID, filtros: FiltrosReporte) -> PublicacionReporte:
        def leer(s):
            _, _, _, version, _, _, _ = self.ciclo._base(s, id_sesion)
            q = select(Pub).where(Pub.sesion_id == id_sesion)
            if filtros.version_publicacion is not None:
                q = q.where(Pub.version == filtros.version_publicacion)
            pub = s.scalar(q.order_by(Pub.version.desc()).limit(1))
            if pub is None:
                raise RecursoNoDisponible()
            fuente = self.ciclo._publicada(s, pub)
            filas = [dict(x['detalle']) for x in fuente['resultados']]
            grupos = {x['grupo_id'] for x in filas}
            alumnos = {x['id_estudiante'] for x in filas}
            if ((filtros.id_grupo is not None and filtros.id_grupo not in grupos)
                    or not set(filtros.estudiantes).issubset(alumnos)):
                raise AccesoDenegado()
            seleccion = [x for x in filas if
                (filtros.id_grupo is None or x['grupo_id'] == filtros.id_grupo)
                and (not filtros.estudiantes or x['id_estudiante'] in filtros.estudiantes)
                and (filtros.estado is None or x['situacion'] == filtros.estado)]
            for f in seleccion:
                if UUID(f['version_caso_id']) != version.id:
                    raise IntegracionPendiente()
                f['nota'] = Decimal(f['nota'])
                if not f['nota'].is_finite() or not Decimal(0) <= f['nota'] <= Decimal(100):
                    raise IntegracionPendiente()
                detalles = []
                for ref in f['intentos']:
                    i = s.get(I, ref['id_intento'])
                    if (i is None or i.id_participacion != f['id_participacion']
                            or i.numero_intento != ref['numero'] or i.estado != ref['estado']
                            or i.estado not in {'FINALIZADO', 'VENCIDO'} or i.fin is None):
                        raise IntegracionPendiente()
                    inicio = self.ciclo.fechas.desde_db(i.inicio)
                    fin = self.ciclo.fechas.desde_db(i.fin)
                    delta = fin - inicio
                    segundos = (Decimal(delta.days * 86400 + delta.seconds)
                                + Decimal(delta.microseconds) / Decimal(1000000))
                    if segundos < 0:
                        raise IntegracionPendiente()
                    detalles.append(dict(id_intento=i.id_intento, numero=i.numero_intento,
                        estado=i.estado, inicio=inicio, fin=fin, segundos=segundos,
                        concedidos=i.duracion_concedida_segundos))
                f['intentos'] = tuple(detalles)
            seleccion.sort(key=(lambda x: (x['grupo_nombre'].casefold(), x['grupo_id'],
                x['nombre_estudiante'].casefold(), x['id_estudiante'], x['convocatoria_id']))
                if filtros.agrupar_por == 'grupo' else (lambda x: (x['nombre_estudiante'].casefold(),
                    x['id_estudiante'], x['grupo_id'], x['convocatoria_id'])))
            return PublicacionReporte(pub.id, id_sesion, pub.version, pub.fuente_sha256,
                pub.fecha.astimezone(UTC), self.ciclo.reloj.ahora().astimezone(UTC), version.nombre,
                version.id, tuple(seleccion), tuple(sorted(fuente['retiradas'])), filtros)
        try:
            return self.ciclo._lectura(leer)
        except (MapeoPersistenciaPendiente, KeyError, ValueError, TypeError, ArithmeticError):
            raise IntegracionPendiente() from None
