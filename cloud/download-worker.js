const manifest = {"name":"GITM-OS-3.3.0-integration-amd64.iso","size":3008622592,"sha256":"42f7822aef8c91e511fe793a41abdbef9193c905199d3dbd720b1741a3993133","parts":[{"name":"GITM-OS-3.3.0-integration-amd64.iso.part-01","size":1572864000,"sha256":"cda5f6ac329d696ab1e0d59ffd8c8fc754400e8cfe56f356405f0ccecdfa8b79","url":"https://github.com/naimamiam1234-star/GITM-OS/releases/download/gitm-os-3.3.0-design1/GITM-OS-3.3.0-integration-amd64.iso.part-01"},{"name":"GITM-OS-3.3.0-integration-amd64.iso.part-02","size":1435758592,"sha256":"5683b6de7e6234da8d53ff7bd4099660895426ca8ca3896db1361ff8c9dc16f4","url":"https://github.com/naimamiam1234-star/GITM-OS/releases/download/gitm-os-3.3.0-design1/GITM-OS-3.3.0-integration-amd64.iso.part-02"}],"boundary_offset":1572863984,"boundary_hex":"0fadd0a142acb5ea28a63095eb3ec82fd06aa71aecd894f11fa46d519f1fd6f9","tail_hex":"0000000000000000000000000000000000000000000000000000000000000000","boot_test_run":38017305438,"bios":"passed","uefi":"passed","gallery":{"images":60,"size":36828303,"sha256":"3e446072b1349833f076d06461a8e84f7263aa185c8a7ebc2f7a705c9c215c02","url":"https://github.com/naimamiam1234-star/GITM-OS/releases/download/gitm-os-3.3.0-design1/gallery.html","overview_url":"https://github.com/naimamiam1234-star/GITM-OS/releases/download/gitm-os-3.3.0-design1/gallery-overview.png","capture_runs":[38017305438]}};
/** @param {string|null} header @param {number} size */
export function parseRange(header,size) {
 if(!header) return [0,size-1];
 const match=/^bytes=(\d*)-(\d*)$/.exec(header);
 if(!match || (!match[1]&&!match[2])) throw new Error("range");
 let start=Number(match[1]),end=match[2]?Number(match[2]):size-1;
 if(!match[1]) {const suffix=Number(match[2]);if(!Number.isSafeInteger(suffix)||suffix<=0)throw new Error("range");start=Math.max(0,size-suffix);end=size-1;}
 if(!Number.isSafeInteger(start)||!Number.isSafeInteger(end)||start<0||start>=size||end<start)throw new Error("range");
 return [start,Math.min(end,size-1)];
}
/** @param {{url:string,size:number,start:number,end:number}} segment */
async function origin(segment) {
 const whole=segment.start===0&&segment.end===segment.size-1;
 const response=await fetch(segment.url,{headers:{"Range":`bytes=${segment.start}-${segment.end}`,"Accept-Encoding":"identity","User-Agent":"GITM-OS-download"},redirect:"follow"});
 if(!response.body || !(response.status===206||(whole&&response.status===200)))throw new Error("origin status "+response.status);
 if(response.status===206&&response.headers.get("Content-Range")!==`bytes ${segment.start}-${segment.end}/${segment.size}`)throw new Error("origin range");
 const length=response.headers.get("Content-Length");
 if(length&&Number(length)!==segment.end-segment.start+1)throw new Error("origin length");
 return response.body;
}
export default {
 /** @param {Request} request */
 async fetch(request) {
  const path=new URL(request.url).pathname;
  if(!["GET","HEAD"].includes(request.method))return new Response("Method not allowed",{status:405,headers:{"Allow":"GET, HEAD"}});
  if(["/","/health","/manifest.json"].includes(path))return Response.json(manifest);
  if(path==='/gallery' || path==='/gallery-overview.png'){
   const isHtml=path==='/gallery';
   const url=isHtml?manifest.gallery.url:manifest.gallery.overview_url;
   const headers=new Headers({'Content-Type':isHtml?'text/html; charset=utf-8':'image/png','Cache-Control':'public, max-age=3600','X-Content-Type-Options':'nosniff'});
   if(isHtml){
    headers.set('ETag','"'+manifest.gallery.sha256+'"');
    headers.set('Content-Security-Policy',"default-src 'none'; img-src data:; style-src 'unsafe-inline'; base-uri 'none'; frame-ancestors 'none'");
   }
   if(request.method==='HEAD')return new Response(null,{headers});
   try{
    const upstream=await fetch(url,{redirect:'follow',headers:{'Accept-Encoding':'identity','User-Agent':'GITM-Gallery'}});
    if(upstream.status!==200||!upstream.body)return new Response('Gallery unavailable',{status:502});
    return new Response(upstream.body,{headers});
   }catch(error){console.error(JSON.stringify({event:'gallery_failed',message:String(error)}));return new Response('Gallery unavailable',{status:502});}
  }
  if(path!=="/"+manifest.name)return new Response("Not found",{status:404});
  let start,end;
  const range=request.headers.get("Range"),ifRange=request.headers.get("If-Range");
  const selectedRange=range&&(!ifRange||ifRange==='"'+manifest.sha256+'"')?range:null;
  try{[start,end]=parseRange(selectedRange,manifest.size);}catch{return new Response(null,{status:416,headers:{"Content-Range":`bytes */${manifest.size}`}});}
  const partial=selectedRange!==null,length=end-start+1;
  const headers=new Headers({"Content-Type":"application/octet-stream","Content-Disposition":`attachment; filename="${manifest.name}"`,"Content-Length":String(length),"Accept-Ranges":"bytes","ETag":`"${manifest.sha256}"`,"Cache-Control":"no-store","X-Content-Type-Options":"nosniff"});
  if(partial)headers.set("Content-Range",`bytes ${start}-${end}/${manifest.size}`);
  if(request.method==="HEAD")return new Response(null,{status:partial?206:200,headers});
  let offset=0;
  const segments=[];
  for(const part of manifest.parts){const a=Math.max(start,offset),b=Math.min(end,offset+part.size-1);if(a<=b)segments.push({...part,start:a-offset,end:b-offset});offset+=part.size;}
  try {
   const first=await origin(segments[0]);
   const stream=new FixedLengthStream(length);
   // The returned readable keeps this invocation alive while it streams.
   void (async()=>{await first.pipeTo(stream.writable,{preventClose:true});for(const segment of segments.slice(1)){const body=await origin(segment);await body.pipeTo(stream.writable,{preventClose:true});}const writer=stream.writable.getWriter();await writer.close();})().catch(async error=>{console.error(JSON.stringify({event:"download_failed",message:String(error)}));try{await stream.writable.abort(error);}catch{}});
   return new Response(stream.readable,{status:partial?206:200,headers});
  }catch(error){console.error(JSON.stringify({event:"origin_failed",message:String(error)}));return new Response("Download unavailable; use the GitHub release",{status:502});}
 }
};
