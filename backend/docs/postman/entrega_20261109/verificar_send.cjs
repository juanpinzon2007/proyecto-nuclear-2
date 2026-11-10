// Valida Send: un runtime Newman NUEVO por solicitud; solo Environment persiste.
const fs=require('fs');const path=require('path');const readline=require('readline');
const newman=require(process.env.NUCLEAR_NEWMAN_MODULE);
const [colPath,envPath,out]=process.argv.slice(2);
const col=JSON.parse(fs.readFileSync(colPath,'utf8'));let env=JSON.parse(fs.readFileSync(envPath,'utf8'));
const input=readline.createInterface({input:process.stdin,crlfDelay:Infinity});const lines=input[Symbol.asyncIterator]();
function safe(s){s=String(s||'').replace(/eyJ[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+\.[A-Za-z0-9_-]+/g,'[JWT omitido]');for(const v of env.values||[]){if(/token|clave|codigo/.test(v.key)&&v.value&&String(v.value).length>=8)s=s.split(String(v.value)).join('[secreto LAB omitido]');}return s;}
function send(item){return new Promise((resolve,reject)=>newman.run({collection:{info:col.info,event:col.event,item:[item]},environment:env,reporters:[],timeoutRequest:30000,timeoutScript:10000,bail:false},(err,s)=>err?reject(err):resolve(s)));}
(async()=>{
let total=0;let fallos=0;let guardas=0;
const inicial=JSON.parse(JSON.stringify(env));
for(const caso of ['environment_equivocado','orden_incorrecto']){
 env=JSON.parse(JSON.stringify(inicial));
 if(caso==='environment_equivocado')env.values.find(v=>v.key==='laboratorio_modo').value='OTRO';
 const s=await send(col.item[caso==='environment_equivocado'?0:1]);
 const bloqueo=!(s.run.executions||[]).some(x=>x.response);
 process.stdout.write(JSON.stringify({tipo:'guarda',nombre:caso,bloqueada_sin_http:bloqueo})+'\n');
 if(!bloqueo)throw new Error('La guarda no evitó el envío: '+caso);guardas++;
}
env=inicial;
for(let i=0;i<col.item.length;i++){
 const item=col.item[i];
 if(env.values.find(v=>v.key==='laboratorio_modo')?.value==='worker' && i>=2){
   process.stdout.write(JSON.stringify({tipo:'worker',numero:i-1})+'\n');const ack=await lines.next();if(ack.done||JSON.parse(ack.value).ok!==true)throw new Error('No se confirmó Worker propio.');
 }
 const s=await send(item);env=s.environment.toJSON();
 const exec=s.run.executions[0];const asserts=(exec?.assertions||[]).map(a=>({nombre:a.assertion,aprobada:!a.error,error:a.error?safe(a.error.message):undefined}));
 const fails=(s.run.failures||[]).map(f=>({nombre:f.error?.name||'Error',mensaje:safe(f.error?.message)}));
 const r=exec?.response;const info={tipo:'request',paso:i+1,nombre:item.name,http:r?.code,pruebas:asserts,fallos:fails};
 if(!r || !asserts.length || fails.length)fallos++;
 if(r?.code===200 && /formato=(xlsx|pdf)/.test(item.request.url)){
  const tipo=item.request.url.includes('formato=xlsx')?'xlsx':'pdf';const b=Buffer.from(r.stream);fs.writeFileSync(path.join(out,'RF16_Oficial.'+tipo),b);
  info.archivo='RF16_Oficial.'+tipo;info.bytes=b.length;info.cabeceras={};for(const k of ['Content-Type','Content-Disposition','X-Publicacion-Id','X-Publicacion-Version','X-Publicacion-SHA256'])info.cabeceras[k]=r.headers.get(k);
 }
 total+=asserts.length;process.stdout.write(JSON.stringify(info)+'\n');
 if(fallos)break;
}
const keys=['id_intento','id_participacion','publicacion_id','publicacion_version','publicacion_sha256','paso_principal','paso_reportes','paso_worker'];const vars={};for(const k of keys){const v=env.values.find(x=>x.key===k);if(v&&v.value)vars[k]=v.value;}
process.stdout.write(JSON.stringify({tipo:'fin',aserciones:total,fallos,guardas,variables:vars,modo:'Un newman.run independiente por Send; sin variables locales de la ejecución anterior.'})+'\n');
input.close();process.exitCode=fallos?1:0;
})().catch(e=>{process.stdout.write(JSON.stringify({tipo:'fatal',mensaje:safe(e.message)})+'\n');input.close();process.exitCode=1;});
