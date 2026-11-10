// Un runtime nuevo por Send. Nunca serializa tokens, Environment ni cuerpos de login.
const fs=require('fs'),path=require('path'),readline=require('readline');
const newman=require(process.env.NUCLEAR_NEWMAN_MODULE);
const [collectionFile,envFile,rf,out]=process.argv.slice(2);
const col=JSON.parse(fs.readFileSync(collectionFile,'utf8'));let env=JSON.parse(fs.readFileSync(envFile,'utf8'));
const folder=col.item.find(x=>x.name.startsWith(rf+' '));
const input=readline.createInterface({input:process.stdin,crlfDelay:Infinity});const lines=input[Symbol.asyncIterator]();
function safe(s){s=String(s||'').replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g,'[JWT omitido]');for(const v of env.values||[])if(/token|clave|codigo/.test(v.key)&&v.value&&String(v.value).length>=8)s=s.split(String(v.value)).join('[secreto LAB omitido]');return s;}
(async()=>{
 let fallos=0,aserciones=0;
 for(let i=0;i<folder.item.length;i++){
  if(rf==='RF-19'&&/WORKER [23] /.test(folder.item[i].name)){process.stdout.write(JSON.stringify({tipo:'worker'})+'\n');const ack=await lines.next();if(ack.done||!JSON.parse(ack.value).ok)throw Error('Worker no confirmado');}
  const item=folder.item[i];if(item.name.includes('RELOJ LAB')){process.stdout.write(JSON.stringify({tipo:'reloj'})+'\n');const ack=await lines.next();if(ack.done||!JSON.parse(ack.value).ok)throw Error('Reloj LAB no confirmado');}const s=await new Promise((resolve,reject)=>newman.run({collection:{info:col.info,item:[item]},environment:env,reporters:[],timeoutRequest:30000,timeoutScript:10000},(err,r)=>err?reject(err):resolve(r)));
  env=s.environment.toJSON();const ex=s.run.executions[0],r=ex?.response;
  const pruebas=(ex?.assertions||[]).map(x=>({nombre:x.assertion,aprobada:!x.error,error:x.error?safe(x.error.message):undefined}));
  const errores=(s.run.failures||[]).map(x=>safe(x.error?.message));
  const d={tipo:'solicitud',caso:item.name,metodo:item.request.method,ruta:item.request.url,http:r?.code,pruebas,errores};
  if(r&&String(r.headers.get('Content-Type')).includes('application/json')){
   try{const limpiar=(x)=>Array.isArray(x)?x.map(limpiar):x&&typeof x==='object'?Object.fromEntries(Object.entries(x).map(([k,v])=>[k,/^(access_token|codigo_acceso|codigo_convocatoria|clave|clave_hash|codigo_hash|password)$/i.test(k)?'[omitido]':limpiar(v)])):x;
    d.respuesta=limpiar(JSON.parse(r.text()));
   }catch{}
  }
  if(r?.code>=400&&item.request.url.includes('/cases')){try{d.detalle_error=safe(JSON.stringify(JSON.parse(r.text()).detail));}catch{}}
  if(!r||!pruebas.length||errores.length)fallos++;
  if(r?.code===200&&/formato=(xlsx|pdf)/.test(item.request.url)){
   const ext=item.request.url.includes('formato=xlsx')?'xlsx':'pdf';const bytes=Buffer.from(r.stream);fs.writeFileSync(path.join(out,'reporte.'+ext),bytes);d.archivo='reporte.'+ext;d.bytes=bytes.length;d.publicacion={};
   for(const k of ['Content-Type','X-Publicacion-Id','X-Publicacion-Version','X-Publicacion-SHA256'])d.publicacion[k]=r.headers.get(k);
  }
  aserciones+=pruebas.length;process.stdout.write(JSON.stringify(d)+'\n');if(fallos)break;
 }
 const keys=['rf_version','rf_sesion','rf_docente_creado','rf_convocatoria','id_intento','id_participacion','publicacion_id'];const ids={};for(const k of keys){const v=env.values.find(x=>x.key===k);if(v?.value)ids[k]=v.value;}
 process.stdout.write(JSON.stringify({tipo:'fin',fallos,aserciones,ids})+'\n');input.close();process.exitCode=fallos?1:0;
})().catch(e=>{process.stdout.write(JSON.stringify({tipo:'fatal',error:safe(e.message)})+'\n');input.close();process.exitCode=1;});
