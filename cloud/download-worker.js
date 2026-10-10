const manifest = {"name":"GITM-OS-3.3.0-integration-amd64.iso","size":3008573440,"sha256":"c39399eed36a7f6dff97e48140a096567ba75dce819b1e8a5a418bbb224fc7c8","parts":[{"name":"GITM-OS-3.3.0-integration-amd64.iso.part-01","size":1572864000,"sha256":"bd6eca3105bd3b63d0cf2e316c459965bd6c8783e78792eb6e55315fc440c0dd","url":"https://github.com/naimamiam1234-star/GITM-OS/releases/download/gitm-os-3.3.0-statusfix1/GITM-OS-3.3.0-integration-amd64.iso.part-01"},{"name":"GITM-OS-3.3.0-integration-amd64.iso.part-02","size":1435709440,"sha256":"40e7c4f28d7cbacb9a2db7f3c963b260ae5f0c6a42ea265529bbc51111c5cef9","url":"https://github.com/naimamiam1234-star/GITM-OS/releases/download/gitm-os-3.3.0-statusfix1/GITM-OS-3.3.0-integration-amd64.iso.part-02"}],"boundary_offset":1572863984,"boundary_hex":"4617ba44eace7071d81982de348afe9f2473c4ab3645d01f1cfc32381f03abf8","tail_hex":"0000000000000000000000000000000000000000000000000000000000000000","boot_test_run":38006827522,"bios":"passed","uefi":"passed"};
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
  if(path!=="/"+manifest.name)return new Response("Not found",{status:404});
  let start,end;
  try{[start,end]=parseRange(request.headers.get("Range"),manifest.size);}catch{return new Response(null,{status:416,headers:{"Content-Range":`bytes */${manifest.size}`}});}
  const partial=request.headers.has("Range"),length=end-start+1;
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
