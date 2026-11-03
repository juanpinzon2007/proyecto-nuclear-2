"""Genera el reporte desde JUnit real; no atribuye PASS a escenarios no ejecutados."""

import argparse
import json
from pathlib import Path
import xml.etree.ElementTree as ET


def celda(valor: object) -> str:
    return str(valor).replace("|", "\\|").replace("\n", " ")


def estado_grupo(casos, nombres):
    seleccion = [c for c in casos if c.get("classname", "").split(".")[-1] in nombres]
    if not seleccion or any(c.find("skipped") is not None for c in seleccion):
        return "BLOCKED"
    if any(c.find("failure") is not None or c.find("error") is not None for c in seleccion):
        return "FAIL"
    return "PASS"


def generar(junit: Path, salida: Path) -> None:
    casos = list(ET.parse(junit).getroot().iter("testcase"))
    fallidos = sum(c.find("failure") is not None or c.find("error") is not None for c in casos)
    omitidos = sum(c.find("skipped") is not None for c in casos)
    aprobados = len(casos) - fallidos - omitidos
    lineas = [
        "# Evidencia de QA funcional — Participación SPS", "",
        "Reporte generado desde `tests/artifacts/qa.xml`, producido por la ejecución real de Pytest.",
        "Los estados provienen de JUnit; los valores obtenidos se registran después de las aserciones.", "",
        f"**{aprobados} aprobadas, {fallidos} fallidas y {omitidos} omitidas; {len(casos)} pruebas recogidas.**", "",
        "Entorno: aplicación FastAPI aislada, TestClient normal con excepciones visibles, fachada, servicios,",
        "dominio, estrategias y calculador reales. Solo se sustituyen los ports externos y repositorios por fakes.",
        "No hay políticas oficiales ni PostgreSQL académico verificados.", "",
        "## Matriz ejecutada", "",
        "| Endpoint | Escenario probado | Resultado esperado | Resultado obtenido | Estado | Archivo de prueba asociado |",
        "| --- | --- | --- | --- | --- | --- |",
    ]
    trazas = []
    filas = 0
    for caso in casos:
        propiedades = caso.find("properties")
        if propiedades is None:
            continue
        estado = "BLOCKED" if caso.find("skipped") is not None else (
            "FAIL" if caso.find("failure") is not None or caso.find("error") is not None else "PASS"
        )
        archivo = caso.get("file", "tests/test_http_functional.py").replace("\\", "/")
        if "app/modules/participation/" in archivo:
            archivo = archivo.split("app/modules/participation/", 1)[1]
        for propiedad in propiedades.findall("property"):
            if propiedad.get("name") == "traza_capas":
                trazas = json.loads(propiedad.get("value", "[]"))
            if propiedad.get("name") != "qa":
                continue
            datos = json.loads(propiedad.get("value", "{}"))
            columnas = [datos["endpoint"], datos["escenario"], datos["esperado"], datos["obtenido"], estado,
                        f"{archivo}::{caso.get('name')}"]
            lineas.append("| " + " | ".join(map(celda, columnas)) + " |")
            filas += 1
    if not filas:
        raise ValueError("JUnit no contiene evidencia funcional; ejecutar con -o junit_family=xunit1.")
    lineas += ["", f"Filas de evidencia HTTP registradas: {filas}.", "", "## Escenario completo y defectos", "",
        "`test_flujo_funcional_completo_http_con_trazabilidad` materializa la participación en el fake,",
        "inicia por HTTP, registra dos decisiones inmutables, consulta progreso y rechaza PUT conservando ambas,",
        "finaliza, rechaza edición, repite cierre sin escrituras y obtiene PENDIENTE antes de evaluar.",
        "Después solicita explícitamente la evaluación backend mediante Facade (no existe un endpoint que la dispare),",
        "confirma el cálculo real con política ficticia y lee DEFINITIVA 4.00 por HTTP. No se duplica al reintentar.", "",
        "Los espías de trazabilidad invocan los métodos originales: no reemplazan el dominio ni el cálculo.",
        "Secuencia registrada:", "", "```text", " → ".join(trazas), "```", "",
        "Defecto reproducido: la captura `except Exception` del router ocultaba RuntimeError al TestClient normal.",
        "La prueba nueva falló inicialmente con `DID NOT RAISE RuntimeError`. Se retiró esa captura;",
        "el error inesperado se propaga y ASGI sin debug devuelve HTTP 500 genérico, sin credenciales ni datos académicos.",
        "Se conserva la prueba anterior de privacidad usando `raise_server_exceptions=False` solo para observar ese límite HTTP.",
        "Cambio explícito del contrato provisional: el 500 inesperado deja de prometer el JSON ERROR_INTERNO;",
        "los errores esperados mantienen sus códigos JSON. No se borraron tests ni se cambiaron reglas académicas.", "",
        "## Comprobaciones adicionales y bloqueos", "",
        "| Alcance | Resultado / limitación | Estado | Evidencia |", "| --- | --- | --- | --- |",
        "| API anterior, dominio y Application | Se incluyen sus pruebas en esta ejecución | " + estado_grupo(casos, {"test_api", "test_domain", "test_application", "test_evaluation_domain", "test_evaluation_application"}) + " | tests/test_api.py y demás suites |",
        "| Infraestructura sin BD | Compilación SQL, codecs y ciclo Session; no prueba transacciones de filas | " + estado_grupo(casos, {"test_sqlalchemy_queries", "test_sqlalchemy_uow", "test_persistence_codecs"}) + " | tests/test_sqlalchemy_queries.py, tests/test_sqlalchemy_uow.py, tests/test_persistence_codecs.py |",
    ]
    for caso in casos:
        omitido = caso.find("skipped")
        if omitido is not None:
            lineas.append("| PostgreSQL real | " + celda(omitido.get("message", "Omitido")) + " | BLOCKED | " + celda(caso.get("name")) + " |")
    lineas += [
        "| Habilitación integrada de los siete endpoints | Router no registrado en main.py; identidad y adaptadores reales pendientes | BLOCKED | tests/test_api.py::test_router_no_registrado_en_aplicacion_principal |",
        "| Resultado definitivo de ausencia | Se prueban ceros internos sin intento y HTTP PENDIENTE; falta mapeo ER aprobado | BLOCKED | test_ausencia_usa_strategy_real_sin_intento_y_no_publica_cero_ficticio |", "",
        "La repetición de GET no calcula ni crea resultados. El test parcial pasa de PENDIENTE a PARCIAL 3.00",
        "solo después de habilitar una política de fixture explícita. La ausencia permanece pendiente; no se publica un cero ficticio.", "",
        "## Dependencias para la integración real", "",
        "- Alejandro: identidad verificada, consentimiento, propiedad y permisos reales.",
        "- Juan Andrés: contenido y recorrido autorizados, rúbrica histórica y mapeo académico a niveles.",
        "- Maicol: convocatorias/participaciones, ventanas, duración histórica y confirmación de ausencias.",
        "- Equipo: DDL aprobado, escritores SQL, unicidad/concurrencia PostgreSQL, precisión y políticas de evaluación/consolidación.", "",
        "No se modificó main.py, no se crearon tablas/migraciones ni se conectó una autenticación ficticia.",
        "No se verifican persistencia académica ni concurrencia real PostgreSQL. No se utiliza SQLite como sustituto.", "",
        "## Repetir la ejecución", "", "Desde la raíz del repositorio oficial, con el extra dev instalado:", "",
        "```powershell",
        '.\\.venv\\Scripts\\python.exe -m pytest backend/app/modules/participation/tests backend/tests -c backend/pyproject.toml -q -rs --junitxml=backend/app/modules/participation/tests/artifacts/qa.xml -o junit_family=xunit1',
        '.\\.venv\\Scripts\\python.exe -m app.modules.participation.tests.generate_qa_report --junit backend/app/modules/participation/tests/artifacts/qa.xml --output backend/app/modules/participation/QA_ENDPOINTS.md',
        "```", "",
        "`tests/artifacts/` está ignorado localmente. El Markdown es evidencia regenerable para revisión,",
        "no una certificación de despliegue ni de políticas oficiales. No habilitar PostgreSQL real con la bandera",
        "SPS_TEST_POSTGRESQL hasta configurar deliberadamente la conexión compartida al entorno de prueba.", "",
        "## Recomendación de Git", "",
        "Revisar el diff y versionar como QA del módulo en martin si la ejecución no tiene fallos.",
        "Conservar los bloqueos de integración. El push a martin es apropiado tras revisión y pruebas en el entorno del equipo,",
        "sin habilitar producción. Esta ejecución no hace commit, push ni abre Pull Request.",
        "Los archivos pendientes del quinto incremento ya existían al iniciar esta tarea; revisar el alcance del commit.", "",
    ]
    salida.write_text("\n".join(lineas), encoding="utf-8")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--junit", type=Path, required=True)
    parser.add_argument("--output", type=Path, required=True)
    args = parser.parse_args()
    generar(args.junit, args.output)
    print(f"Reporte generado: {args.output}")
