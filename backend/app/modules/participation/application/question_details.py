"""Contabilidad exacta de preguntas; nunca determina pesos de calificación."""
from decimal import Decimal, Context, localcontext
from fractions import Fraction

from app.modules.participation.domain.evaluation import EvaluacionInconsistente


def detalle_exacto(config, selecciones):
    ruta, total, puntos = config.seleccionar(selecciones)
    nodos = {e.id: e for e in config.grafo.escenas}
    correspondencias = {}
    for p in config.puntajes:
        correspondencias.setdefault(p.pregunta_id, set()).add(p.criterio_id)
    memo = {}

    def perfil(eid):
        if eid not in memo:
            q = nodos[eid].preguntas[0]
            propio = tuple(int(c in correspondencias[q.id]) for c in config.criterios)
            ramas = {tuple(a+b for a,b in zip(propio, perfil(o.destino_id)
                if o.tipo == 'ESCENA' else (0,)*len(propio))) for o in q.opciones}
            if len(ramas) != 1:
                raise EvaluacionInconsistente('Perfil de criterios ambiguo.')
            memo[eid] = ramas.pop()
        return memo[eid]

    cantidades = perfil(config.grafo.validar_ejecutable())
    precision = max((len(p.as_tuple().digits)+abs(p.as_tuple().exponent) for p in puntos), default=1)+len(str(total))+32
    with localcontext(Context(prec=precision)):
        suma = sum(puntos, Decimal(0))
        preguntas = tuple(dict(pregunta_id=q,opcion_id=o,puntaje=p,numero_paso=i+1)
            for i,((q,o),p) in enumerate(zip(selecciones,puntos)))
        criterios = []
        for cid,n in zip(config.criterios,cantidades):
            valores = [(q,p) for (q,_),p in zip(selecciones,puntos) if cid in correspondencias[q]]
            # Una pregunta sigue teniendo un voto. Su contribución se reparte
            # por igual entre sus correspondencias SOLO para contabilizarla;
            # la nota se calcula directamente por preguntas, nunca por criterios.
            aporte = sum((Fraction(p)/len(correspondencias[q]) for q,p in valores),Fraction(0))/total
            criterios.append(dict(criterio_id=cid,suma_puntajes=sum((p for _,p in valores),Decimal(0)),
                preguntas_evaluables=n,numerador=aporte.numerator,denominador=aporte.denominator))
        if sum((Fraction(c['numerador'],c['denominador']) for c in criterios),Fraction(0)) != Fraction(suma)/total:
            raise EvaluacionInconsistente('Las contribuciones no corresponden al promedio global.')
    return dict(suma_puntajes=suma,preguntas_exigidas=total,preguntas_respondidas=len(puntos),
        preguntas_pendientes=total-len(puntos),preguntas=preguntas,criterios=tuple(criterios))
