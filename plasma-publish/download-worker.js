const manifest = {"name":"GITM-OS-Plasma6-amd64.iso","size":3313645568,"sha256":"6f21d51e1c1461b0eae9b5727c20f613057188a58c6762168fa0cd8db6be8ac9","parts":[{"name":"GITM-OS-Plasma6-amd64.iso.part01","size":1572864000,"sha256":"4c44d7398ee4780536193bd2624fe78f3eeaca1fe2f76bcdea4662b5b1edca41","url":"https://github.com/naimamiam1234-star/GITM-OS/releases/download/gitm-os-3.3.0-plasma5/GITM-OS-Plasma6-amd64.iso.part01"},{"name":"GITM-OS-Plasma6-amd64.iso.part02","size":1572864000,"sha256":"1694a060fe277da0f89fc28a3887d2a1aa2be339a2824e301d91dbe7e23756a9","url":"https://github.com/naimamiam1234-star/GITM-OS/releases/download/gitm-os-3.3.0-plasma5/GITM-OS-Plasma6-amd64.iso.part02"},{"name":"GITM-OS-Plasma6-amd64.iso.part03","size":167917568,"sha256":"473852d5dbe5b2650591c07d3da5a0e57aadc2e6868c872d7cdc65280dac443b","url":"https://github.com/naimamiam1234-star/GITM-OS/releases/download/gitm-os-3.3.0-plasma5/GITM-OS-Plasma6-amd64.iso.part03"}],"boundary_offset":1572863984,"boundary_hex":"7ec8c5e4892cf1fe7abee25a8feeec14aedc6748ad2c9474bd546ace7c630427","tail_hex":"0000000000000000000000000000000000000000000000000000000000000000","build_commit":"54f3d38f1097f46a420744495b269c9248be6931","boot_test_run":38094790367,"bios":"passed","uefi":"passed","settings_single_window":"verified","keyboard_search":"verified","framebuffer":"verified","theme":{"klassy":"9b788b2ea8d40c6a7af3b0130de9e891d41fbb30","panel_colorizer":"d0b1d4cab773f05cdcda2c1b2970093a5c367b54","icons":"Papirus","dock":"native-floating-visible","auto_hide_optional":true,"wallpaper":"shared"},"base":"Ubuntu 26.04","desktop":"Plasma 6.6.6","cpu_features":["ssse3","sse4_1","sse4_2","popcnt"],"gallery":{"images":61,"size":39079315,"sha256":"263030ae9dee3b88b4c2ca9347b27a823df6e87f74899d81dd82890927aa093a","url":"https://github.com/naimamiam1234-star/GITM-OS/releases/download/gitm-os-3.3.0-plasma5/gallery.html","overview_url":"https://github.com/naimamiam1234-star/GITM-OS/releases/download/gitm-os-3.3.0-plasma5/gallery-overview.png","capture_runs":[38094790367,38094959169]}};
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
