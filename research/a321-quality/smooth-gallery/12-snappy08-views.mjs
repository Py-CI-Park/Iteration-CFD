// meteor-cfd - Copyright (c) 2026 주식회사 이터레이션즈 (Iterations Co., Ltd.)
// Source-available, not Open Source. Teaching and academic research are
// free; commercial and non-academic research require a licence.
// Enquiries: simul@msimul.com
// See LICENSE at the repository root.
// Provenance: see ../PROVENANCE.md. No GPL-licensed source was consulted.
// Header comments added after execution; the pre-existing script body is preserved.
// The current file including this header is not a byte-original execution receipt.
const task=await taskSpace(10),p=task.page("p1");
const fs=await import("node:fs/promises");
const dir="D:/Chanil_Park/Project/Programming/Iteration-CFD-a321-preflight/research/a321-quality/evidence";
await p.click('loc=role:tab[name*="3D 뷰어"]');
const overview=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");const api=getViewerApi();
 for(const cmd of [
 {type:"load",path:"research/a321-quality/artifacts/snappy-08-owner-diagnostic",field:"diagnostic_owner_layer_min"},
 {type:"setField",field:"diagnostic_owner_layer_min",range:[0,8],colormap:"turbo"},
 {type:"setRepresentation",mode:"surface",patches:["aircraft"],shading:"flat"},
 {type:"setCamera",position:[49,35,38],target:[22,0,6],projection:"perspective"}]){
 const r=await api.execute(cmd);if(!r.ok)throw Error(JSON.stringify(r.error));}
 return api.getState();
});
if(overview.cellCount!==1010837)throw Error("WRONG_08_MESH");
async function capture(name){
 const {windowId}=await task.cdp("Browser.getWindowForTarget",{targetId:(await task.tabs()).find(t=>t.label==="p1").targetId});
 await task.cdp("Browser.setWindowBounds",{windowId,bounds:{windowState:"normal"}});
 await p.cdp("Page.bringToFront");
 await p.screenshot({path:dir+"/"+name+".png"});
}
await capture("studio-snappy08-layer-map");
const wing=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");const api=getViewerApi();
 const r=await api.execute({type:"setCamera",position:[25,13,14],target:[22.8,8,3.9],projection:"perspective"});
 if(!r.ok)throw Error(JSON.stringify(r.error));return api.getState();
});
await capture("studio-snappy08-wing-layers");
const edges=await p.evaluate(async()=>{
 const {getViewerApi}=await import("/src/viewer/api/viewerApi.ts");const api=getViewerApi();
 const r=await api.execute({type:"setRepresentation",mode:"surfaceEdges",patches:["aircraft"],shading:"flat"});
 if(!r.ok)throw Error(JSON.stringify(r.error));return api.getState();
});
await capture("studio-snappy08-wing-grid");
await fs.writeFile(dir+"/studio-snappy08-views.json",JSON.stringify({overview,wing,edges,meaning:"native layer-count diagnostic and aircraft boundary grid, not pressure or full volume mesh",CFD_solver_run:false},null,2)+"\n");
console.log({cells:overview.cellCount,field:overview.field,range:overview.range});
