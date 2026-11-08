// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
// Header comments added after execution; the pre-existing script body is preserved.
// The current file including this header is not a byte-original execution receipt.
const task=await taskSpace(10),p=task.page("p2");
const fs=await import("node:fs/promises");
const sources=[];
for(const [url,term] of [
 ["https://doc.openfoam.com/2212/tools/pre-processing/mesh/generation/snappyhexmesh/layers/","nBufferCellsNoExtrude"],
 ["https://doc.openfoam.com/2606/tools/pre-processing/mesh/generation/snappyhexmesh/meshquality/","minFaceWeight"]]){
 await p.goto(url,{waitUntil:"domcontentloaded",timeout:30000});
 const result=await p.evaluate(term=>{const text=document.body.innerText;const i=text.indexOf(term);return {title:document.title,url:location.href,term,found:i>=0,context:i>=0?text.slice(Math.max(0,i-80),i+500):null};},term);
 sources.push(result);
}
await fs.writeFile("D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence/smooth-study-sources.json",JSON.stringify({sources,note:"Public parameter documentation; installed external executable is OpenFOAM v1912; no implementation source consulted"},null,2)+"\n");
await p.goto("http://127.0.0.1:8776/a321-quality/report.html",{waitUntil:"domcontentloaded",timeout:30000});
console.log(sources.map(s=>({url:s.url,found:s.found})));
