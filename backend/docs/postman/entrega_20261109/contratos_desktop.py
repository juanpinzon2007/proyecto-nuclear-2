"""Una fuente de descripciones/orden para colecciones Send y guía de sustentación."""
import json,re
from pathlib import Path

ARCHIVOS={'principal':'Proyecto_Nuclear_entrega_20261109.postman_collection.json',
    'reportes':'Proyecto_Nuclear_reportes_oficiales.postman_collection.json',
    'worker':'Proyecto_Nuclear_worker_20261109.postman_collection.json'}
# RF, Response esperada y explicación académica por solicitud existente.
PRINCIPAL=[
('RF-02/RF-03','access_token, token_type y vigencia; token capturado automáticamente.','El administrador entra con credenciales sintéticas reales de Identity; no mostrar el JWT.'),
('RF-02','access_token del docente; captura automática.','El rol y cuenta se validan en PostgreSQL, no en una cabecera de identidad.'),
('RF-03','Página de docentes con campos públicos, sin hashes ni contraseñas.','La consulta requiere administrador; no concede permisos adicionales.'),
('RF-01','access_token estudiantil asociado a su convocatoria.','El correo y código pertenecen al titular; login no inicia el intento.'),
('RF-01','Token de otro estudiante sintético, reservado para negativas.','Se utiliza una identidad real distinta, no un token inventado.'),
('RF-01/RF-02','Identidad del estudiante y roles vigentes.','La API recupera la cuenta persistente del JWT; no confía en datos de identidad enviados por el cliente.'),
('RF-22','admitida=true y concesión propia persistida.','La admisión fue preparada administrativamente en LAB; esta consulta no concede ingreso ni crea participación.'),
('RF-22','Validación autorizada de ingreso, sin crear participación ni intento.','Validar ingreso se distingue de iniciar la simulación.'),
('RF-12','Documento sintético, versión, referencia y huella; captura automática.','Esta ruta solo existe en la aplicación LAB; no constituye consentimiento institucional aprobado.'),
('RF-12','Aceptación explícita con id_consentimiento.','Se acepta el documento del servidor y se conserva su versión; solo política LAB.'),
('RF-12','Intento EN_CURSO, id_intento e id_participacion capturados.','La creación usa convocatoria, admisión y consentimiento en una transacción de laboratorio.'),
('RF-12','Conflicto de inicio repetido; no otro intento válido.','409 es el resultado esperado: la repetición no debe crear otro inicio.'),
('RF-11/RF-12','Error de acceso, sin progreso del titular.','Un estudiante autenticado distinto no puede consultar este intento.'),
('RF-11','Progreso con respondidas=0 y el intento esperado.','La consulta es privada y todavía no hay selecciones ni calificaciones.'),
('RF-10/RF-11','Primera pregunta autorizada y sus opciones; captura automática.','Solo se muestra la escena actual; no respuestas correctas ni preguntas futuras.'),
('RF-10','Confirmación de primera selección; mismo intento.','La primera respuesta queda registrada e inmutable.'),
('RF-10','409 al intentar seleccionar otra alternativa para la misma pregunta.','La regla posterior de la profesora prohíbe modificar una respuesta ya registrada.'),
('RF-10/RF-11','Pregunta siguiente del grafo real; captura automática.','La alternativa registrada determina la transición persistente de Cases.'),
('RF-10','Confirmación de la segunda selección; mismo intento.','Se responde una pregunta pendiente, sin sustituir la anterior.'),
('RF-10/RF-11','recorrido_finalizado=true y pregunta=null.','FIN corresponde al grafo publicado; no se fabrica una escena adicional.'),
('RF-11','respondidas=2 y selección original conservada.','El progreso recupera las decisiones reales y no revela calificaciones.'),
('RF-12','403 al cierre por estudiante ajeno.','Autenticarse no concede titularidad sobre cualquier intento.'),
('RF-12/RF-23','estado=FINALIZADO y fecha de cierre.','Cerrar no calcula ni publica una nota; el cálculo docente es posterior.'),
('RF-12','Mismo cierre y fecha que la solicitud anterior.','El cierre repetido es idempotente y no cambia su historia.'),
('RF-10/RF-12','409: no continúa una simulación cerrada.','El cierre confirmado impide seguir respondiendo o navegar el intento.'),
('RF-02','Token de un docente distinto, capturado para la negativa.','La prueba usa un docente real ajeno al ámbito académico.'),
('RF-13/RF-24','404: todavía no existe resultado técnico.','La consulta no calcula: el cierre dejó el intento sin calificación automática.'),
('RF-13/RF-24','Resultado técnico 100.00, oficial=false, versión histórica.','POST explícito del docente calcula las dos respuestas correctas de esta fixture; no es nota oficial.'),
('RF-13/RF-24','Mismo id_resultado, huella y fecha de cálculo.','Reintentar el comando no duplica ni recalifica el resultado.'),
('RF-13/RF-24','Mismo resultado persistido, recuperado por GET.','Una solicitud SQL independiente recupera el resultado sin generarlo de nuevo.'),
('RF-02/RF-13','403: un estudiante no puede ejecutar evaluación docente.','El permiso se comprueba en el servidor, no se deduce del conocimiento de un UUID.'),
('RF-13/RF-15','403: docente fuera del ámbito de sesión/caso/grupo.','El rol docente no concede acceso a recursos ajenos.'),
]
REPORTES=[
('RF-02','JWT docente capturado.','Login real; no capturar el token en la evidencia.'),
('RF-01','JWT del estudiante titular capturado.','Esta identidad comprobará la consulta privada y la negativa de exportación.'),
('RF-02','JWT de un docente ajeno capturado.','No concede ámbito sobre la sesión del laboratorio.'),
('RF-13/RF-24','Cohorte publicable y nota técnica 33.33; captura de revisión_sha256.','La fixture tiene un intento VENCIDO con una respuesta de tres; aún no está publicado.'),
('RF-13/RF-24/RF-27','oficial=true, publicación v1 y hash de revisión autorizado.','El docente publica expresamente toda la cohorte; es un POST que escribe publicación y aviso internos.'),
('RF-13/RF-27','Mismo id de publicación.','Repetir la misma autorización no duplica publicación ni avisos.'),
('RF-13/RF-16','Publicación oficial exacta; captura id, versión y huella.','Esta fuente inmutable es la que deben usar los dos archivos.'),
('RF-14','Resultado propio oficial 33.33.','Solo el estudiante titular consulta su fila, sin acceso a las de otros.'),
('RF-15/RF-16','403 para docente ajeno.','La publicación no es un recurso público por conocer el identificador.'),
('RF-02/RF-16','401 sin autenticación.','Este rechazo es una prueba aprobada, no un fallo de la demostración.'),
('RF-16','Binario XLSX no vacío y cabeceras de la publicación capturada.','Guardar con Send and Download y abrir Resultados: PARCIAL 33.33, misma publicación.'),
('RF-16','PDF no vacío y cabeceras de la misma publicación.','Abrir el PDF y comparar id/versión/nota con Excel; no recalcula calificaciones.'),
('RF-16','401 y JSON de error, sin archivo adjunto.','La exportación requiere JWT válido.'),
('RF-15/RF-16','403 y ningún archivo adjunto.','Se rechaza al docente ajeno aunque esté autenticado.'),
('RF-02/RF-16','403 y ningún archivo adjunto.','El estudiante puede consultar su resultado, pero no exportar el reporte docente de la sesión.'),
]
WORKER=[
('RF-02','JWT docente capturado.','Login real con credencial sintética generada por el preparador.'),
('RF-19','Sesión EN_CURSO y versión exacta.','Está vencida desde hace más de 24 horas; la fecha es preparación LAB para no esperar un día.'),
('RF-19','Sesión FINALIZADO tras ejecutar w en la consola.','El Worker real persistió el cierre, auditoría y aviso; no evaluó intentos ni publicó notas.'),
('RF-19','FINALIZADO de nuevo tras ejecutar w por segunda vez.','La segunda ejecución cierra cero sesiones y mantiene un solo efecto histórico.'),
]
DATOS={'principal':PRINCIPAL,'reportes':REPORTES,'worker':WORKER}


def generar_guia(out):
    lineas=['# Postman Desktop para Windows — sustentación',
    '', '## Preparar e importar', '',
    'Desde PowerShell, situado en la raíz del repositorio original:', '',
    '```powershell', '.\\preparar-postman.ps1', '```', '',
    'Elija 1 (recorrido principal), 2 (publicación y reportes) o 3 (Worker). También puede ejecutar ` .\\preparar-postman.ps1 -Opcion 1` (o 2/3). Requiere Docker Engine activo, imagen postgres:17 y el entorno Python del proyecto; no requiere Newman ni Postman CLI.',
    'Si faltara el entorno Python, prepárelo una sola vez desde la raíz: `py -m venv .venv` y `.\\.venv\\Scripts\\python.exe -m pip install -e "./backend[dev]"`. Si falta únicamente la imagen, use `docker pull postgres:17`. El lanzador comprueba estos requisitos y falla sin reutilizar bases existentes.',
    'Si Windows bloquea el script por su política de ejecución, puede usar una excepción solo para ese proceso: `powershell.exe -NoProfile -ExecutionPolicy Bypass -File .\\preparar-postman.ps1`. No cambie la política global.', '',
    'Mantenga abierta esa consola. El preparador crea exclusivamente PostgreSQL desechable, servidores locales en puertos libres y credenciales sintéticas nuevas. No usa .env ni bases permanentes. La preparación de casos, asociaciones, admisión y documentos es administrativa de LAB: no demuestra un flujo docente completo por API.', '',
    'La consola muestra dos rutas exactas dentro de una carpeta temporal privada: la colección seleccionada y `Environment_ACTIVO.postman_environment.json`. Pulse `i` para abrirla. En Postman Desktop use Import para esos dos archivos. No importe el environment vacío de la carpeta del repositorio como entorno activo.',
    '**Seleccione expresamente en el desplegable Environment el nombre único que imprime la consola**, `NUCLEAR LAB — … — <identificador>`. Importar un JSON no selecciona automáticamente el entorno ni actualiza otro entorno ya activo. Si Postman pregunta cómo resolver una colección antigua, importe como copia o seleccione la colección recién importada; use el nombre NUCLEAR DESKTOP correspondiente al modo.', '',
    'No copie UUID, contraseñas o JWT. El environment temporal contiene los datos sintéticos completos; cada login captura su token con pm.environment.set. Las solicitudes guardan los identificadores reales para el siguiente Send. Las variables sobreviven entre solicitudes independientes, sin Runner.',
    'El archivo temporal contiene secretos sintéticos en texto; el tipo secret solo los oculta visualmente. No exporte, comparta ni sincronice esos valores. Use valores locales de Desktop y un entorno de laboratorio. Las capturas nunca deben incluir Authorization, variables secretas, códigos ni el cuerpo de respuesta del login.', '',
    '## Ejecutar sin improvisación', '',
    'Abra la primera solicitud de la colección indicada y pulse Send. Continúe en el orden numérico siguiente únicamente si todas las aserciones de Test Results están verdes. Los 401/403/404/409 de las negativas son éxitos esperados. No ejecute las tres colecciones sobre un mismo entorno.',
    'Las guardas impiden enviar con un modo equivocado o saltando pasos. No sustituyen autorización del servidor. Si una prueba queda roja, conserve la respuesta y deténgase; prepare un laboratorio nuevo para repetir. No repita comandos de escritura fuera de sus pruebas de idempotencia. Si expira un JWT, vuelva a enviar el login de ese actor y reanude, sin copiar el token.',
    'En reportes use Send and Download (o Save Response después de Send) para guardar XLSX/PDF y abrirlos. Compare las cabeceras de publicación y la nota 33.33. Las negativas deben devolver JSON, nunca un archivo.',
    'En Worker envíe las dos primeras solicitudes, escriba `w` en la consola, envíe la tercera, escriba `w` otra vez y envíe la cuarta. Se ejecuta el Worker real --once: primero cierra 1 sesión y después 0. La fecha de la fixture está más de 24 horas vencida; no se modifica la política del Worker ni se calculan notas.', '',
    '## Cerrar y cambiar de laboratorio', '',
    'Escriba `q` en la consola: detiene solo los servidores y PostgreSQL creados por esa ejecución y elimina sus dos archivos temporales de importación. No elimina capturas o descargas que haya añadido. En el menú elija otro modo; importe sus nuevos archivos y seleccione su nuevo Environment. Con -Opcion, q termina el lanzador.',
    'La copia importada en Postman no se borra automáticamente: elimínela manualmente al terminar la demostración. No reutilice sus tokens o URLs después de q. No cierre Docker Desktop para limpiar: podría afectar recursos de otros compañeros.', '',
    '## Alcance y evidencia', '',
    'MAIN significa ruta registrada en app.main; LAB significa composición aislada, no una ruta productiva habilitada. El recorrido principal calcula 100.00 como resultado técnico NO oficial. La colección de reportes usa otra fixture y una publicación explícita exclusivamente de laboratorio. No implica aprobación institucional de las políticas.',
    'Para cada captura muestre nombre de solicitud, método/URL sin secretos, estado HTTP y Test Results. En operaciones no login puede mostrar Response con datos sintéticos. Para archivos capture también el documento abierto y sus cabeceras de publicación. Guarde las imágenes fuera del índice Git.', '']
    for modo,archivo in ARCHIVOS.items():
        c=json.loads((out/archivo).read_text(encoding='utf-8'))
        lineas += [f'## {c["info"]["name"]}', '', f'Archivo: `{archivo}`. Environment: el único generado para **{modo}**.', '']
        for n,(item,(rf,respuesta,explicacion)) in enumerate(zip(c['item'],DATOS[modo]),1):
            req=item['request']; script='\n'.join(e['script']['exec'][0] if len(e['script']['exec'])==1 else '\n'.join(e['script']['exec']) for e in item['event'] if e['listen']=='test')
            http=re.search(r'HTTP exacto (\d+)',script)[1]
            pruebas=re.findall(r"pm\.test\(['\"]([^'\"]+)['\"]",script)
            login='/auth/' in req['url']
            dependencia='Preparar/importar y seleccionar este Environment.' if n==1 else f'Paso {n-1} aprobado.'
            if modo=='worker' and n in (3,4):dependencia+=' Ejecutar w en la consola antes de Send.'
            lineas += [f'### {n:02d}. {item["name"]}', '', f'- RF: {rf}. Superficie: '+('LAB aislada.' if '{{base_url_laboratorio}}' in req['url'] else 'app.main.'),
                f'- Operación: `{req["method"]} {req["url"]}`. HTTP esperado: **{http}**.',
                f'- Dependencia: {dependencia}', f'- Response esperada: {respuesta}',
                '- Test Results: '+('; '.join(pruebas) if pruebas else 'Ver las aserciones guardadas en Scripts / Post-response')+'. Todas deben aprobar.',
                f'- Explicación: {explicacion}',
                f'- Captura: `{modo}_{n:02d}.png`; '+('solo estado y Test Results; ocultar Response del login.' if login else 'estado, Response sintética y Test Results; ocultar cabeceras de autorización.'), '']
    (out/'GUIA_POSTMAN_SUSTENTACION.md').write_text('\n'.join(lineas)+'\n',encoding='utf-8')


def enriquecer(out):
    for modo,file in ARCHIVOS.items():
        path=out/file;c=json.loads(path.read_text(encoding='utf-8'));datos=DATOS[modo]
        assert len(c['item'])==len(datos),(modo,len(c['item']))
        c['info']['name']={'principal':'NUCLEAR DESKTOP — 1 Recorrido principal (MAIN + LAB)','reportes':'NUCLEAR DESKTOP — 2 Publicación y reportes RF-16','worker':'NUCLEAR DESKTOP — 3 Worker RF-19'}[modo]
        if modo=='principal':
            c['item'][29]['name']='MAIN — recuperar resultado técnico persistido'
            c['item'][30]['name']='MAIN — rechazar evaluación por estudiante'
            c['item'][31]['name']='MAIN — rechazar evaluación por docente ajeno'
        c['info']['description']+=' Windows/Desktop: preparar con preparar-postman.ps1, importar Environment temporal de este modo, seleccionar su nombre y pulsar Send en orden. Cada solicitud guarda variables en pm.environment; no requiere Runner. No compartir secretos sintéticos.'
        modo_guard="""function rechazarPreparacion(m){if(pm.execution&&typeof pm.execution.skipRequest==='function')pm.execution.skipRequest();throw new Error(m);}
if(pm.environment.get('laboratorio_modo')!=='%s')rechazarPreparacion('Environment equivocado: prepare y seleccione el laboratorio %s.');
if(!pm.environment.get('laboratorio_id'))rechazarPreparacion('Importe el Environment temporal generado por preparar-postman.ps1.');
""" % (modo,modo)
        c.setdefault('event',[]).insert(0,{'listen':'prerequest','script':{'type':'text/javascript','exec':modo_guard.splitlines()}})
        for n,(item,(rf,respuesta,exponer)) in enumerate(zip(c['item'],datos),1):
            req=item['request'];scripts=item['event'][0]['script']['exec'];texto='\n'.join(scripts)
            assert 'pm.variables.set(' not in texto,'Variable local no sobrevive a Send'
            status=int(re.search(r'HTTP exacto (\d+)',texto)[1])
            superficie='LAB AISLADA' if '{{base_url_laboratorio}}' in req['url'] else 'app.main'
            accion=('Solo lectura.' if req['method']=='GET' else 'POST explícito: '+('autenticación y emisión de token.' if '/auth/' in req['url'] else 'intenta cambiar estado o registrar datos sintéticos; el rechazo esperado no autoriza escritura.'))
            dependencia='Preparación del laboratorio.' if n==1 else 'Ejecutar antes la solicitud '+str(n-1)+' con sus pruebas aprobadas.'
            if modo=='worker' and n in (3,4):dependencia+=' Ejecutar w en la consola justo antes de este Send.'
            req['description']=f'**Paso {n}/{len(datos)} — {rf} — {superficie}**\n\nObjetivo: {exponer}\n\nHTTP esperado: {status}. Response: {respuesta}\n\nOperación: {accion}\n\nDependencia: {dependencia}\n\nSustentación: {exponer} No mostrar Authorization, passwords, códigos o respuestas de login. Datos exclusivamente sintéticos.'
            guard="if((Number(pm.environment.get('paso_%s'))||0)<%d){if(pm.execution&&pm.execution.skipRequest)pm.execution.skipRequest();throw new Error('Ejecute primero el paso %d de esta colección.');}"%(modo,n-1,n-1)
            item['event'].insert(0,{'listen':'prerequest','script':{'type':'text/javascript','exec':[guard]}})
            scripts.append("if(pm.response.code===%d)pm.environment.set('paso_%s',Math.max(Number(pm.environment.get('paso_%s'))||0,%d));"%(status,modo,modo,n))
            if status>=400:scripts.append("pm.test('Error sin datos académicos',()=>{const j=pm.response.json();pm.expect(j).to.have.property('detail');pm.expect(j).not.to.have.any.keys('access_token','nota_final','selecciones','resultados');});")
            if modo=='principal' and n==15:
                scripts.append("const qp=pm.response.json().pregunta;pm.test('Otra alternativa real disponible',()=>pm.expect(qp.opciones.length).to.be.above(1));pm.environment.set('primera_decision_id',qp.id);pm.environment.set('primera_opcion_id',qp.opciones[0].id);pm.environment.set('opcion_alternativa_id',qp.opciones[1].id);")
            if modo=='principal' and n==17:req['body']['raw']='{\n  "id_opcion": "{{opcion_alternativa_id}}"\n}'
            if modo=='principal' and n in (14,21):
                scripts.append("pm.test('Intento propio recuperado',()=>{const j=pm.response.json();pm.expect(String(j.intento.id_intento)).to.eql(String(pm.environment.get('id_intento')));pm.expect(String(j.intento.id_participacion)).to.eql(String(pm.environment.get('id_participacion')));});")
            if modo=='principal' and n==21:
                scripts.append("pm.test('Selección original intacta',()=>pm.expect(pm.response.json().selecciones.some(s=>s.id_decision===pm.environment.get('primera_decision_id')&&s.id_opcion===pm.environment.get('primera_opcion_id'))).to.eql(true));")
            if modo=='principal' and n==23:
                scripts.append("pm.environment.set('cierre_original',JSON.stringify(pm.response.json()));")
            if modo=='principal' and n==24:
                scripts.append("pm.test('Cierre íntegramente idempotente',()=>pm.expect(pm.response.json()).to.deep.eql(JSON.parse(pm.environment.get('cierre_original'))));")
            if modo=='principal' and n in (28,29,30):
                scripts.append("pm.test('Mismo intento y resultado NO oficial',()=>{const j=pm.response.json();pm.expect(String(j.id_intento)).to.eql(String(pm.environment.get('id_intento')));pm.expect(j.oficial).to.eql(false);});")
            if modo=='principal' and n==30:
                scripts.append("pm.test('Resultado persistido idéntico',()=>{const j=pm.response.json();pm.expect(String(j.id_resultado)).to.eql(String(pm.environment.get('resultado_id_primero')));pm.expect(j.procedencia_sha256).to.eql(pm.environment.get('resultado_hash_primero'));});")
        path.write_text(json.dumps(c,ensure_ascii=False,indent=2)+'\n',encoding='utf-8')
